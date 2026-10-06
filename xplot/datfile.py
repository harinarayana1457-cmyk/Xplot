"""Load XPPAUT ``.dat`` files and work out what kind of output they hold.

XPPAUT produces three kinds of ``.dat`` file:

``sim``      simulation output ("File > Write data" or ``xppaut -silent``):
             ``t x1 x2 ... aux1 ...``
``diagram``  AUTO "File > Write pts": ``par y_hi y_lo type branch``
``allinfo``  AUTO "File > All info":
             ``type branch par1 par2 period u_hi[1..n] u_lo[1..n] ev_re[1] ev_im[1] ...``

AUTO type codes: 1 stable equilibrium, 2 unstable equilibrium,
3 stable periodic orbit, 4 unstable periodic orbit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .odefile import OdeInfo, find_ode_for, parse_ode

KINDS = ("sim", "diagram", "allinfo")
KIND_LABELS = {
    "sim": "simulation (XPPAUT 'Write data' / -silent output)",
    "diagram": "AUTO bifurcation diagram ('Write pts')",
    "allinfo": "AUTO bifurcation diagram ('All info')",
}
TYPE_LABELS = {
    1: "stable equilibrium",
    2: "unstable equilibrium",
    3: "stable periodic orbit",
    4: "unstable periodic orbit",
}
COMMENT_CHARS = ("#", "%", ";", "!")


class DatError(ValueError):
    """Raised when a file can't be read as XPPAUT output."""


@dataclass
class DatFile:
    """A loaded ``.dat`` file plus everything needed to plot it."""

    path: Path
    data: np.ndarray
    kind: str
    columns: list[str]                 # one name per raw column
    variables: list[str]               # plottable y quantities
    load_kwargs: dict = field(default_factory=dict)
    ode: OdeInfo | None = None
    names_source: str = "generic"
    warnings: list[str] = field(default_factory=list)

    @property
    def n_rows(self) -> int:
        return self.data.shape[0]

    @property
    def n_cols(self) -> int:
        return self.data.shape[1]

    def resolve(self, key: str) -> str:
        """Map a user-supplied column name (any case) or index to its exact name."""
        pool = self.columns if self.kind == "sim" else self.variables
        for name in pool:
            if name == key:
                return name
        lowered = {n.lower(): n for n in pool}
        if key.lower() in lowered:
            return lowered[key.lower()]
        if re.fullmatch(r"\d+", key) and self.kind == "sim" and int(key) < self.n_cols:
            return self.columns[int(key)]
        raise DatError(f"unknown column '{key}' in {self.path.name}; choose from: {', '.join(pool)}")

    def index(self, name: str) -> int:
        """Raw column index of a resolved name."""
        return self.columns.index(name)


def _sniff(path: Path) -> tuple[dict, list[str] | None]:
    """Find the delimiter and an optional header row (XPP files have none)."""
    delimiter = None
    header: list[str] | None = None
    skip = 0
    with path.open(encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, start=1):
            text = line.strip()
            if not text or text.startswith(COMMENT_CHARS):
                continue
            if "," in text:
                delimiter = ","
            elif ";" in text:
                delimiter = ";"
            fields = [f.strip() for f in (text.split(delimiter) if delimiter else text.split())]
            try:
                [float(f) for f in fields if f]
            except ValueError:
                header, skip = fields, lineno
            break
        else:
            raise DatError(f"{path.name} contains no data")

    kwargs: dict = {"comments": list(COMMENT_CHARS) if delimiter != ";" else ["#", "%", "!"]}
    if delimiter:
        kwargs["delimiter"] = delimiter
    if skip:
        kwargs["skiprows"] = skip
    return kwargs, header


def _int_column(col: np.ndarray, lo: float = -np.inf, hi: float = np.inf) -> bool:
    return bool(
        np.all(np.isfinite(col)) and np.all(col == np.round(col)) and col.min() >= lo and col.max() <= hi
    )


def detect_kind(data: np.ndarray) -> str:
    """Guess which XPPAUT output ``data`` came from, using the column layout."""
    n = data.shape[1]
    if n == 5 and _int_column(data[:, 3], 1, 4) and _int_column(data[:, 4]):
        return "diagram"
    if n >= 9 and (n - 5) % 4 == 0 and _int_column(data[:, 0], 1, 4) and _int_column(data[:, 1]):
        return "allinfo"
    return "sim"


def _unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


def _fit(names: list[str], count: int, source: str, warnings: list[str], fill) -> list[str]:
    """Trim or pad ``names`` to ``count`` entries, noting any mismatch."""
    if len(names) != count:
        warnings.append(
            f"{source} gives {len(names)} names but the file has {count} columns; "
            + ("extra names ignored" if len(names) > count else "missing names filled in")
        )
    names = list(names[:count])
    names += [fill(i) for i in range(len(names), count)]
    return _unique(names)


