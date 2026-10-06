"""Read an XPPAUT ``.ode`` file just far enough to name the columns of its output.

XPPAUT writes ``.dat`` files with no header row. Their column order is fixed by
the ``.ode`` file:

* simulation output ("Write data", ``xppaut -silent``): ``t``, the state
  variables in declaration order, then the ``aux`` quantities
* AUTO "All info" output: uses the state variables only

This is not a full XPP parser. It only recognises the declarations that create
output columns (plus ``par`` lines, so the summary can show parameter values).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_NAME = r"[A-Za-z_][\w\[\]\.]*"

# Declarations that create a state variable, in the forms XPPAUT accepts.
_STATE_PATTERNS = [
    re.compile(rf"^d\s*({_NAME})\s*/\s*dt\s*=", re.I),          # dx/dt = ...
    re.compile(rf"^({_NAME})\s*'\s*=", re.I),                   # x' = ...
    re.compile(rf"^({_NAME})\s*\(\s*t\s*\+\s*1\s*\)\s*=", re.I),  # x(t+1) = ...
    re.compile(rf"^volt\s+({_NAME})\s*=", re.I),                # volt x = ...
    re.compile(rf"^markov\s+({_NAME})\s", re.I),                # markov x 2
]
_AUX = re.compile(rf"^(?:aux|a)\s+({_NAME})\s*=", re.I)
_PAR = re.compile(r"^(?:p|par|param|parameter|parameters)\s+(.*)$", re.I)
_ASSIGN = re.compile(rf"({_NAME})\s*=\s*([^\s,]+)")
_RANGE = re.compile(r"^(?P<pre>[A-Za-z_]\w*)\[(?P<lo>-?\d+)\.\.(?P<hi>-?\d+)\](?P<post>\w*)$")
_BLOCK_START = re.compile(r"^%\s*\[\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*\]\s*$")
_INDEX_EXPR = re.compile(r"\[([^\[\]]*\bj\b[^\[\]]*)\]")


@dataclass
class OdeInfo:
    """Names extracted from an ``.ode`` file."""

    path: Path
    states: list[str] = field(default_factory=list)
    aux: list[str] = field(default_factory=list)
    params: dict[str, str] = field(default_factory=dict)

    @property
    def sim_columns(self) -> list[str]:
        """Column names of a simulation ``.dat`` file written by XPPAUT."""
        return ["t", *self.states, *self.aux]


def _expand(name: str) -> list[str]:
    """Expand XPP array names: ``x[1..3]`` -> ``x1, x2, x3``."""
    m = _RANGE.match(name)
    if not m:
        return [name]
    lo, hi = int(m["lo"]), int(m["hi"])
    step = 1 if hi >= lo else -1
    return [f"{m['pre']}{i}{m['post']}" for i in range(lo, hi + step, step)]


def _substitute_j(line: str, j: int) -> str:
    """Inside a ``%[a..b]`` block, turn ``x[j]`` / ``x[j+1]`` into ``x3`` / ``x4``."""

    def repl(m: re.Match) -> str:
        expr = m.group(1).replace(" ", "")
        if not re.fullmatch(r"[\dj+\-*]+", expr):
            return m.group(0)
        return str(eval(expr, {"__builtins__": {}}, {"j": j}))  # digits, j, + - * only

    return _INDEX_EXPR.sub(repl, line)


def _logical_lines(text: str) -> list[str]:
    """Strip comments, join ``\\`` continuations and expand ``%[a..b]`` blocks."""
    lines: list[str] = []
    pending = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        line = (pending + line).strip()
        pending = ""
        if line:
            lines.append(line)

    out: list[str] = []
    block: list[str] | None = None
    bounds = (0, 0)
    for line in lines:
        start = _BLOCK_START.match(line)
        if start and block is None:
            block, bounds = [], (int(start[1]), int(start[2]))
        elif line == "%" and block is not None:
            lo, hi = bounds
            for j in range(lo, hi + 1):
                out.extend(_substitute_j(b, j) for b in block)
            block = None
        elif block is not None:
            block.append(line)
        else:
            out.append(line)
    return out


def parse_ode(path: str | Path) -> OdeInfo:
    """Parse ``path`` and return the variable, aux and parameter names it declares."""
    path = Path(path)
    info = OdeInfo(path=path)
    for line in _logical_lines(path.read_text(encoding="utf-8", errors="replace")):
        if line.lower() == "done":
            break
        if m := _AUX.match(line):
            info.aux.extend(_expand(m[1]))
            continue
        if m := _PAR.match(line):
            for name, value in _ASSIGN.findall(m[1]):
                for n in _expand(name):
                    info.params[n] = value
            continue
        for pattern in _STATE_PATTERNS:
            if m := pattern.match(line):
                info.states.extend(_expand(m[1]))
                break
    return info


def find_ode_for(dat_path: str | Path) -> Path | None:
    """Guess the ``.ode`` file that produced ``dat_path``.

    Tries, in order: ``<stem>.ode`` next to the data file, the ``.ode`` whose
    name is the longest prefix of the data file's name (``fhn_allinfo.dat`` ->
    ``fhn.ode``), and finally the only ``.ode`` in the folder if there is just one.
    """
    dat_path = Path(dat_path)
    same_stem = dat_path.with_suffix(".ode")
    if same_stem.is_file():
        return same_stem
    candidates = sorted(dat_path.parent.glob("*.ode"))
    stem = dat_path.stem.lower()
    prefixed = [c for c in candidates if stem.startswith(c.stem.lower())]
    if prefixed:
        return max(prefixed, key=lambda c: len(c.stem))
    return candidates[0] if len(candidates) == 1 else None
