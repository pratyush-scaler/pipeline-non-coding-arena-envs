"""plan_batch: per-seed rules, batch quotas, trace signals, determinism, briefs (2026-10-15).

    cd production/tools && python3 -I -m unittest          (discovery)
Plans against the synthetic library in production/traps/fixtures; everything is written under a TemporaryDirectory.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import paths  # noqa: E402
import plan_batch  # noqa: E402

sys.path.insert(0, str(paths.TRAPS))
import traplib  # noqa: E402

FIX = paths.TRAPS / "fixtures"


def run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            rc = plan_batch.main(argv)
        except SystemExit as exc:
            rc = exc.code
    return rc, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="plan-test-")
        self.d = Path(self.tmp.name)
        self.lib_path = self.library(FIX)

    def tearDown(self):
        self.tmp.cleanup()

    def library(self, src: Path, name: str = "lib") -> Path:
        lib, _ = traplib.merge(src)
        out = self.d / name
        out.mkdir()
        (out / "library.json").write_text(json.dumps(lib))
        return out / "library.json"

    def small_library(self, keep: set[str], name: str) -> Path:
        src = self.d / f"{name}-src"
        src.mkdir()
        for f in ("modes-internal.json", "modes-external.json", "modes-trace.json"):
            doc = json.loads((FIX / f).read_text())
            doc["modes"] = [m for m in doc["modes"] if m["id"] in keep]
            (src / f).write_text(json.dumps(doc))
        return self.library(src, name)

    def seeds(self, entries: list[dict], name: str = "seeds.json") -> Path:
        p = self.d / name
        p.write_text(json.dumps(entries))
        return p

    def plan(self, seeds: Path, out: str = "plan", *extra: str, lib: Path | None = None) -> tuple[int, dict, str]:
        rc, text = run([str(seeds), "--out", str(self.d / out), "--library", str(lib or self.lib_path), *extra])
        p = self.d / out / "plan.json"
        return rc, (json.loads(p.read_text()) if p.is_file() else {}), text


SEEDS = [{"seed": "seed-alpha", "domain": "engineering procurement for a workshop"},
         {"seed": "seed-beta", "domain": "hospitality scheduling"},
         {"seed": "seed-gamma", "domain": "school administration records"},
         {"seed": "seed-delta", "domain": "tax bills for a retail shop"}]


class PerSeedRules(Base):
    def test_every_plan_meets_the_rules(self):
        rc, plan, out = self.plan(self.seeds(SEEDS))
        self.assertEqual(rc, 0, out)
        lib = traplib.load(self.lib_path)
        for s in plan["seeds"]:
            self.assertEqual(s["status"], "planned", s)
            ms = [lib.modes[r["id"]] for r in s["modes"]]
            core = [m for m in ms if m["status"] in ("proven", "promising")]
            self.assertTrue(3 <= len(ms) <= 5, s)
            self.assertGreaterEqual(len(core), 3, s)  # a pilot-first mode is topped up with core modes
            self.assertTrue(any(m["aimed_at"] in ("fable", "both") for m in core), s)
            self.assertTrue(any(m["aimed_at"] in ("astra", "both") for m in core), s)
            self.assertLessEqual(sum(m["status"] in traplib.PILOT_FIRST for m in ms), 1, s)
            self.assertLessEqual(sum(m["clock"] for m in ms), 1, s)
            self.assertGreaterEqual(len({m["family"] for m in ms}), 2, s)
            self.assertNotIn("dead", {m["status"] for m in ms})
            self.assertFalse(any(traplib.dead_listed(m) for m in ms), s)  # D3 is promising on low_n: still never
            lead = s["modes"][0]
            self.assertEqual(lead["role"], "lead")
            self.assertIn(lead["status"], ("proven", "promising"))
            self.assertFalse(lead["clock"])
            self.assertEqual(lead["weight"], max(r["weight"] for r in s["modes"]))
            self.assertLessEqual(s["projected_free_share"], 0.40)
            self.assertTrue(all(r["weight"] <= 25 for r in s["modes"]))

    def test_batch_lead_quotas(self):
        rc, plan, out = self.plan(self.seeds(SEEDS))
        self.assertEqual(plan["quotas"]["cap"], 1)
        leads = [s["modes"][0] for s in plan["seeds"]]
        self.assertEqual(len({r["id"] for r in leads}), 4)
        self.assertEqual(len({r["family"] for r in leads}), 4)
        self.assertEqual(plan["quotas"]["violations"], [])
        eight = [{"seed": f"s{i}", "domain": d} for i, d in enumerate(["retail", "tax", "education", "finance",
                                                                       "hospitality", "engineering", "bills", "audit"])]
        rc, plan, out = self.plan(self.seeds(eight, "eight.json"), "plan8")
        self.assertEqual(plan["quotas"]["cap"], 2)
        self.assertTrue(all(v <= 2 for v in Counter(s["modes"][0]["family"] for s in plan["seeds"]).values()), out)
        self.assertTrue(all(v <= 2 for v in Counter(s["lead"] for s in plan["seeds"]).values()), out)
        self.assertEqual(rc, 0, out)

    def test_deterministic_and_seeded(self):
        sp = self.seeds(SEEDS)
        self.plan(sp, "a")
        self.plan(sp, "b")
        for rel in ["plan.json"] + [f"briefs/{s['seed']}.md" for s in SEEDS]:
            self.assertEqual((self.d / "a" / rel).read_bytes(), (self.d / "b" / rel).read_bytes(), rel)
        rc, plan, out = self.plan(sp, "c", "--seed", "7")
        self.assertEqual(rc, 0, out)
        self.assertEqual(plan["rng_seed"], 7)


class Signals(Base):
    def test_trace_traps_session_output_is_preferred(self):
        tt = self.d / "tt-gamma.json"  # trace_traps.py's per-session shape
        tt.write_text(json.dumps({"schema": "trace_traps/1", "session_id": "seed-gamma",
                                  "signals": [{"mapped_ids": ["D1", "T7"], "strength": 0.2}],
                                  "proposed_ids": [{"id": "T9", "weight": 2.5}, {"id": "R1", "weight": 1.1}]}))
        seeds = [dict(SEEDS[2], trace_traps=str(tt))]
        rc, plan, out = self.plan(self.seeds(seeds))
        s = plan["seeds"][0]
        ids = [r["id"] for r in s["modes"]]
        self.assertEqual(s["signals"], {"T9": 1.0, "R1": 0.44})
        self.assertIn("T9", ids)
        self.assertIn("R1", ids)
        self.assertEqual(next(r for r in s["modes"] if r["id"] == "R1")["role"], "pilot-first")
        self.assertNotIn("T7", s["signals"])  # per-signal mapped_ids lose to the session's proposed_ids

    def test_mode_mined_from_the_seed_counts_as_a_signal(self):
        rc, plan, out = self.plan(self.seeds([SEEDS[1]]))
        s = plan["seeds"][0]
        self.assertEqual(s["signals"].get("R2"), 1.0)
        self.assertIn("R2", [r["id"] for r in s["modes"]])

    def test_signals_from_shapes(self):
        lib = traplib.load(self.lib_path)
        summary = {"ranked": [{"session_id": "x", "proposed_ids": ["T2", "L4"]},
                              {"session_id": "y", "proposed_ids": ["T1"]}]}
        self.assertEqual(plan_batch.signals_from(summary, "x", lib), {"T2": 1.0, "T11": 1.0})
        keyed = {"y": [{"mode": "keying-slip", "confidence": 0.5}, {"trap": "T99"}, "nonsense"]}
        self.assertEqual(plan_batch.signals_from(keyed, "y", lib), {"T1": 0.5})
        self.assertEqual(plan_batch.signals_from({"proposed_ids": []}, "z", lib), {})


class Limits(Base):
    def test_infeasible_library_leaves_seeds_unplanned(self):
        lib = self.small_library({"T3", "T4", "T5", "L1"}, "fable-only")
        rc, plan, out = self.plan(self.seeds(SEEDS[:2]), lib=lib)
        self.assertEqual(rc, 1, out)
        self.assertTrue(all(s["status"] == "unplanned" for s in plan["seeds"]))
        self.assertIn("seed-alpha: unplanned", plan["quotas"]["violations"])
        brief = (self.d / "plan/briefs/seed-alpha.md").read_text()
        self.assertIn("UNPLANNED", brief)

    def test_quota_relaxed_only_when_nothing_else_fits(self):
        lib = self.small_library({"T1", "T3", "L1"}, "narrow")
        three = [{"seed": f"n{i}", "domain": "retail"} for i in range(3)]
        rc, plan, out = self.plan(self.seeds(three), lib=lib)
        self.assertEqual(rc, 1, out)
        self.assertEqual([s.get("relaxed") for s in plan["seeds"]], [False, False, True])
        self.assertEqual(sorted(s["lead"] for s in plan["seeds"][:2]), ["T1", "T3"])
        self.assertTrue(any("leads 2 tasks > cap 1" in v for v in plan["quotas"]["violations"]), plan["quotas"])
        self.assertIn("RELAXED", out)
        self.assertTrue(any("fewer than three proven/promising" in n for n in plan["seeds"][0]["notes"]))

    def test_bad_input(self):
        rc, _, out = self.plan(self.seeds({"seed": "x"}, "notlist.json"))
        self.assertEqual(rc, 2)
        rc, _, out = self.plan(self.seeds([SEEDS[0], SEEDS[0]], "dup.json"))
        self.assertEqual((rc, "repeats a seed" in out), (2, True))
        rc, _, out = self.plan(self.seeds(SEEDS), lib=self.d / "nowhere.json")
        self.assertEqual(rc, 2)
        self.assertIn("traplib.py", out)


class Briefs(Base):
    def test_brief_carries_table_skeleton_and_mode_sections(self):
        rc, plan, out = self.plan(self.seeds(SEEDS))
        s = plan["seeds"][0]
        md = (self.d / "plan/briefs" / f"{s['seed']}.md").read_text()
        self.assertIn("AUTHOR-BRIEF-B8.md", md)
        self.assertIn("| role | mode | name |", md)
        skel = json.loads(md.split("```json\n", 1)[1].split("```", 1)[0])
        self.assertEqual(skel["schema"], "b8/premises/1")
        self.assertEqual([p["template"] for p in skel["premises"]], [r["id"] for r in s["modes"]])
        self.assertTrue(all(p["decisive"] for p in skel["premises"]))
        for r in s["modes"]:
            self.assertIn(f"### {r['id']}: {r['name']}", md)


if __name__ == "__main__":
    unittest.main()
