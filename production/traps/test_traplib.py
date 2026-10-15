"""traplib: build, validation refusals, promotion, resolve/status_of, CLI (2026-10-15).

    cd production/traps && python3 -I -m unittest          (discovery; -I keeps the cwd off sys.path otherwise)
Builds the synthetic sources in fixtures/ into TemporaryDirectory copies; nothing outside them is written.
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import traplib  # noqa: E402

FIX = HERE / "fixtures"


def run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            rc = traplib.main(argv)
        except SystemExit as exc:
            rc = exc.code
    return rc, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="traplib-test-")
        self.src = Path(self.tmp.name) / "src"
        self.out = Path(self.tmp.name) / "out"
        shutil.copytree(FIX, self.src)

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, fname: str, fn) -> None:
        p = self.src / fname
        doc = json.loads(p.read_text())
        fn(doc)
        p.write_text(json.dumps(doc))

    def mode(self, doc: dict, mid: str) -> dict:
        return next(m for m in doc["modes"] if m["id"] == mid)

    def build(self, *extra) -> tuple[int, str]:
        return run(["build", "--src", str(self.src), "--out", str(self.out), *extra])


class Build(Base):
    def test_fixture_builds_strict_and_renders(self):
        rc, out = self.build("--strict")
        self.assertEqual(rc, 0, out)
        lib = json.loads((self.out / "library.json").read_text())
        self.assertEqual(lib["schema"], "traplib/1")
        self.assertEqual(len(lib["modes"]), 20)
        self.assertEqual({s for s in lib["sources"]}, {"internal", "external", "trace"})
        md = (self.out / "TRAP-LIBRARY.md").read_text()
        self.assertIn("## Summary by family and status", md)
        self.assertIn("| **all** | 2 | 9 | 1 | 4 | 2 | 2 | 20 |", md)
        self.assertIn("- **Dead list:** never a decisive template (status computed on a small sample: low_n)", md)
        for m in lib["modes"]:
            self.assertIn(f"## {m['id']}: {m['name']}", md)
            self.assertIn(f"(#{traplib._anchor(m)})", md)

    def test_build_is_deterministic(self):
        self.build()
        first = {p.name: p.read_bytes() for p in self.out.iterdir()}
        shutil.rmtree(self.out)
        self.build()
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_promotion_supersedes_the_literature_mode(self):
        self.build()
        lib = traplib.load(self.out / "library.json")
        self.assertNotIn("L4", lib.modes)
        self.assertEqual(lib.resolve("L4")["id"], "T11")
        self.assertEqual(lib.data["superseded"], {"L4": "T11"})
        self.assertTrue(any(r["source"] == "Fixture Bench D" for r in lib.modes["T11"]["evidence"]["external"]))

    def test_missing_sources_are_skipped(self):
        (self.src / "modes-external.json").unlink()
        (self.src / "modes-trace.json").unlink()
        rc, out = self.build()
        self.assertEqual(rc, 0, out)
        self.assertIn("modes-trace.json: not present, skipped", out)
        lib = traplib.load(self.out / "library.json")
        self.assertEqual(set(lib.data["sources"]), {"internal"})
        self.assertIsNone(lib.resolve("L1"))
        self.assertEqual(lib.resolve("L4")["id"], "T11")  # its own alias still resolves


class Refusals(Base):
    """Every schema violation refuses the build and writes nothing."""

    def refused(self, fname, fn, needle):
        self.edit(fname, fn)
        rc, out = self.build()
        self.assertEqual(rc, 1, out)
        self.assertIn("BUILD REFUSED", out)
        self.assertIn(needle, out)
        self.assertFalse((self.out / "library.json").exists())

    def test_duplicate_id(self):
        self.refused("modes-internal.json", lambda d: d["modes"].append(dict(self.mode(d, "T1"))), "duplicate id T1")

    def test_prefix_not_allowed_in_source(self):
        def f(d):
            self.mode(d, "T9")["id"] = "L9"
        self.refused("modes-internal.json", f, "id prefix L is not allowed in modes-internal.json")

    def test_status_not_allowed_in_source(self):
        def f(d):
            self.mode(d, "R1")["status"] = "proven"
        self.refused("modes-trace.json", f, "status proven is not allowed in modes-trace.json")

    def test_bad_id_pattern(self):
        def f(d):
            self.mode(d, "T9")["id"] = "T9a"
        self.refused("modes-internal.json", f, "does not match ^[TLRD][0-9]+$")

    def test_family_enum(self):
        def f(d):
            self.mode(d, "T3")["family"] = "changed_premise"
        self.refused("modes-internal.json", f, "family 'changed_premise' is not one of")

    def test_aimed_and_loophole_enums(self):
        def f(d):
            self.mode(d, "T3")["aimed_at"] = "gpt"
            self.mode(d, "T4")["loopholes"] = ["L-nothing"]
        self.edit("modes-internal.json", f)
        rc, out = self.build()
        self.assertEqual(rc, 1)
        self.assertIn("aimed_at 'gpt'", out)
        self.assertIn("loophole 'L-nothing'", out)

    def test_name_too_long(self):
        def f(d):
            self.mode(d, "T3")["name"] = "x" * 81
        self.refused("modes-internal.json", f, "at most 80 characters")

    def test_missing_required_field(self):
        def f(d):
            del self.mode(d, "T3")["summary"]
        self.refused("modes-internal.json", f, "missing required field summary")

    def test_clock_must_be_bool(self):
        def f(d):
            self.mode(d, "T3")["clock"] = "no"
        self.refused("modes-internal.json", f, "clock must be true or false")

    def test_alias_shadowing_an_id(self):
        def f(d):
            self.mode(d, "T2")["aliases"] = ["T1"]
        self.refused("modes-internal.json", f, "alias 'T1' is the id of another mode")

    def test_alias_on_two_modes(self):
        def f(d):
            self.mode(d, "T2")["aliases"] = ["keying-slip"]
        self.refused("modes-internal.json", f, "alias 'keying-slip' names two modes")

    def test_bad_evidence_pair(self):
        def f(d):
            self.mode(d, "T3")["evidence"]["pooled"]["fable"] = [5, 3]
        self.refused("modes-internal.json", f, "evidence.pooled.fable must be [k, n]")

    def test_bad_internal_row(self):
        def f(d):
            self.mode(d, "T3")["evidence"]["internal"][0]["stage"] = "screen"
        self.refused("modes-internal.json", f, "stage 'screen' is not pilot or final")

    def test_recipe_shape(self):
        def f(d):
            self.mode(d, "T3")["recipe"]["dials"] = "one notch"
        self.refused("modes-internal.json", f, "recipe.dials must be a list of strings")

    def test_literature_with_measured_rows(self):
        def f(d):
            self.mode(d, "L1")["evidence"]["internal"] = [{"task": "x", "stage": "final", "fable": [1, 10]}]
        self.refused("modes-external.json", f, "re-issue it as a T mode")

    def test_header_mismatch(self):
        def f(d):
            d["source"] = "internal"
            d["schema"] = "traplib/0"
        self.edit("modes-external.json", f)
        rc, out = self.build()
        self.assertEqual(rc, 1)
        self.assertIn("schema 'traplib/0' is not 'traplib/1'", out)
        self.assertIn("source 'internal' must be 'external'", out)

    def test_invalid_json(self):
        (self.src / "modes-trace.json").write_text("{not json")
        rc, out = self.build()
        self.assertEqual(rc, 1)
        self.assertIn("modes-trace.json: not valid JSON", out)

    def test_d_id_must_be_dead_unless_low_n(self):
        def f(d):
            del self.mode(d, "D3")["low_n"]
        self.refused("modes-internal.json", f, "D id with status 'promising'")

    def test_low_n_is_a_bool(self):
        def f(d):
            self.mode(d, "D3")["low_n"] = "yes"
        self.refused("modes-internal.json", f, "low_n must be true or false")

    def test_two_promotions_of_one_mode(self):
        def f(d):
            self.mode(d, "T7")["aliases"] = ["L4"]
        self.refused("modes-internal.json", f, "L4 is claimed by two promoted modes")


class StatusRules(Base):
    def unproven(self, d):
        self.mode(d, "T2")["evidence"]["internal"] = self.mode(d, "T2")["evidence"]["internal"][:1]

    def test_status_disagreement_warns_then_refuses_under_strict(self):
        self.edit("modes-internal.json", self.unproven)
        rc, out = self.build()
        self.assertEqual(rc, 0, out)
        self.assertIn("WARN  status: T2: proven needs >= 2 GENUINE final tasks", out)
        rc, out = self.build("--strict")
        self.assertEqual(rc, 1)
        self.assertIn("T2: proven needs", out)

    def test_dead_needs_both_models_low(self):
        def f(d):
            self.mode(d, "D1")["evidence"]["pooled"]["astra"] = [9, 25]
        self.edit("modes-internal.json", f)
        rc, out = self.build("--strict")
        self.assertEqual(rc, 1)
        self.assertIn("D1: dead needs a pooled miss rate <= 0.05 on BOTH models", out)

    def test_bimodal_shape(self):
        def f(d):
            self.mode(d, "T8")["evidence"]["internal"][1]["fable"] = [5, 10]
        self.edit("modes-internal.json", f)
        rc, out = self.build("--strict")
        self.assertEqual(rc, 1)
        self.assertIn("T8: bimodal needs per-task final miss rates", out)


class Api(Base):
    def setUp(self):
        super().setUp()
        rc, out = self.build()
        self.assertEqual(rc, 0, out)
        self.lib = traplib.load(self.out / "library.json")

    def test_resolve_and_status_of(self):
        self.assertEqual(self.lib.resolve("keying-slip")["id"], "T1")
        self.assertEqual(self.lib.resolve("t2")["id"], "T2")
        self.assertIsNone(self.lib.resolve("T99"))
        self.assertEqual(self.lib.status_of("D1"), "dead")
        self.assertEqual(traplib.status_of("L4", self.lib), "promising")
        self.assertEqual(traplib.resolve("R1", self.lib)["status"], "trace-derived")

    def test_dead_listed(self):
        self.assertTrue(traplib.dead_listed(self.lib.resolve("D1")))
        self.assertTrue(traplib.dead_listed(self.lib.resolve("decoys")))  # D3: promising on a low_n sample
        self.assertEqual(self.lib.status_of("D3"), "promising")
        self.assertFalse(traplib.dead_listed(self.lib.resolve("T1")))
        self.assertTrue(traplib.dead_listed(dict(self.lib.resolve("T1"), aliases=["D40"])))

    def test_select(self):
        self.assertEqual({m["id"] for m in self.lib.select(status="proven")}, {"T1", "T2"})
        fable = {m["id"] for m in self.lib.select(aimed_at="fable")}
        self.assertIn("T1", fable)  # both counts for each model
        self.assertNotIn("T2", fable)
        self.assertEqual({m["id"] for m in self.lib.select(family="rule_scope")}, {"T9"})

    def test_load_refuses_other_schema(self):
        bad = self.out / "bad.json"
        bad.write_text(json.dumps({"schema": "traplib/0", "modes": []}))
        with self.assertRaises(ValueError):
            traplib.load(bad)

    def test_cli(self):
        lib = str(self.out / "library.json")
        rc, out = run(["resolve", "L4", "--lib", lib])
        self.assertEqual((rc, out.strip()), (0, "T11 promising"))
        rc, out = run(["resolve", "nope", "--lib", lib])
        self.assertEqual(rc, 1)
        rc, out = run(["show", "keying-slip", "--lib", lib])
        self.assertEqual(rc, 0)
        self.assertTrue(out.startswith("## T1: keying slip"))
        rc, out = run(["show", "T1", "--json", "--lib", lib])
        self.assertEqual(json.loads(out)["family"], "record_reversal")
        rc, out = run(["list", "--status", "dead", "--lib", lib])
        self.assertEqual(rc, 0)
        self.assertIn("2 mode(s)", out)
        rc, out = run(["list", "--aimed-at", "astra", "--family", "temporal_anchor", "--lib", lib])
        self.assertIn("T10", out)  # aimed at both
        self.assertIn("T11", out)
        rc, out = run(["list", "--lib", str(self.out / "missing.json")])
        self.assertEqual(rc, 2)
        self.assertIn("traplib.py build", out)


if __name__ == "__main__":
    unittest.main()