def load_dat(
    path: str | Path,
    kind: str = "auto",
    ode: str | Path | None = None,
    names: list[str] | None = None,
) -> DatFile:
    """Load ``path``, detect its kind and give every column a name.

    Names come from ``names`` if given, then from the ``.ode`` file (``ode`` or
    one found next to the data), then from a header row, then generic names.
    """
    path = Path(path)
    if not path.is_file():
        raise DatError(f"file not found: {path}")
    load_kwargs, header = _sniff(path)
    try:
        data = np.loadtxt(path, ndmin=2, **load_kwargs)
    except ValueError as exc:
        raise DatError(f"could not read {path.name} as numeric columns: {exc}") from exc
    if data.size == 0:
        raise DatError(f"{path.name} contains no data")

    ode_info = None
    ode_path = Path(ode) if ode else (None if names else find_ode_for(path))
    if ode_path:
        if not ode_path.is_file():
            raise DatError(f".ode file not found: {ode_path}")
        ode_info = parse_ode(ode_path)

    if kind == "auto":
        kind = detect_kind(data)
        # A file whose width exactly matches the model's t+vars+aux is simulation output,
        # even if its columns happen to look like an AUTO diagram.
        if kind != "sim" and ode_info and ode_info.states and len(ode_info.sim_columns) == data.shape[1]:
            kind = "sim"
    elif kind not in KINDS:
        raise DatError(f"unknown kind '{kind}', expected one of {', '.join(KINDS)}")

    warnings: list[str] = []
    n = data.shape[1]
    source = "generic"

    if kind == "sim":
        if names:
            columns, source = _fit(names, n, "--names", warnings, lambda i: f"col{i}"), "--names"
        elif ode_info and ode_info.states:
            columns = _fit(ode_info.sim_columns, n, ode_info.path.name, warnings, lambda i: f"col{i}")
            source = ode_info.path.name
        elif header:
            columns, source = _fit(header, n, "header row", warnings, lambda i: f"col{i}"), "header row"
        else:
            columns = ["t"] + [f"x{i}" for i in range(1, n)]
        variables = columns[1:]

    elif kind == "diagram":
        if n != 5:
            raise DatError(f"'Write pts' diagrams have 5 columns, {path.name} has {n}")
        ylabel = names[0] if names else "y"
        columns = ["par", f"{ylabel}_hi", f"{ylabel}_lo", "type", "branch"]
        variables = [ylabel]
        source = "--names" if names else "generic"

    else:  # allinfo
        if n < 9 or (n - 5) % 4:
            raise DatError(f"'All info' files have 5 + 4n columns, {path.name} has {n}")
        nvar = (n - 5) // 4
        if names:
            variables, source = _fit(names, nvar, "--names", warnings, lambda i: f"x{i + 1}"), "--names"
        elif ode_info and ode_info.states:
            variables = _fit(ode_info.states, nvar, ode_info.path.name, warnings, lambda i: f"x{i + 1}")
            source = ode_info.path.name
        else:
            variables = [f"x{i}" for i in range(1, nvar + 1)]
        columns = (
            ["type", "branch", "par1", "par2", "period"]
            + [f"{v}_hi" for v in variables]
            + [f"{v}_lo" for v in variables]
            + [f"ev{i}_{part}" for i in range(1, nvar + 1) for part in ("re", "im")]
        )
        variables = variables + ["period"]

    return DatFile(
        path=path,
        data=data,
        kind=kind,
        columns=columns,
        variables=variables,
        load_kwargs=load_kwargs,
        ode=ode_info,
        names_source=source,
        warnings=warnings,
    )


def _fmt(x: float) -> str:
    return f"{x:.6g}"


def summarize(dat: DatFile) -> str:
    """Plain-text overview of a loaded file, for printing in the terminal."""
    lines = [
        f"File    : {dat.path}",
        f"Kind    : {KIND_LABELS[dat.kind]}",
        f"Size    : {dat.n_rows} rows x {dat.n_cols} columns",
        f"Names   : from {dat.names_source}",
    ]
    if dat.ode and dat.ode.params:
        params = ", ".join(f"{k}={v}" for k, v in dat.ode.params.items())
        lines.append(f"Params  : {params}")
    for w in dat.warnings:
        lines.append(f"Warning : {w}")
    lines.append("")

    d = dat.data
    if dat.kind == "sim":
        width = max(6, *(len(c) for c in dat.columns))
        lines.append(f"  {'#':>3}  {'column':<{width}}  {'min':>12}  {'max':>12}  {'first':>12}  {'last':>12}")
        for i, name in enumerate(dat.columns):
            col = d[:, i]
            lines.append(
                f"  {i:>3}  {name:<{width}}  {_fmt(np.nanmin(col)):>12}  {_fmt(np.nanmax(col)):>12}"
                f"  {_fmt(col[0]):>12}  {_fmt(col[-1]):>12}"
            )
    else:
        type_col, br_col, par_col = (3, 4, 0) if dat.kind == "diagram" else (0, 1, 2)
        types = d[:, type_col].astype(int)
        branches = sorted(set(d[:, br_col].astype(int).tolist()))
        par = d[:, par_col]
        lines.append(f"  parameter range : {_fmt(par.min())} .. {_fmt(par.max())}")
        lines.append(f"  branches        : {', '.join(map(str, branches))}")
        for code, label in TYPE_LABELS.items():
            count = int(np.sum(types == code))
            if count:
                lines.append(f"  {label:<24}: {count} points")
        lines.append(f"  plottable       : {', '.join(dat.variables)}")
    return "\n".join(lines)
