"""Command-line entry point: ``xplot FILE.dat [options]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .codegen import PlotSpec, build_script, run_script
from .datfile import KINDS, DatError, DatFile, load_dat, summarize

EXAMPLES = """\
examples:
  xplot                                   interactive menu (pick file, plot type, ...)
  xplot run.dat                           every variable against t
  xplot run.dat -y v w --subplots         v and w in stacked panels
  xplot run.dat --phase v w               phase plane (w against v)
  xplot lorenz.dat --phase x y z          3-D trajectory
  xplot a.dat b.dat -y v                  overlay v from two runs
  xplot diagram.dat                       AUTO bifurcation diagram ('Write pts')
  xplot allinfo.dat -y w --par 2          AUTO 'All info': w against par2
  xplot run.dat -y v -o v.png --no-show   save a PNG without opening a window
  xplot run.dat --phase v w --script phase.py   also write a Python script for the plot

Columns can be given by name (case-insensitive) or index (0 = first column).
Names come from the .ode file next to the data (or --ode / --names).
"""


def _split(values: list[str] | None) -> list[str]:
    """Accept both ``-y v w`` and ``-y v,w``."""
    out: list[str] = []
    for v in values or []:
        out.extend(p for p in v.replace(",", " ").split() if p)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xplot",
        description="Plot XPPAUT .dat output (simulations and AUTO bifurcation diagrams) "
        "from the terminal. Run with no arguments for an interactive menu.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("files", nargs="*", help=".dat file(s) written by XPPAUT")

    g = p.add_argument_group("reading the data")
    g.add_argument("--ode", metavar="FILE", help=".ode file to take column names from (default: auto-detect)")
    g.add_argument("--names", metavar="NAMES", help="column names, e.g. 't,v,w' (overrides the .ode file)")
    g.add_argument("--kind", choices=("auto", *KINDS), default="auto",
                   help="force the file type instead of auto-detecting it")

    g = p.add_argument_group("what to plot")
    g.add_argument("-x", metavar="COL", help="x-axis column for time series (default: first column, t)")
    g.add_argument("-y", nargs="+", metavar="COL",
                   help="column(s) to plot; for diagrams, the variable (or 'period')")
    g.add_argument("--phase", nargs="+", metavar="COL", help="phase plot: X Y (2-D) or X Y Z (3-D)")
    g.add_argument("--subplots", action="store_true", help="one panel per y column")
    g.add_argument("--points", action="store_true", help="draw points instead of lines")
    g.add_argument("--par", type=int, choices=(1, 2), default=1,
                   help="'All info' diagrams: put par1 or par2 on the x-axis")

    g = p.add_argument_group("appearance")
    g.add_argument("--title")
    g.add_argument("--xlabel")
    g.add_argument("--ylabel")
    g.add_argument("--xlim", nargs=2, type=float, metavar=("LO", "HI"))
    g.add_argument("--ylim", nargs=2, type=float, metavar=("LO", "HI"))
    g.add_argument("--logx", action="store_true")
    g.add_argument("--logy", action="store_true")

    g = p.add_argument_group("output")
    g.add_argument("-o", "--save", action="append", default=[], metavar="FILE",
                   help="save the figure (.png/.svg/.pdf); repeat for several formats")
    g.add_argument("--dpi", type=int, default=150, help="resolution for saved images (default 150)")
    g.add_argument("--script", metavar="FILE.py", help="write a standalone Python script that redraws the plot")
    g.add_argument("--no-show", action="store_true", help="don't open a plot window")
    g.add_argument("--info", action="store_true", help="only print the data summary")
    g.add_argument("-q", "--quiet", action="store_true", help="don't print the data summary")
    g.add_argument("-i", "--interactive", action="store_true", help="interactive menu (optionally starting with FILE)")
    p.add_argument("--version", action="version", version=f"xplot {__version__}")
    return p


def render(spec: PlotSpec, dats: list[DatFile], show: bool, script: str | None = None,
           headless: bool = False) -> None:
    """Write the optional script, then draw (and save) the figure."""
    for target in spec.save:
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    script_path = Path(script) if script else Path.cwd() / "xplot_plot.py"
    if script:
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(build_script(spec, dats, script_path, show=True), encoding="utf-8")
    run_script(build_script(spec, dats, script_path, show=show), script_path, headless=headless)


def spec_from_args(args: argparse.Namespace, dats: list[DatFile]) -> PlotSpec:
    """Translate parsed options into a ``PlotSpec`` with resolved column names."""
    d0 = dats[0]

    def resolve(key: str) -> str:
        for d in dats[1:]:
            d.resolve(key)  # raises if any overlaid file lacks the column
        return d0.resolve(key)
    spec = PlotSpec(
        subplots=args.subplots, points=args.points, par=args.par, title=args.title,
        xlabel=args.xlabel, ylabel=args.ylabel,
        xlim=tuple(args.xlim) if args.xlim else None, ylim=tuple(args.ylim) if args.ylim else None,
        logx=args.logx, logy=args.logy, save=list(args.save), dpi=args.dpi,
    )
    ys = _split(args.y)

    if d0.kind != "sim":
        if args.phase:
            raise DatError("--phase is for simulation output, not AUTO diagrams")
        spec.mode = "bifurcation"
        spec.y = [resolve(ys[0])] if ys else [d0.variables[0]]
        return spec

    phase = _split(args.phase)
    if phase:
        if len(phase) not in (2, 3):
            raise DatError("--phase takes 2 (X Y) or 3 (X Y Z) columns")
        cols = [resolve(c) for c in phase]
        spec.mode = "phase" if len(cols) == 2 else "phase3d"
        spec.x, spec.y = cols[0], [cols[1]]
        spec.z = cols[2] if len(cols) == 3 else None
        return spec

    spec.mode = "timeseries"
    spec.x = resolve(args.x) if args.x else d0.columns[0]
    spec.y = [resolve(c) for c in ys] if ys else [c for c in d0.columns if c != spec.x]
    return spec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    names = _split([args.names]) if args.names else None

    if args.interactive or not args.files:
        from .interactive import run_interactive

        return run_interactive(start_file=args.files[0] if args.files else None,
                               ode=args.ode, names=names, kind=args.kind)

    try:
        dats = [load_dat(f, kind=args.kind, ode=args.ode, names=names) for f in args.files]
        if not args.quiet:
            for d in dats:
                print(summarize(d), end="\n\n")
        if args.info:
            return 0
        spec = spec_from_args(args, dats)
        show = not args.no_show
        render(spec, dats, show=show, script=args.script, headless=not show)
    except DatError as exc:
        print(f"xplot: error: {exc}", file=sys.stderr)
        return 2

    for target in spec.save:
        print(f"saved figure  -> {target}")
    if args.script:
        print(f"saved script  -> {args.script}   (run: python {args.script})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
