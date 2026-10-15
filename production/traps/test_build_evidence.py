"""Tests for build_evidence.py on a tiny synthetic workspace (run from production/traps: python3 -I -m unittest).

The fixture is built under a TemporaryDirectory: one task tree with three premises, campaigns that exercise miss
counting, void trials, a gated-out check, a credential-failure run found by the log scan (no ledger), a ledger
void-auth run, and a campaign whose version has no tree. Status rules are tested on synthetic units directly.
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_evidence as be  # noqa: E402

TASK = "a_f1_fake-task"


def check(value, gated=False):
    return {"value": value, "gated_out": gated, "error": None, "skipped": False, "status": "evaluated"}


def trial(tid, valid, checks):
    return {"id": tid, "valid": valid, "reward": 0.0,
            "steps": [{"name": "01-task", "valid": valid, "checks": {f"reward/{k}": v for k, v in checks.items()}}]}


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def campaign(root: Path, name: str, trials, log: str | None = None) -> None:
    d = root / "pipeline-artifacts/b4" / name
    write(d / "report.json", {"status": "finished", "trials": trials})
    if log is not None:
        write(d / "jobs/run/package__x/agent.log", log)


def build_fixture(root: Path) -> dict:
    tree = root / "envs-b6" / TASK
    write(tree / "task.toml", f'[task]\nname = "arena/{TASK}"\nversion = "1.0.0"\n')
    write(tree / "authoring/traps.json", {"schema": "b6/premises/2", "premises": [
        {"id": "P1", "family": "governing_vs_filing_key", "mechanism": "TWIN", "template": "T1", "decisive": True,
         "checks": ["c_slip"], "aimed_at": "both", "misreading": "keeps the slip on its printed key"},
        {"id": "P2", "family": "house_convention_numeric", "mechanism": "EXEMPLAR", "checks": ["c_round", "c_round2"],
         "aimed_at": "astra", "misreading": "rounds half-up"},
        {"id": "P3", "family": "caption_only_rule", "mechanism": "STATED", "template": "T2", "checks": ["c_stated"],
         "aimed_at": "fable", "misreading": "ignores the stated rule"}]})
    write(tree / "tests/checks.json", {"checks": [{"id": c, "kind": "objective", "weight": 25}
                                                  for c in ("c_slip", "c_round", "c_round2", "c_stated")]})
    ok = {"c_slip": check(1.0), "c_round": check(1.0), "c_round2": check(1.0), "c_stated": check(1.0)}
    # Fable final: t1 misses P1; t2 misses P2 (second check); t3 is a void trial that failed everything;
    # t4 has P1's only check gated out (not attempted) and passes the rest.
    campaign(root, f"{TASK}-1.0.0-final-fable", [
        trial("t1", True, {**ok, "c_slip": check(0.0)}),
        trial("t2", True, {**ok, "c_round2": check(0.0)}),
        trial("t3", False, {k: check(0.0) for k in ok}),
        trial("t4", True, {**ok, "c_slip": check(0.0, gated=True)}),
    ])
    # Astra final: two clean passes and one miss of P1.
    campaign(root, f"{TASK}-1.0.0-final-astra", [
        trial("a1", True, ok), trial("a2", True, ok), trial("a3", True, {**ok, "c_slip": check(0.0)})])
    # Astra pilot: every trial "valid" and failing, but the agent log shows a dead key: the run is void (log scan).
    campaign(root, f"{TASK}-1.0.0-pilot-astra", [trial(f"p{i}", True, {k: check(0.0) for k in ok}) for i in range(5)],
             log="HTTP 401 Unauthorized: token_invalidated")
    # Fable pilot that the ledger marks void-auth: dropped without being read.
    campaign(root, f"{TASK}-1.0.0-pilot-fable", [trial(f"q{i}", True, {k: check(0.0) for k in ok}) for i in range(5)])
    # Oracle passes everything; a campaign for a version with no tree is skipped and reported.
    campaign(root, f"{TASK}-1.0.0-pilot-oracle", [trial("o1", True, ok)])
    campaign(root, f"{TASK}-9.9.9-final-fable", [trial("z1", True, ok)])
    out = str(root / "pipeline-artifacts/b4" / f"{TASK}-1.0.0-pilot-fable")
    write(root / "research/batch4/ledger.json", {"entries": [
        {"id": "x", "task": str(tree), "name": TASK, "version": "1.0.0", "stage": "pilot", "digest": "d",
         "runs": {"fable": {"out": out, "state": "void-auth"}}}]})
    write(root / "research/batch4/b6/genuineness.md", f"- {TASK} 1.0.0 P1 audit: GENUINE (synthetic).\n")
    return {"tree": tree}


def side_files(base: Path) -> dict:
    mode_map = base / "mode-map.json"
    write(mode_map, {"label_to_mode": {}, "code_fallback": {"EXEMPLAR": "T2", "STATED": "D1"}, "overrides": [],
                     "lab_to_mode": {}})
    verdicts = base / "audit-verdicts.json"
    write(verdicts, {"verdicts": [
        {"task": TASK, "versions": "1.0.0", "premises": ["P1"], "verdict": "GENUINE",
         "source": "research/batch4/b6/genuineness.md", "quote": "P1 audit: GENUINE (synthetic)."},
        {"task": TASK, "versions": "1.0.0", "premises": ["P2"], "verdict": "BLIND-1.0",
         "source": "research/batch4/b6/genuineness.md", "quote": "this sentence is not in the source"}]})
    curated = base / "modes-curated.json"
    fields = {"aliases": [], "family": "record_reversal", "clock": False, "summary": "s.", "loopholes": [],
              "recipe": {"record": "", "anchors": "", "withheld": "", "dials": [], "conservation": "", "shields": ""},
              "proof_obligations": [], "hazards": [], "kills": [], "trace_signals": [], "domains": [], "example": ""}
    write(curated, {"modes": [{"id": i, "name": i, **fields} for i in ("T1", "T2", "D1")]})
    return {"map": mode_map, "verdicts": verdicts, "curated": curated}


class BuildFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.root = base / "root"
        build_fixture(cls.root)
        files = side_files(base / "side")
        cls.result = be.build(cls.root, None, files["map"], files["verdicts"])
        cls.out = base / "out"
        cls.modes_out = base / "out/modes-internal.json"
        cls.report = be.write_outputs(cls.result, cls.out, "20261015", files["curated"], cls.modes_out,
                                      "2026-10-15T00:00+05:30", cls.root)
        cls.units = {(u["task"], u["version"], u["premise"], u["stage"]): u for u in cls.result["units"]}

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def unit(self, prem, stage="final"):
        return self.units[(TASK, "1.0.0", prem, stage)]

    def test_miss_counting_and_gated_exclusion(self):
        p1, p2, p3 = self.unit("P1"), self.unit("P2"), self.unit("P3")
        # P1: t1 missed, t2 passed, t4 gated out (not counted), t3 void (not counted)
        self.assertEqual((p1["fable_misses"], p1["fable_runs"], p1["fable_gated"]), (1, 2, 1))
        # P2 is missed when ANY of its two checks fails (t2's second check)
        self.assertEqual((p2["fable_misses"], p2["fable_runs"]), (1, 3))
        self.assertEqual((p3["fable_misses"], p3["fable_runs"]), (0, 3))
        self.assertEqual((p1["astra_misses"], p1["astra_runs"]), (1, 3))

    def test_voids_excluded(self):
        self.assertEqual(self.unit("P1")["fable_void_trials"], 1)
        # both pilot runs are void (log scan; ledger void-auth): no pilot unit exists at all
        self.assertNotIn((TASK, "1.0.0", "P1", "pilot"), self.units)
        reasons = " | ".join(self.report["skips"])
        self.assertIn("void run (credential failure; log scan, not in ledger)", reasons)
        self.assertIn("void run (credential failure; ledger)", reasons)
        self.assertIn("no task tree with this name and version", reasons)
        self.assertEqual(self.result["runs_counted"], {"fable": 1, "astra": 1})

    def test_mode_assignment(self):
        self.assertEqual(self.unit("P1")["mode"], "T1")                      # template
        self.assertEqual(self.unit("P2")["mode"], "T2")                      # code fallback
        self.assertEqual(self.unit("P3")["mode"], "D1")                      # stated beats its template
        self.assertFalse(self.unit("P1")["oracle_missed"])

    def test_verdicts_and_citations(self):
        self.assertEqual(self.unit("P1")["verdict"], "GENUINE")
        cites = {tuple(c["premises"]): c["quote_found"] for c in self.result["verdict_checks"]}
        self.assertTrue(cites[("P1",)])
        self.assertFalse(cites[("P2",)])

    def test_outputs_and_pooling(self):
        rows = list(csv.DictReader(open(self.out / "INTERNAL-evidence-20261015.csv", encoding="utf-8")))
        self.assertEqual(len(rows), 3)
        pooled = json.loads((self.out / "INTERNAL-evidence-20261015-pooled.json").read_text(encoding="utf-8"))
        self.assertEqual(pooled["modes"]["T1"]["final"], {"fable": [1, 2], "astra": [1, 3]})
        modes = json.loads(self.modes_out.read_text(encoding="utf-8"))
        self.assertEqual(modes["schema"], "traplib/1")
        t1 = next(m for m in modes["modes"] if m["id"] == "T1")
        # pooled = all valid clean runs (here only finals survive: both pilot runs were void)
        self.assertEqual(t1["evidence"]["pooled"], {"fable": [1, 2], "astra": [1, 3]})
        self.assertEqual([r["stage"] for r in t1["evidence"]["internal"]], ["final"])
        self.assertEqual(t1["evidence"]["internal"][0]["audit"], "GENUINE")
        self.assertEqual(t1["status"], "promising")          # one task, n < 20
        self.assertIn("Measured here", t1["summary"])


def u(task, stage, f, a, verdict="", presumed=None):
    unit = {"task": task, "stage": stage, "verdict": verdict, "premise_obj": {"aimed_at": ""},
            "fable_misses": f[0], "fable_runs": f[1], "astra_misses": a[0], "astra_runs": a[1]}
    if presumed is None:
        presumed = verdict not in be.GENUINE and any(n >= 5 and k / n >= 0.9 for k, n in (f, a) if n)
    unit["presumed_ambiguous"] = presumed
    return unit


class StatusRuleTest(unittest.TestCase):
    def test_proven(self):
        s = be.compute_status([u("a", "final", (6, 10), (2, 10), "GENUINE"), u("b", "final", (5, 10), (3, 10), "GENUINE-soft")])
        self.assertEqual(s["status"], "proven")

    def test_genuine_counted_on_final_rows_only(self):
        s = be.compute_status([u("a", "final", (6, 10), (2, 10), "GENUINE"), u("b", "pilot", (5, 5), (3, 5), "GENUINE"),
                               u("b", "final", (5, 10), (3, 10))])
        self.assertEqual(s["genuine_tasks"], ["a"])
        self.assertEqual(s["status"], "promising")

    def test_pilot_rows_never_prove(self):
        s = be.compute_status([u("a", "pilot", (30, 30), (0, 30), "GENUINE"), u("b", "pilot", (20, 20), (0, 20), "GENUINE")])
        self.assertNotEqual(s["status"], "proven")

    def test_unaudited_100_percent_does_not_prove(self):
        # c (unaudited, Fable 10/10) is presumed ambiguous and leaves the proven pool; Astra 5/10 keeps it off bimodal
        s = be.compute_status([u("a", "final", (0, 10), (1, 10), "GENUINE"), u("b", "final", (1, 10), (0, 10), "GENUINE"),
                               u("c", "final", (10, 10), (5, 10))])
        self.assertEqual(s["final_strict"], {"fable": [1, 20], "astra": [1, 20]})
        self.assertEqual(s["status"], "promising")

    def test_genuine_task_must_have_bitten(self):
        s = be.compute_status([u("a", "final", (8, 10), (5, 10), "GENUINE"), u("b", "final", (0, 10), (0, 10), "GENUINE"),
                               u("c", "final", (7, 10), (6, 10))])
        self.assertEqual(s["genuine_tasks"], ["a"])
        self.assertEqual(s["status"], "promising")

    def test_dead(self):
        s = be.compute_status([u("a", "pilot", (0, 15), (1, 15)), u("b", "final", (1, 10), (0, 10))])
        self.assertEqual(s["status"], "dead")

    def test_dead_needs_n20_on_both(self):
        s = be.compute_status([u("a", "pilot", (0, 30), (0, 10))])
        self.assertEqual(s["status"], "promising")

    def test_bimodal(self):
        s = be.compute_status([u("a", "final", (10, 10), (0, 10), "GENUINE"), u("b", "final", (0, 10), (0, 10), "GENUINE"),
                               u("c", "final", (9, 10), (1, 10), "GENUINE")])
        self.assertEqual(s["status"], "bimodal")

    def test_ambiguous_units_leave_the_pool(self):
        s = be.compute_status([u("a", "final", (10, 10), (10, 10), "AMBIGUOUS"), u("b", "pilot", (0, 20), (0, 20))])
        self.assertEqual(s["final"], {"fable": [0, 0], "astra": [0, 0]})
        self.assertEqual(s["status"], "dead")


if __name__ == "__main__":
    unittest.main()
