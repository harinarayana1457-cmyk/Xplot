"""Tests for xplot. Run with:  python -m unittest discover -s tests -v"""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402

from xplot.cli import main  # noqa: E402
from xplot.codegen import PlotSpec, build_script  # noqa: E402
from xplot.datfile import DatError, detect_kind, load_dat, summarize  # noqa: E402
from xplot.interactive import run_interactive  # noqa: E402
from xplot.odefile import find_ode_for, parse_ode  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "sample_data"


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text):
        p = self.tmp / name
        p.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
        return p


class OdeParserTests(TempDirTest):
    def test_all_declaration_forms(self):
        ode = self.write("m.ode", r"""
            # comment line
            v' = -v + I   # inline comment
            dw/dt = eps*(v - w)
            n(t+1) = n + 1
            volt u = 1 + int{exp(-t)#u}
            x[1..3]' = -x[j]
            aux curr = I*v
            a power = v*w
            par I=0.5, eps=0.08 gam = 2
            p k=1
            long' = 1 + \
                2
            init v=1
            done
            late' = 1
            """)
        info = parse_ode(ode)
        self.assertEqual(info.states, ["v", "w", "n", "u", "x1", "x2", "x3", "long"])
        self.assertEqual(info.aux, ["curr", "power"])
        self.assertEqual(info.params, {"I": "0.5", "eps": "0.08", "gam": "2", "k": "1"})
        self.assertEqual(info.sim_columns[0], "t")

    def test_percent_block(self):
        ode = self.write("b.ode", """
            %[1..3]
            u[j]' = u[j-1] - u[j]
            %
            """)
        self.assertEqual(parse_ode(ode).states, ["u1", "u2", "u3"])

    def test_find_ode(self):
        self.write("fhn.ode", "v'=1\n")
        self.write("other.ode", "x'=1\n")
        self.assertEqual(find_ode_for(self.tmp / "fhn.dat").name, "fhn.ode")
        self.assertEqual(find_ode_for(self.tmp / "fhn_allinfo.dat").name, "fhn.ode")
        self.assertIsNone(find_ode_for(self.tmp / "output.dat"))


class LoaderTests(TempDirTest):
    def test_kind_detection(self):
        sim = np.column_stack([np.linspace(0, 1, 5), np.random.rand(5, 4)])
        diag = np.array([[0.1, 1, 1, 1, 1], [0.2, 2, 0, 3, 2]], float)
        allinfo = np.array([[1, 1, 0.1, 0.7, 0, 1, 2, 1, 2, -1, 0, -2, 0]], float)
        self.assertEqual(detect_kind(sim), "sim")
        self.assertEqual(detect_kind(diag), "diagram")
        self.assertEqual(detect_kind(allinfo), "allinfo")

    def test_names_from_ode_and_mismatch_warning(self):
        self.write("m.ode", "v'=1\nw'=2\naux z=v\n")
        self.write("m.dat", "0 1 2 3\n0.1 1 2 3\n")
        d = load_dat(self.tmp / "m.dat")
        self.assertEqual(d.columns, ["t", "v", "w", "z"])
        self.assertEqual(d.names_source, "m.ode")
        self.assertEqual(d.resolve("V"), "v")
        self.assertEqual(d.resolve("2"), "w")
        with self.assertRaises(DatError):
            d.resolve("nope")

        self.write("short.dat", "0 1.5 2.5 3.5 4.5\n")
        d = load_dat(self.tmp / "short.dat", ode=self.tmp / "m.ode")
        self.assertEqual(d.columns, ["t", "v", "w", "z", "col4"])
        self.assertTrue(d.warnings)

    def test_ode_width_overrides_diagram_guess(self):
        # 5 integer columns look like 'Write pts', but the model says t + 4 variables
        self.write("m4.ode", "a'=1\nb'=1\nc'=1\nd'=1\n")
        self.write("m4.dat", "0 1 2 3 4\n1 1 2 3 4\n")
        self.assertEqual(load_dat(self.tmp / "m4.dat").kind, "sim")
        self.assertEqual(load_dat(self.tmp / "m4.dat", kind="diagram").kind, "diagram")

    def test_generic_names_and_explicit_names(self):
        self.write("output.dat", "0 1 2\n1 2 3\n")
        self.assertEqual(load_dat(self.tmp / "output.dat").columns, ["t", "x1", "x2"])
        d = load_dat(self.tmp / "output.dat", names=["time", "a", "b"])
        self.assertEqual(d.columns, ["time", "a", "b"])

    def test_errors(self):
        with self.assertRaises(DatError):
            load_dat(self.tmp / "missing.dat")
        self.write("empty.dat", "# nothing\n")
        with self.assertRaises(DatError):
            load_dat(self.tmp / "empty.dat")
        self.write("ragged.dat", "1 2 3\n1 2\n")
        with self.assertRaises(DatError):
            load_dat(self.tmp / "ragged.dat")

    def test_samples(self):
        sim = load_dat(SAMPLES / "fhn.dat")
        self.assertEqual((sim.kind, sim.columns), ("sim", ["t", "v", "w", "dv"]))
        diag = load_dat(SAMPLES / "fhn_diagram.dat")
        self.assertEqual(diag.kind, "diagram")
        info = load_dat(SAMPLES / "fhn_allinfo.dat")
        self.assertEqual((info.kind, info.variables), ("allinfo", ["v", "w", "period"]))
        for d in (sim, diag, info):
            self.assertIn("Kind", summarize(d))


