"""design_lint's trap-library templates and B8 rules, the instruction-example scan, and b6ctl author-check (2026-10-15).

    cd production/tools && python3 -I -m unittest          (discovery; about two minutes, most of it author-check)

Every case runs on a TemporaryDirectory copy of templates/reference-task-suitcase-2.6.0 made B8-shaped (schema
b8/premises/1; P2 T2 astra, P5 T1 both, P7 T3 fable decisive = 62 of 100 points; one extra verbatim anchor for P2),
graded against the synthetic library built from production/traps/fixtures. design_lint and author-check run as
subprocesses under the verifier's python3.11 (paths.PY311), exactly as b6ctl runs them.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import b6ctl  # noqa: E402
import design_lint  # noqa: E402
import paths  # noqa: E402

sys.path.insert(0, str(paths.TRAPS))
import traplib  # noqa: E402

REF = paths.PRODUCTION / "templates/reference-task-suitcase-2.6.0"
EXTRA_ANCHOR = {"file": "defence/soobshchenie_nastavnika.md",
                "text": "Пришли мне цифры одним файлом, Полина перенесёт их на слайды."}
TMP: tempfile.TemporaryDirectory | None = None
LIB: Path | None = None


def setUpModule():
    global TMP, LIB
    TMP = tempfile.TemporaryDirectory(prefix="lint-b8-test-")
    out = Path(TMP.name) / "lib"
    lib, _ = traplib.merge(paths.TRAPS / "fixtures")
    out.mkdir()
    (out / "library.json").write_text(json.dumps(lib))
    LIB = out / "library.json"
    (Path(TMP.name) / "tmp").mkdir()


def tearDownModule():
    TMP.cleanup()


def b8_tree(name: str) -> Path:
    dest = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=TMP.name)) / "a_f1_suitcase-b8"
    shutil.copytree(REF, dest, ignore=shutil.ignore_patterns("__pycache__", "verification"))
    edit_traps(dest, b8_shape)
    return dest


def edit_traps(task: Path, fn) -> None:
    p = task / "authoring/traps.json"
    t = json.loads(p.read_text())
    fn(t)
    p.write_text(json.dumps(t, ensure_ascii=False, indent=1))


def prem(t: dict, pid: str) -> dict:
    return next(p for p in t["premises"] if p["id"] == pid)


def b8_shape(t: dict) -> None:
    t["schema"] = "b8/premises/1"
    for pid in ("P2", "P5", "P7"):
        prem(t, pid)["decisive"] = True
    prem(t, "P2")["anchors"].append(dict(EXTRA_ANCHOR))


def env(library: Path | str | None = None) -> dict:
    e = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_AUTH_TOKEN"}
    e.update({"ARENA_LIBRARY": str(library or LIB), "TMPDIR": str(Path(TMP.name) / "tmp")})
    return e


def lint(task: Path, *args: str, library=None, additivity: bool = False) -> tuple[int, dict, str]:
    rep = task.parent / "lint.json"
    proc = subprocess.run([paths.PY311, "-I", "-B", str(TOOLS / "design_lint.py"), str(task),
                           *(() if additivity else ("--no-additivity",)), *args, "--json", str(rep)],
                          capture_output=True, text=True, env=env(library), timeout=900)
    return proc.returncode, json.loads(rep.read_text()), proc.stdout + proc.stderr


def has(msgs: list[str], needle: str) -> bool:
    return any(needle in m for m in msgs)


@unittest.skipUnless(Path(paths.PY311).is_file(), f"verifier python not found at {paths.PY311} (set ARENA_PY311)")
class B8Rules(unittest.TestCase):
    def check_fail(self, mutate, needle: str, *args: str):
        task = b8_tree(self._testMethodName)
        edit_traps(task, mutate)
        rc, rep, out = lint(task, *args)
        self.assertEqual(rc, 1, out)
        self.assertTrue(has(rep["fails"], needle), rep["fails"])
        return rep

    def test_b8_reference_passes_with_additivity(self):
        rc, rep, out = lint(b8_tree("ref"), additivity=True)
        self.assertEqual(rc, 0, out)
        self.assertTrue(has(rep["oks"], "B8: 3 decisive premises over families"), rep["oks"])
        self.assertTrue(has(rep["oks"], "templates: trap library"), rep["oks"])
        self.assertTrue(has(rep["oks"], "additivity:"), rep["oks"])

    def test_too_few_decisive(self):
        self.check_fail(lambda t: prem(t, "P7").pop("decisive"), "B8: 2 decisive premise(s)")

    def test_one_library_family(self):
        def f(t):
            prem(t, "P2")["template"], prem(t, "P7")["template"] = "T5", "keying-slip"
        self.check_fail(f, "B8: decisive premises span 1 library family ['record_reversal']")

    def test_no_decisive_premise_aimed_at_astra(self):
        def f(t):
            for pid in ("P2", "P5", "P7"):
                prem(t, pid)["aimed_at"] = "fable"
                prem(t, pid).pop("target_model", None)
        self.check_fail(f, "B8: no decisive premise is aimed at astra")

    def test_aim_falls_back_to_the_mode(self):
        def f(t):  # no premise names astra; T2's own aim (astra) still covers it
            prem(t, "P2")["aimed_at"] = "see DIAL.md"
            prem(t, "P2").pop("target_model", None)
            prem(t, "P5")["aimed_at"] = "fable"
        task = b8_tree("aimfallback")
        edit_traps(task, f)
        rc, rep, out = lint(task)
        self.assertEqual(rc, 0, out)

    def test_anchor_files_other_than_the_quote(self):
        self.check_fail(lambda t: prem(t, "P7")["anchors"].pop(), "B8: P7 needs >= 2 verbatim anchors")

    def test_worked_figure_mode_needs_one_figure_anchor_only(self):
        def as_shipped(t):  # T2: the discriminating figure sits in the governing document (the quote's file) itself
            p = prem(t, "P2")
            p["anchors"] = [a for a in p["anchors"] if a != EXTRA_ANCHOR]
        task = b8_tree("figure1")
        edit_traps(task, as_shipped)
        rc, rep, out = lint(task)
        self.assertEqual(rc, 0, out)
        self.check_fail(lambda t: prem(t, "P2").__setitem__("anchors", []),
                        "B8: P2 (T2, convention from worked figures) needs >= 1 verbatim anchor")

    def test_clock_premise_heaviest(self):
        def f(t):
            prem(t, "P7")["template"] = "T10"  # a clock mode on the 24-point premise
        self.check_fail(f, "B8: 01-task: clock premise P7 is the heaviest premise")

    def test_projected_free_share(self):
        def f(t):
            prem(t, "P7").pop("decisive")
            prem(t, "P1").update({"decisive": True, "template": "T4"})
        self.check_fail(f, "B8: 01-task: projected free share 57%")

    def test_stated_mechanism_cannot_be_decisive(self):
        self.check_fail(lambda t: prem(t, "P7").update({"mechanism": "STATED"}), "P7 is decisive but its mechanism is STATED")

    def test_dead_template_fails(self):
        self.check_fail(lambda t: prem(t, "P7").update({"template": "D1"}), "is dead in the trap library")

    def test_d_ids_fail_whatever_their_status(self):
        rep = self.check_fail(lambda t: prem(t, "P7").update({"template": "D3"}), "is dead in the trap library (a D id")
        self.assertTrue(has(rep["fails"], "whatever its computed status promising"), rep["fails"])
        lib = json.loads(LIB.read_text())  # a T mode that carries a D id among its aliases is dead-listed too
        next(m for m in lib["modes"] if m["id"] == "T3")["aliases"] = ["D40"]
        alt = Path(tempfile.mkdtemp(prefix="dalias-", dir=TMP.name)) / "library.json"
        alt.write_text(json.dumps(lib))
        rc, rep, out = lint(b8_tree("dalias"), library=alt)
        self.assertEqual(rc, 1, out)
        self.assertTrue(has(rep["fails"], "P7: template T3 (T3: "), rep["fails"])

    def test_unknown_template_fails(self):
        self.check_fail(lambda t: prem(t, "P7").update({"template": "T99"}), "template 'T99' is not in the trap library")

    def test_missing_template_fails_under_b8_and_warns_under_b6(self):
        self.check_fail(lambda t: prem(t, "P7").pop("template"), "P7: decisive premise declares no trap-library template")
        task = b8_tree("b6schema")
        edit_traps(task, lambda t: (prem(t, "P7").pop("template"), t.update({"schema": "b6/premises/2"})))
        rc, rep, out = lint(task)
        self.assertTrue(has(rep["warns"], "P7: decisive premise declares no trap-library template"), rep)
        self.assertFalse(has(rep["fails"], "declares no trap-library template"), rep["fails"])

    def test_pilot_first_statuses_warn_only(self):
        for tpl, status in (("L1", "literature"), ("R1", "trace-derived"), ("T8", "bimodal")):
            task = b8_tree(f"pilot-{tpl}")
            edit_traps(task, lambda t: prem(t, "P7").update({"template": tpl}))
            rc, rep, out = lint(task)
            self.assertEqual(rc, 0, out)
            self.assertTrue(has(rep["warns"], f"is {status}, unproven in this harness; pilot first"), rep["warns"])

    def test_alias_and_promoted_id_resolve(self):
        def f(t):
            prem(t, "P5")["template"] = "keying-slip"
            prem(t, "P2")["template"] = "L4"  # promoted to T11 (temporal_anchor, astra)
        task = b8_tree("alias")
        edit_traps(task, f)
        rc, rep, out = lint(task)
        self.assertEqual(rc, 0, out)
        self.assertTrue(has(rep["oks"], "temporal_anchor"), rep["oks"])

    def test_older_schema_gets_b8_as_warnings_and_b8_flag_forces_them(self):
        def f(t):
            t["schema"] = "b6/premises/2"
            prem(t, "P7").pop("decisive")
        task = b8_tree("old")
        edit_traps(task, f)
        rc, rep, out = lint(task)
        self.assertEqual(rc, 0, out)
        self.assertTrue(has(rep["warns"], "B8: 2 decisive premise(s)"), rep["warns"])
        self.assertTrue(has(rep["warns"], "a warning for schema b6/premises/2"), rep["warns"])
        rc, rep, out = lint(task, "--b8")
        self.assertEqual(rc, 1, out)
        self.assertTrue(has(rep["fails"], "B8: 2 decisive premise(s)"), rep["fails"])

    def test_no_library_falls_back_to_the_builtin_catalogue(self):
        rc, rep, out = lint(b8_tree("nolib"), library=Path(TMP.name) / "absent/library.json")
        self.assertEqual(rc, 0, out)
        self.assertTrue(has(rep["oks"], "templates: built-in B7 catalogue (no trap library at"), rep["oks"])

    def test_unreadable_library_fails(self):
        bad = Path(TMP.name) / "corrupt-library.json"
        bad.write_text("{")
        rc, rep, out = lint(b8_tree("corrupt"), library=bad)
        self.assertEqual(rc, 1, out)
        self.assertTrue(has(rep["fails"], "the trap library is unreadable"), rep["fails"])

    def test_instruction_example_fails_under_b8_warns_under_b6(self):
        task = b8_tree("example")
        inst = task / "steps/01-task/instruction.md"
        inst.write_text(inst.read_text().replace("Write every count", "Name each design as printed, for example "
                                                 "«Почта до востребования». Write every count", 1))
        rc, rep, out = lint(task)
        self.assertEqual(rc, 1, out)
        self.assertTrue(has(rep["fails"], "leaks: instruction example"), rep["fails"])
        edit_traps(task, lambda t: t.update({"schema": "b6/premises/2"}))
        rc, rep, out = lint(task)
        self.assertEqual(rc, 0, out)
        self.assertTrue(has(rep["warns"], "leaks: instruction example"), rep["warns"])


class ExampleScan(unittest.TestCase):
    """design_lint.example_leaks in-process: digits, IDs and fixture values inside instruction examples."""

    def setUp(self):
        self.task = Path(tempfile.mkdtemp(prefix="exscan-", dir=TMP.name)) / "t"
        shutil.copytree(REF, self.task, ignore=shutil.ignore_patterns("__pycache__", "verification"))
        self.inst = self.task / "steps/01-task/instruction.md"
        self.traps = json.loads((self.task / "authoring/traps.json").read_text())

    def scan(self, sentence: str, traps: dict | None = None) -> list[str]:
        self.inst.write_text(self.inst.read_text() + "\n" + sentence + "\n")
        return design_lint.example_leaks(self.task, traps or self.traps)

    def test_reference_is_clean(self):
        self.assertEqual(design_lint.example_leaks(self.task, self.traps), [])

    def test_ids_and_numbers_in_examples(self):
        self.assertTrue(self.scan("Write identifiers such as H01 in upper case."))
        self.assertTrue(self.scan("Give the share as a whole number, e.g. 12."))
        self.assertTrue(self.scan("For example: ЧХ-30148 is one article."))

    def test_fixture_value_quoted_in_an_example(self):
        hits = self.scan("Name designs as printed, for instance «Огни побережья».")
        self.assertTrue(hits and "Огни побережья" in hits[0], hits)

    def test_field_names_and_leak_allow_are_exempt(self):
        self.assertEqual(self.scan("Some fields, such as `designs`, are lists."), [])
        traps = dict(self.traps, leak_allow=[{"value": "2025-W01", "reason": "the ISO week format the brief fixes"}])
        self.assertEqual(self.scan("Weeks are ISO weeks, for example 2025-W01.", traps), [])

    def test_no_example_cue_no_hit(self):
        self.assertEqual(self.scan("The as-of date is stated above; counts are integers."), [])


class AuthorCheckUnits(unittest.TestCase):
    def test_lint_hints(self):
        for msg, want in (("P7: template 'T99' is not in the trap library x", "traplib.py list"),
                          ("P7: template D1 (D1: x) is dead in the trap library; build", "proven/promising"),
                          ("B8: 01-task: projected free share 57% = 100 - decisive weight 43% (max 40%)", "25/21/17"),
                          ("leaks: instruction example 01-task: 'e.g. 12' carries ['12']: examples", "no number, ID"),
                          ("additivity: 01-task misread ('P2',): failed []", "ARENA_MISREAD"),
                          ("something new", "AUTHOR-BRIEF-B8.md")):
            self.assertIn(want, b6ctl.lint_hint(msg), msg)

    def test_dockerfile_rules(self):
        d = Path(tempfile.mkdtemp(prefix="docker-", dir=TMP.name))
        (d / "environment").mkdir()
        df = d / "environment/Dockerfile"
        self.assertEqual(b6ctl.dockerfile_problems(d), ["environment/Dockerfile is missing"])
        df.write_text("FROM x AS node\nFROM y\nCOPY --from=node /a /b\nCOPY files/ /app/environment/files/\n"
                      'COPY ["files/", "/app/x/"]\nRUN echo ok\n')
        self.assertEqual(b6ctl.dockerfile_problems(d), [])
        df.write_text("FROM y\nCOPY . /app/\nADD https://example.invalid/a.tgz /a\nCOPY files/ \\\n  ../tests /t/\n")
        probs = b6ctl.dockerfile_problems(d)
        self.assertEqual(len(probs), 3, probs)
        self.assertTrue(any("'.'" in p for p in probs) and any("../tests" in p for p in probs), probs)
        self.assertEqual(b6ctl.dockerfile_problems(REF), [])


@unittest.skipUnless(Path(paths.PY311).is_file(), f"verifier python not found at {paths.PY311} (set ARENA_PY311)")
class AuthorCheck(unittest.TestCase):
    def run_ac(self, task: Path) -> tuple[int, str]:
        e = env()
        e["ARENA_STATE"] = str(Path(TMP.name) / "state")
        proc = subprocess.run([sys.executable, "-I", "-B", str(TOOLS / "b6ctl.py"), "author-check", str(task)],
                              capture_output=True, text=True, env=e, timeout=1800)
        return proc.returncode, proc.stdout + proc.stderr

    def test_ready(self):
        rc, out = self.run_ac(b8_tree("ready"))
        self.assertEqual(rc, 0, out[-3000:])
        self.assertIn("AUTHOR-CHECK a_f1_suitcase-b8 2.6.0: READY", out)

    def test_not_ready_lists_every_item_with_a_fix(self):
        task = b8_tree("notready")
        edit_traps(task, lambda t: prem(t, "P7").update({"template": "D1"}))
        (task / "environment/Dockerfile").write_text((task / "environment/Dockerfile").read_text()
                                                     .replace("COPY files/ /app/environment/files/", "COPY . /app/"))
        (task / "verification").mkdir()
        (task / "verification/notes.txt").write_text("not a receipt\n")
        (task / "authoring/validate.py").unlink()
        rc, out = self.run_ac(task)
        self.assertEqual(rc, 1, out[-3000:])
        verdict = out[out.index("AUTHOR-CHECK a_f1_suitcase-b8 2.6.0: NOT READY"):]
        for needle in ("[lint] P7: template D1", "[validate] no authoring/validate.py", "[tree] verification/ is present",
                       "[docker] COPY copies ['.']"):
            self.assertIn(needle, verdict)
        n_items = len(re.findall(r"(?m)^\s+\d+\. \[", verdict))
        self.assertIn(f"NOT READY ({n_items} items)", verdict)
        self.assertEqual(n_items, len(re.findall(r"(?m)^\s+fix: \S", verdict)))


if __name__ == "__main__":
    unittest.main()
