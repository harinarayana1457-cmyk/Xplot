"""Regenerate the sample XPPAUT-format files in this folder.

    python sample_data/make_samples.py

The data comes from real numerical solutions, written in XPPAUT's layout:

* fhn.dat           FitzHugh-Nagumo simulation: t v w dv   (matches fhn.ode)
* fhn_diagram.dat   bifurcation in I, 'Write pts' layout: par y_hi y_lo type branch
* fhn_allinfo.dat   same diagram, 'All info' layout
* lorenz.dat        Lorenz attractor: t x y z              (matches lorenz.ode)

Only stable periodic orbits are included (found by simulation). AUTO would
also trace the unstable ones.
"""

from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
A, B, EPS = 0.7, 0.8, 0.08


def rk4(f, y0, dt, steps, every=1):
    ys = [np.array(y0, float)]
    y = ys[0].copy()
    for k in range(1, steps + 1):
        k1 = f(y)
        k2 = f(y + dt / 2 * k1)
        k3 = f(y + dt / 2 * k2)
        k4 = f(y + dt * k3)
        y = y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        if k % every == 0:
            ys.append(y.copy())
    return np.array(ys)


def write(name, rows):
    """Write rows the way XPPAUT does: space separated, no header."""
    with open(HERE / name, "w", newline="\n") as fh:
        for row in rows:
            fh.write(" ".join(f"{x:.8g}" for x in row) + " \n")


def fhn(I):
    return lambda y: np.array([y[0] - y[0] ** 3 / 3 - y[1] + I, EPS * (y[0] + A - B * y[1])])


def make_simulation():
    I, dt, every = 0.5, 0.05, 4
    sol = rk4(fhn(I), [-1.0, 1.0], dt, 4000, every)
    t = np.arange(len(sol)) * dt * every
    v, w = sol.T
    dv = v - v ** 3 / 3 - w + I
    write("fhn.dat", np.column_stack([t, v, w, dv]))


def make_lorenz():
    s, r, b = 10.0, 28.0, 8 / 3
    f = lambda y: np.array([s * (y[1] - y[0]), y[0] * (r - y[2]) - y[1], y[0] * y[1] - b * y[2]])
    dt, every = 0.005, 2
    sol = rk4(f, [1.0, 1.0, 1.0], dt, 8000, every)
    t = np.arange(len(sol)) * dt * every
    write("lorenz.dat", np.column_stack([t, sol]))


def make_diagrams():
    I_of_v = lambda v: v ** 3 / 3 - v + (v + A) / B   # equilibrium curve, monotonic in v
    v_eq = np.linspace(-1.35, 1.75, 160)
    pts, info = [], []
    for v in v_eq:
        I, w = I_of_v(v), (v + A) / B
        jac = np.array([[1 - v ** 2, -1.0], [EPS, -EPS * B]])
        ev = np.linalg.eigvals(jac)
        typ = 1 if np.all(ev.real < 0) else 2
        pts.append([I, v, v, typ, 1])
        info.append([typ, 1, I, A, 0.0, v, w, v, w, ev[0].real, ev[0].imag, ev[1].real, ev[1].imag])

    dt = 0.05
    for I in np.linspace(0.34, 1.41, 45):
        sol = rk4(fhn(I), [0.0, 0.0], dt, 14000)[-4000:]   # drop the transient
        v, w = sol.T
        if v.max() - v.min() < 1e-2:
            continue
        up = np.flatnonzero((v[:-1] < v.mean()) & (v[1:] >= v.mean()))
        if len(up) < 3:
            continue
        period = np.mean(np.diff(up)) * dt
        # non-trivial Floquet multiplier = exp(integral of the divergence over one period)
        cycle = v[up[-2]:up[-1]]
        mult = np.exp(np.sum(1 - cycle ** 2 - EPS * B) * dt)
        pts.append([I, v.max(), v.min(), 3, 2])
        info.append([3, 2, I, A, period, v.max(), w.max(), v.min(), w.min(), 1.0, 0.0, mult, 0.0])

    write("fhn_diagram.dat", pts)
    write("fhn_allinfo.dat", info)


if __name__ == "__main__":
    make_simulation()
    make_lorenz()
    make_diagrams()
    print("wrote fhn.dat, fhn_diagram.dat, fhn_allinfo.dat, lorenz.dat")