class PlotTests(TempDirTest):
    def run_cli(self, *args):
        out = self.tmp / "out.png"
        code = main([*map(str, args), "-o", str(out), "--no-show", "-q"])
        self.assertEqual(code, 0)
        self.assertGreater(out.stat().st_size, 1000)
        out.unlink()

    def test_every_plot_mode(self):
        self.run_cli(SAMPLES / "fhn.dat")
        self.run_cli(SAMPLES / "fhn.dat", "-y", "v,w", "--subplots", "--title", "FHN")
        self.run_cli(SAMPLES / "fhn.dat", "--phase", "v", "w", "--points")
        self.run_cli(SAMPLES / "lorenz.dat", "--phase", "x", "y", "z")
        self.run_cli(SAMPLES / "fhn.dat", SAMPLES / "fhn.dat", "-y", "v")
        self.run_cli(SAMPLES / "fhn_diagram.dat")
        self.run_cli(SAMPLES / "fhn_allinfo.dat", "-y", "w")
        self.run_cli(SAMPLES / "fhn_allinfo.dat", "-y", "period", "--par", "1", "--logy")

    def test_bad_requests_return_error_code(self):
        self.assertEqual(main([str(SAMPLES / "fhn.dat"), "-y", "nope", "--no-show", "-q"]), 2)
        self.assertEqual(main([str(SAMPLES / "fhn_diagram.dat"), "--phase", "a", "b", "--no-show", "-q"]), 2)
        self.assertEqual(main([str(SAMPLES / "fhn.dat"), "--phase", "v", "--no-show", "-q"]), 2)

    def test_exported_script_runs_standalone(self):
        script = self.tmp / "sub" / "phase.py"
        png = self.tmp / "sub" / "phase.png"
        code = main([str(SAMPLES / "fhn.dat"), "--phase", "v", "w", "--script", str(script),
                     "-o", str(png), "--no-show", "-q"])
        self.assertEqual(code, 0)
        png.unlink()
        source = script.read_text()
        self.assertIn("plt.show()", source)
        self.assertNotIn("xplot", source.split('"""', 2)[2])  # no dependency on xplot itself
        env = dict(os.environ, MPLBACKEND="Agg")
        subprocess.run([sys.executable, str(script)], check=True, env=env, cwd=self.tmp)
        self.assertTrue(png.exists())

    def test_script_mixing_kinds_rejected(self):
        sim = load_dat(SAMPLES / "fhn.dat")
        diag = load_dat(SAMPLES / "fhn_diagram.dat")
        with self.assertRaises(DatError):
            build_script(PlotSpec(mode="timeseries", x="t", y=["v"]), [sim, diag], self.tmp / "s.py")


class InteractiveTests(TempDirTest):
    def run_session(self, answers, start):
        feed = iter(answers)
        out = []
        code = run_interactive(start_file=str(start), ask=lambda _: next(feed),
                               say=lambda *a, **k: out.append(" ".join(map(str, a))))
        return code, "\n".join(out)

    def test_phase_plot_with_script(self):
        png, script = self.tmp / "p.png", self.tmp / "p.py"
        answers = ["2", "", "", "My title", str(png), str(script), "n", "q"]
        code, text = self.run_session(answers, SAMPLES / "fhn.dat")
        self.assertEqual(code, 0)
        self.assertTrue(png.exists() and script.exists())
        self.assertIn("--phase v w", text)

    def test_bad_column_is_reasked(self):
        png = self.tmp / "t.png"
        answers = ["1", "", "bogus", "v", "", str(png), "", "n", "q"]
        code, text = self.run_session(answers, SAMPLES / "fhn.dat")
        self.assertIn("unknown column 'bogus'", text)
        self.assertTrue(png.exists())

    def test_bifurcation(self):
        png = self.tmp / "b.png"
        answers = ["1", "w", "2", "", str(png), "", "n", "q"]
        self.run_session(answers, SAMPLES / "fhn_allinfo.dat")
        self.assertTrue(png.exists())


if __name__ == "__main__":
    unittest.main()
