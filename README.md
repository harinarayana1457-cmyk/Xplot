# xplot

Plot XPPAUT `.dat` output from the terminal: simulation runs and AUTO bifurcation diagrams. One command replaces the usual loadtxt/matplotlib boilerplate, and `--script` writes that boilerplate out for you when you want to customise a figure.

```text
xplot run.dat --phase v w
```

## Install

```bash
pip install -e .        # from this folder; gives you the `xplot` command
python -m xplot ...     # works too, if the Scripts folder isn't on PATH
```

Needs Python 3.9+, numpy and matplotlib.

## What it reads

XPPAUT `.dat` files have no header row, so xplot takes the column names from the `.ode` file. It looks for `run.ode` next to `run.dat`. If that's missing, it tries an `.ode` whose name is a prefix of the data file (`fhn_allinfo.dat` → `fhn.ode`), and then the only `.ode` in the folder. You can also pass `--ode model.ode` or `--names t,v,w`.

| Kind | Where it comes from in XPPAUT | Columns |
|---|---|---|
| simulation | *File → Write data*, `xppaut -silent` | `t`, state variables, `aux` quantities |
| diagram | AUTO *File → Write pts* | `par y_hi y_lo type branch` |
| allinfo | AUTO *File → All info* | `type branch par1 par2 period u_hi… u_lo… eigenvalues…` |

xplot detects the kind from the column layout. Use `--kind sim|diagram|allinfo` to override it.

## Usage

```bash
xplot                                     # interactive menu
xplot run.dat                             # every variable against t
xplot run.dat -y v w --subplots           # stacked panels
xplot run.dat --phase v w                 # phase plane
xplot lorenz.dat --phase x y z            # 3-D trajectory
xplot I0.5.dat I1.0.dat -y v              # overlay several runs
xplot diagram.dat                         # bifurcation diagram (Write pts)
xplot allinfo.dat -y w --par 2            # All info: w against par2
xplot allinfo.dat -y period               # period of the periodic branches
xplot run.dat -y v -o v.png -o v.pdf --no-show      # save only
xplot run.dat --phase v w --script phase.py         # also write a Python script
xplot run.dat --info                      # just print the summary
```

You can give columns by name (any case) or by index (`0` = first column). Every run prints a summary first: the source of the names, the parameter values from the `.ode`, and min/max/first/last for each column. Use `-q` to hide it.

Bifurcation diagrams use XPPAUT's colour scheme:

| Colour | Meaning |
|---|---|
| red line | stable equilibria |
| black dashed line | unstable equilibria |
| green filled dots | stable periodic orbits (max/min) |
| blue open dots | unstable periodic orbits (max/min) |

Other options: `--title --xlabel --ylabel --xlim LO HI --ylim LO HI --logx --logy --points --dpi`. Run `xplot -h` for the full list.

## Exported scripts

`--script plot.py` (or the matching question in the interactive menu) writes a self-contained script that needs only numpy and matplotlib. xplot draws every figure by running that same generated code, so the script reproduces exactly what you saw. In the interactive menu, xplot also prints the one-line command for each plot you make.

## Try it

```bash
cd sample_data
xplot fhn.dat --phase v w
xplot fhn_diagram.dat
xplot lorenz.dat --phase x y z
```

`sample_data/make_samples.py` regenerates these files from numerical solutions of FitzHugh-Nagumo and Lorenz, written in XPPAUT's format. The sample diagrams contain only stable periodic orbits, because the script finds them by simulation. A real AUTO run would also trace the unstable ones.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Layout

```text
xplot/
  cli.py          argument parsing, one-line mode
  interactive.py  menu mode
  datfile.py      loading, kind detection, column naming, summary
  odefile.py      reads variable/aux/parameter names from .ode files
  codegen.py      builds (and runs) the matplotlib script for each plot
sample_data/      example .ode/.dat files + generator
tests/
```
