"""Interactive terminal menu, started by running ``xplot`` with no arguments."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Callable

from .codegen import PlotSpec
from .datfile import DatError, DatFile, load_dat, summarize

Ask = Callable[[str], str]
Say = Callable[..., None]


class _Quit(Exception):
    pass


class Session:
    """State and prompts for one interactive run. ``ask``/``say`` can be swapped in tests."""

    def __init__(self, ask: Ask = input, say: Say = print, ode=None, names=None, kind="auto"):
        self.ask, self.say = ask, say
        self.ode, self.names, self.kind = ode, names, kind
        self.dat: DatFile | None = None

    # ---- prompt helpers -------------------------------------------------
    def prompt(self, text: str, default: str | None = None) -> str:
        suffix = f" [{default}]" if default not in (None, "") else ""
        answer = self.ask(f"{text}{suffix}: ").strip()
        if answer.lower() in ("q", "quit", "exit"):
            raise _Quit
        return answer or (default or "")

    def yes(self, text: str, default: bool) -> bool:
        answer = self.prompt(f"{text} ({'Y/n' if default else 'y/N'})").lower()
        return default if not answer else answer.startswith("y")

    def columns(self, text: str, default: list[str], single: bool = False) -> list[str]:
        """Ask for column name(s)/index(es) until they all exist in the file."""
        while True:
            raw = self.prompt(text, " ".join(default))
            keys = raw.replace(",", " ").split()
            if single and len(keys) != 1:
                self.say("  enter exactly one column")
                continue
            try:
                return [self.dat.resolve(k) for k in keys]
            except DatError as exc:
                self.say(f"  {exc}")

    # ---- steps ----------------------------------------------------------
    def choose_file(self, start: str | None = None) -> None:
        candidate = start
        while True:
            if candidate is None:
                found = sorted(Path.cwd().glob("*.dat"))
                if found:
                    self.say("\n.dat files in this folder:")
                    for i, f in enumerate(found, 1):
                        self.say(f"  {i}) {f.name}")
                    raw = self.prompt("File number or path", "1")
                    candidate = str(found[int(raw) - 1]) if raw.isdigit() and 0 < int(raw) <= len(found) else raw
                else:
                    candidate = self.prompt("Path to a .dat file")
            try:
                self.dat = load_dat(candidate, kind=self.kind, ode=self.ode, names=self.names)
            except DatError as exc:
                self.say(f"  {exc}")
                candidate = None
                continue
            self.say("\n" + summarize(self.dat) + "\n")
            return

    def menu(self) -> str:
        if self.dat.kind == "sim":
            options = {"1": "time series", "2": "phase plane (2-D)"}
            if self.dat.n_cols >= 3:
                options["3"] = "phase space (3-D)"
        else:
            options = {"1": "bifurcation diagram"}
        options |= {"i": "show data summary", "f": "open another file", "q": "quit"}
        self.say("What would you like to do?")
        for key, label in options.items():
            self.say(f"  {key}) {label}")
        while True:
            choice = self.prompt("Choice", "1").lower()
            if choice in options:
                return choice
            self.say("  please pick one of: " + ", ".join(options))

    def build_spec(self, choice: str) -> PlotSpec:
        d = self.dat
        spec = PlotSpec()
        if d.kind != "sim":
            spec.mode = "bifurcation"
            self.say(f"  plottable: {', '.join(d.variables)}")
            spec.y = self.columns("Variable on the y-axis", [d.variables[0]], single=True)
            if d.kind == "allinfo":
                spec.par = 2 if self.prompt("Parameter on the x-axis (1 or 2)", "1") == "2" else 1
        elif choice == "1":
            spec.mode = "timeseries"
            self.say(f"  columns: {', '.join(f'{i}={c}' for i, c in enumerate(d.columns))}")
            spec.x = self.columns("X column", [d.columns[0]], single=True)[0]
            spec.y = self.columns("Y column(s)", [c for c in d.columns if c != spec.x])
            if len(spec.y) > 1:
                spec.subplots = self.yes("One panel per column?", False)
        else:
            spec.mode = "phase" if choice == "2" else "phase3d"
            self.say(f"  columns: {', '.join(f'{i}={c}' for i, c in enumerate(d.columns))}")
            v = d.variables
            spec.x = self.columns("X axis", [v[0]], single=True)[0]
            spec.y = self.columns("Y axis", [v[1] if len(v) > 1 else d.columns[0]], single=True)
            if spec.mode == "phase3d":
                spec.z = self.columns("Z axis", [v[2] if len(v) > 2 else d.columns[0]], single=True)[0]

        spec.title = self.prompt("Title (Enter for none)") or None
        save = self.prompt("Save image as (e.g. plot.png, Enter to skip)")
        spec.save = [save] if save else []
        return spec

    def equivalent_command(self, spec: PlotSpec, script: str | None, show: bool) -> str:
        """The one-line command that would make the same plot."""
        parts = ["xplot", str(self.dat.path)]
        if self.ode:
            parts += ["--ode", str(self.ode)]
        if spec.mode == "timeseries":
            if spec.x != self.dat.columns[0]:
                parts += ["-x", spec.x]
            parts += ["-y", *spec.y]
            if spec.subplots:
                parts.append("--subplots")
        elif spec.mode in ("phase", "phase3d"):
            parts += ["--phase", spec.x, spec.y[0]] + ([spec.z] if spec.z else [])
        else:
            parts += ["-y", spec.y[0]]
            if spec.par != 1:
                parts += ["--par", "2"]
        if spec.title:
            parts += ["--title", spec.title]
        for s in spec.save:
            parts += ["-o", s]
        if script:
            parts += ["--script", script]
        if not show:
            parts.append("--no-show")
        return " ".join(shlex.quote(p) for p in parts)

    def plot(self, choice: str) -> None:
        from .cli import render

        spec = self.build_spec(choice)
        script = self.prompt("Export a Python script as (e.g. myplot.py, Enter to skip)") or None
        if script and not script.endswith(".py"):
            script += ".py"
        show = self.yes("Open the plot window?", True)
        if not (show or spec.save or script):
            self.say("  nothing to do (no window, image or script)")
            return
        render(spec, [self.dat], show=show, script=script)
        for s in spec.save:
            self.say(f"  saved figure -> {s}")
        if script:
            self.say(f"  saved script -> {script}   (run: python {script})")
        self.say(f"  same plot from the command line:\n    {self.equivalent_command(spec, script, show)}\n")


def run_interactive(start_file: str | None = None, ode=None, names=None, kind="auto",
                    ask: Ask = input, say: Say = print) -> int:
    """Run the menu loop. Returns a process exit code."""
    s = Session(ask, say, ode=ode, names=names, kind=kind)
    say("xplot - XPPAUT .dat plotter   (type q at any prompt to quit)")
    try:
        s.choose_file(start_file)
        while True:
            choice = s.menu()
            if choice == "q":
                break
            if choice == "i":
                say("\n" + summarize(s.dat) + "\n")
            elif choice == "f":
                s.ode = None  # the next file may come from a different model
                s.choose_file()
            else:
                try:
                    s.plot(choice)
                except DatError as exc:
                    say(f"  error: {exc}")
    except (_Quit, KeyboardInterrupt, EOFError):
        say("")
    say("bye")
    return 0
