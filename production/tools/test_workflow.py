"""b6ctl's workflow subcommands (doctor, new, prompt, run, next, ship), pool-free (2026-10-15).

    cd production/tools && python3 -I -B -m unittest test_workflow       (also run by `-m unittest discover -s .`)

Every test builds its own fake workspace under one TemporaryDirectory: paths.TASKS, STATE, GATES, ARTIFACTS, TC_RUNS
and the ledger point there, and the task is a copy of production/templates/reference-task-suitcase-2.6.0. External
effects sit behind a subprocess guard: measure.py (launch, launch --rerun-void, status) is a fake that edits the fake
ledger, tc_path.py launch/pull and assemble_b4_zip.py follow a per-test script, and coder or harbor raise. The key
preflight's HTTP call and the Coder CLI are faked at b6ctl._http_status / _coder / _coder_bin. signal_gate.py runs for
real on synthetic report.json files; census_answers.py runs for real in CensusReal (it needs the verifier python3.11)
and is a stub elsewhere.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import b6ctl  # noqa: E402
import paths  # noqa: E402

REF = paths.PRODUCTION / "templates/reference-task-suitcase-2.6.0"
NAME, VER = "a_f1_suitcase-cover-matrix-check", "2.6.0"
REAL_RUN = subprocess.run
CP = subprocess.CompletedProcess
TMP: tempfile.TemporaryDirectory | None = None
PLACEHOLDER = re.compile(r"\{(TASK_DIR|TASK|VERSION|REPO|SCRATCH|NOTES|PLAN|AUDIT_REPORT|CAMPAIGNS)\}")


def setUpModule():
    global TMP
    TMP = tempfile.TemporaryDirectory(prefix="test-workflow-")


def tearDownModule():
    TMP.cleanup()


def done(valid: int, full: int, void: int = 0) -> dict:
    return {"state": "done", "valid": valid, "full": full, "void": void, "pass_at_1": full / valid,
            "mean_reward": (full + 0.5 * (valid - full)) / valid}


def voided(valid: int) -> dict:
    return {"state": "void-auth", "valid": valid, "full": 0, "void": 0, "pass_at_1": 0.0, "mean_reward": 0.0,
            "error": "agent log files show a credential failure"}


ORACLE = {"state": "done", "valid": 1, "full": 1, "void": 0, "pass_at_1": 1.0, "mean_reward": 1.0}
NOP = {"state": "done", "valid": 1, "full": 0, "void": 0, "pass_at_1": 0.0, "mean_reward": 0.0}
RUNNING = {"state": "running"}
CENSUS_STUB = "from pathlib import Path\nprint(Path(__file__).with_suffix('.out').read_text(), end='')\n"
CLEAN_ROWS = ("    -final-fable aaaaaaa 01-task reward=0.5 diff_fields=['f.json.k: ref=1 got=2']\n"
              "    -final-astra bbbbbbb 01-task reward=1.0 diff_fields=none\n")


def write_report(d: Path, r: dict, ident: str | None) -> None:
    """A report.json shaped like a benchmark's: r['valid'] valid trials (r['full'] at 1.0), r['void'] invalid ones."""
    d.mkdir(parents=True, exist_ok=True)
    trials = []
    for i in range(r.get("valid", 0)):
        rew = 1.0 if i < r.get("full", 0) else 0.0 if r["state"] == "void-auth" else 0.4 + 0.1 * (i % 3)
        trials.append({"id": f"{d.name}-t{i}", "valid": True, "reward": rew,
                       "steps": [{"name": "01-task", "reward": rew, "valid": True, "checks": {}}]})
    trials += [{"id": f"{d.name}-v{i}", "valid": False, "reward": 0.0, "steps": []} for i in range(r.get("void", 0))]
    (d / "report.json").write_text(json.dumps({"status": "finished", "trials": trials,
                                               "task_validation": {"artifact_sha256": ident}}))


class Workspace(unittest.TestCase):
    """A fake workspace per test, with every pool, harbor and packaging call faked behind a subprocess guard."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ws-", dir=TMP.name)).resolve()
        state = self.root / "state"
        for obj, attr, val in ((paths, "TASKS", self.root / "envs-b6"), (paths, "STATE", state),
                               (paths, "GATES", state / "gates"), (paths, "ARTIFACTS", self.root / "artifacts"),
                               (paths, "TC_RUNS", state / "tc_path_runs.json"), (b6ctl, "LEDGER", state / "ledger.json"),
                               (b6ctl, "STALE", state / "stale-receipts"), (b6ctl, "STATUS_LOCK", state / ".wait.lock"),
                               (b6ctl, "RUN_EVERY", 0), (b6ctl, "SHIP_POLL", 0), (b6ctl, "KEYS", self.root / "keys.env"),
                               (b6ctl, "PROMPTS", self.root / "prompts"), (b6ctl, "CENSUS", self.root / "census_stub.py"),
                               (b6ctl, "_http_status", lambda url, headers: self.http_code),
                               (subprocess, "run", self.guard)):
            p = mock.patch.object(obj, attr, val)
            p.start()
            self.addCleanup(p.stop)
        env = mock.patch.dict(os.environ, {"SHELL": "/bin/bash"})
        env.start()
        self.addCleanup(env.stop)
        for k in ("ANTHROPIC_AUTH_TOKEN", "CLAUDE_SCRATCH", "ARENA_POOLS"):
            os.environ.pop(k, None)
        self.http_code = "200"
        (self.root / "keys.env").write_text("ANTHROPIC_API_KEY=wf-test-anthropic-value-0001\n"
                                            "OPENAI_API_KEY=wf-test-openai-value-0002\n")
        (self.root / "keys.env").chmod(0o600)
        (self.root / "census_stub.py").write_text(CENSUS_STUB)
        self.census_rows(CLEAN_ROWS)
        paths.ARTIFACTS.mkdir(parents=True)
        self.task = paths.TASKS / NAME
        shutil.copytree(REF, self.task, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        self.ident = b6ctl._identity(self.task)
        self.calls: list[tuple] = []
        self.outcomes: dict[tuple[str, str], list[dict]] = {}
        self.tc_pulls: list[str] = []
        self.asm: dict = {}

    # ---- fakes ---------------------------------------------------------------------------------------------------
    def guard(self, cmd, *a, **k):
        argv = [str(c) for c in cmd] if isinstance(cmd, (list, tuple)) else [str(cmd)]
        s = " ".join(argv)
        if "measure.py" in s:
            return self.fake_measure(argv)
        if "tc_path.py" in s:
            return self.fake_tc(argv)
        if "assemble_b4_zip.py" in s:
            return self.fake_asm(argv)
        if re.search(r"(^|[/ ])(coder|harbor)( |$)", s):
            raise AssertionError(f"blocked external command: {s}")
        if "signal_gate.py" in s and "capture_output" not in k and "stdout" not in k:
            p = REAL_RUN(cmd, *a, capture_output=True, text=True, **k)  # into the test's captured stdout
            print(p.stdout + p.stderr, end="")
            return p
        return REAL_RUN(cmd, *a, **k)

    def cdir(self, stage: str, model: str, rerun: int = 0) -> Path:
        return paths.ARTIFACTS / (f"{NAME}-{VER}-{stage}-{model}" + (f"-rerun{1792000000 + rerun}" if rerun else ""))

    def ledger(self) -> dict:
        return json.loads(b6ctl.LEDGER.read_text()) if b6ctl.LEDGER.is_file() else {"entries": []}

    def save(self, led: dict) -> None:
        b6ctl.LEDGER.parent.mkdir(parents=True, exist_ok=True)
        b6ctl.LEDGER.write_text(json.dumps(led))

    def entry(self, stage: str, runs: dict, **extra) -> dict:
        """A ledger entry whose runs already finished; each run's report.json is written too."""
        e = {"id": f"{NAME}-{VER}-{stage}@{stage}", "task": str(self.task), "name": NAME, "version": VER,
             "stage": stage, "digest": "d", "ws": "arena-calib-9", "launched_at": 1 if stage == "pilot" else 2,
             "runs": {}, **extra}
        for m, r in runs.items():
            out = self.cdir(stage, m)
            e["runs"][m] = {**r, "out": str(out)}
            if r.get("state") in ("done", "void-auth"):
                write_report(out, r, self.ident)
        led = self.ledger()
        led["entries"].append(e)
        self.save(led)
        return e

    def fake_measure(self, argv: list[str]) -> CP:
        args = argv[next(i for i, c in enumerate(argv) if c.endswith("measure.py")) + 1:]
        self.calls.append(("measure", *args))
        led = self.ledger()
        if args[0] == "launch":
            task, stage = args[1], args[args.index("--stage") + 1]
            if "--rerun-void" in args:
                m = args[args.index("--rerun-void") + 1]
                e = [x for x in led["entries"] if x["task"] == task and x["stage"] == stage][-1]
                e.setdefault("void_history", []).append({m: e["runs"][m]})
                e["runs"][m] = {"state": "launched", "out": str(self.cdir(stage, m, len(e["void_history"])))}
            else:
                models = (("oracle", "nop") if stage == "pilot" else ()) + b6ctl.MODELS
                led["entries"].append({"id": f"{NAME}-{VER}-{stage}@{len(led['entries'])}", "task": task, "name": NAME,
                                       "version": VER, "stage": stage, "digest": "d", "ws": "arena-calib-9",
                                       "launched_at": len(led["entries"]) + 1,
                                       "runs": {m: {"state": "launched", "out": str(self.cdir(stage, m))}
                                                for m in models}})
        elif args[0] == "status":
            for e in led["entries"]:
                for m, r in e["runs"].items():
                    if r["state"] in ("launched", "running"):
                        nxt = self.outcomes[(e["stage"], m)].pop(0)
                        r.update(nxt)
                        if nxt["state"] in ("done", "void-auth"):
                            write_report(Path(r["out"]), nxt, self.ident)
        self.save(led)
        return CP(argv, 0, "", "")

    def fake_tc(self, argv: list[str]) -> CP:
        i = next(i for i, c in enumerate(argv) if c.endswith("tc_path.py"))
        op, task, ws = argv[i + 1], argv[i + 2], argv[i + 3]
        self.calls.append(("tc", op, task, ws))
        if op == "launch":
            runs = json.loads(paths.TC_RUNS.read_text()) if paths.TC_RUNS.is_file() else {}
            runs[task] = {"ws": ws, "run": "R1"}
            paths.TC_RUNS.parent.mkdir(parents=True, exist_ok=True)
            paths.TC_RUNS.write_text(json.dumps(runs))
            return CP(argv, 0, f"tasks-check {Path(task).name} on {ws}: R1\n", "")
        step = self.tc_pulls.pop(0) if self.tc_pulls else "no receipt yet"
        if step.startswith("install:"):
            status = step.split(":", 1)[1]
            (Path(task) / "verification").mkdir(exist_ok=True)
            (Path(task) / "verification/harbor-tasks-check.json").write_text(json.dumps(
                {"status": status, "artifact_sha256": b6ctl._identity(Path(task))}))
            return CP(argv, 0, f"installed {status}\n", "")
        return CP(argv, 1, step + "\n", "")

    def fake_asm(self, argv: list[str]) -> CP:
        args = argv[next(i for i, c in enumerate(argv) if c.endswith("assemble_b4_zip.py")) + 1:]
        staged = Path(args[0])
        opts = dict(zip(args[1::2], args[2::2]))
        self.calls.append(("asm", *args))
        self.asm = {"staged": staged, "staged_was_dir": staged.is_dir(),
                    "staged_identity": b6ctl._identity(staged) if staged.is_dir() else None, **opts}
        out = Path(opts["-o"])
        out.mkdir(parents=True, exist_ok=True)
        z = out / f"{staged.name}__01-task.zip"
        z.write_bytes(b"PK fake")
        return CP(argv, 0, f"Fable 5.1: pass@1 0.30 (3/10 valid, 0 void); steps: 01-task 3/10\n{z}: OK (7 bytes)\n", "")

    # ---- helpers -------------------------------------------------------------------------------------------------
    def cli(self, *argv) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                rc = b6ctl.main([str(a) for a in argv])
            except SystemExit as exc:
                rc = exc.code
        return rc, out.getvalue(), err.getvalue()

    def census_rows(self, text: str) -> None:
        (self.root / "census_stub.out").write_text(text)

    def measured(self, kind: str) -> list[tuple]:
        return [c for c in self.calls if c[0] == "measure" and c[1] == "launch"
                and (("--rerun-void" in c) == (kind == "rerun"))]

    def stage_of(self) -> tuple[str, str]:
        rc, out, _ = self.cli("next", self.task)
        self.assertEqual(rc, 0, out)
        return re.search(r"(?m)^STAGE\s+(\S+)", out).group(1), out


# --------------------------------------------------------------------------------------------------------- doctor
class Doctor(Workspace):
    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(paths.TRAPS))
        import traplib
        lib, _ = traplib.merge(paths.TRAPS / "fixtures")
        (self.root / "library.json").write_text(json.dumps(lib))
        dump = self.root / "dump"
        (dump / "sessions/s1").mkdir(parents=True)
        (dump / "sessions/s2").mkdir()
        self.pools = {"arena-calib-2": "running", "arena-calib-3": "stopped", "arena-calib-4": "running"}
        self.whoami = (0, "Coder is running at https://coder.invalid, You're authenticated as tester.")
        for obj, attr, val in ((paths, "LIBRARY", self.root / "library.json"), (paths, "PY", sys.executable),
                               (b6ctl, "_py_version", lambda exe: "3.11.9" if exe == b6ctl.PY else "3.12.1"),
                               (b6ctl, "_coder_bin", lambda: "/fake/bin/coder-cli"), (b6ctl, "_coder", self.fake_coder)):
            p = mock.patch.object(obj, attr, val)
            p.start()
            self.addCleanup(p.stop)
        os.environ["ARENA_DUMP"] = str(dump)
        os.environ["ARENA_POOLS"] = ",".join(self.pools)

    def fake_coder(self, *args):
        self.calls.append(("coder", *args))
        self.assertIn(args[0], ("whoami", "list"), "doctor may only run read-only Coder commands")
        if args[0] == "whoami":
            return CP(args, self.whoami[0], self.whoami[1], "")
        rows = [{"name": n, "latest_build": {"status": s}} for n, s in self.pools.items()]
        return CP(args, 0, "version mismatch: client v2.1, server v2.2\n" + json.dumps(rows), "")

    def lines(self, out: str) -> dict[str, str]:
        return {l[5:]: l[:4].strip() for l in out.splitlines() if l[:4].strip() in ("OK", "WARN", "FAIL")}

    def test_all_clear_except_a_stopped_pool(self):
        rc, out, _ = self.cli("doctor")
        self.assertEqual(rc, 0, out)
        tags = self.lines(out)
        self.assertNotIn("FAIL", tags.values(), out)
        for want in ("login shell /bin/bash", "ANTHROPIC_AUTH_TOKEN not set", "keys.env mode 600",
                     "key preflight ANTHROPIC_API_KEY 200, OPENAI_API_KEY 200", ".venv python 3.12.1",
                     "verifier python 3.11.9", "pool arena-calib-2 running", "pool arena-calib-4 running"):
            self.assertTrue(any(k.startswith(want) and v == "OK" for k, v in tags.items()), (want, out))
        self.assertTrue(any(k.startswith("dump ") and "(2 sessions)" in k for k in tags), out)
        self.assertTrue(any(k.startswith("trap library ") and "modes" in k for k in tags), out)
        self.assertRegex(out, r"OK   pipeline code sha [0-9a-f]{64}")
        self.assertRegex(out, r"WARN pool arena-calib-3 is stopped -- fix: starting a pool needs the user's go-ahead")
        self.assertNotIn("wf-test-", out, "doctor printed a key")
        self.assertTrue(all(c[1] in ("whoami", "list") for c in self.calls if c[0] == "coder"))
        self.assertIn("DOCTOR: no FAIL", out)

    def test_every_failure_has_a_fix_and_fails_the_exit_code(self):
        os.environ["SHELL"] = "/bin/zsh"
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "wf-test-session-token"
        b6ctl.KEYS.chmod(0o644)
        self.http_code = "401"
        self.pools = {"arena-calib-2": "stopped", "arena-calib-3": "stopped", "arena-calib-4": "stopped"}
        with mock.patch.object(b6ctl, "_py_version", lambda exe: None), \
                mock.patch.object(paths, "LIBRARY", self.root / "missing.json"), \
                mock.patch.object(b6ctl, "_dump", mock.Mock(side_effect=SystemExit("No trace dump configured."))):
            rc, out, _ = self.cli("doctor")
        self.assertEqual(rc, 1, out)
        self.assertIn("WARN login shell /bin/zsh -- fix: use bash -c", out)
        for want in ("FAIL ANTHROPIC_AUTH_TOKEN is set in this environment -- fix: launch with env -u ANTHROPIC_AUTH_TOKEN",
                     "FAIL keys.env mode 644 -- fix: chmod 600",
                     "FAIL key preflight ANTHROPIC_API_KEY 401, OPENAI_API_KEY 401 -- fix: a human fixes keys.env",
                     "FAIL .venv python missing", "-- fix: uv sync",
                     "FAIL verifier python3.11 not found", "-- fix: uv python install 3.11 (or set ARENA_PY311",
                     "FAIL trap library", "-- fix: python3 -I production/traps/traplib.py build",
                     "FAIL dump: No trace dump configured. -- fix: ./arena dump --set <path>",
                     "FAIL no pool is running"):
            self.assertIn(want, out)
        fails = [l for l in out.splitlines() if l.startswith("FAIL")]
        self.assertTrue(fails and all(" -- fix: " in l for l in fails), out)
        self.assertNotIn("wf-test-", out, "doctor printed a key or the token")

    def test_coder_missing_or_logged_out(self):
        with mock.patch.object(b6ctl, "_coder_bin", lambda: None):
            rc, out, _ = self.cli("doctor")
        self.assertEqual(rc, 1)
        self.assertIn("FAIL Coder CLI not found -- fix: install it", out)
        self.whoami = (1, "You are not logged in.")
        rc, out, _ = self.cli("doctor")
        self.assertEqual(rc, 1)
        self.assertIn("FAIL Coder CLI is not logged in -- fix: ./arena coder login", out)
        self.assertFalse([c for c in self.calls if c[0] == "coder" and c[1] == "list"])

    def test_no_pools_configured_fails_with_the_own_pool_rule(self):
        del os.environ["ARENA_POOLS"]
        rc, out, _ = self.cli("doctor")
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL ARENA_POOLS is not set -- fix: export ARENA_POOLS=<your Coder workspace>", out)
        self.assertNotIn("pool arena-calib-2", out)

    def test_pools_come_from_arena_pools(self):
        os.environ["ARENA_POOLS"] = "arena-calib-4,arena-calib-7"
        rc, out, _ = self.cli("doctor")
        self.assertEqual(rc, 1, out)
        self.assertIn("OK   pool arena-calib-4 running", out)
        self.assertIn("FAIL pool arena-calib-7 not in `coder list`", out)
        self.assertNotIn("arena-calib-2", out)


# ------------------------------------------------------------------------------------------------------------ new
class New(Workspace):
    def test_scaffold(self):
        plan = self.root / "brief.md"
        plan.write_text("# plan for seed X\n- T1 lead\n")
        seed = "0199aaaa-1111-7222-8333-944455556666"
        rc, out, _ = self.cli("new", "supplier-credit-review", "--seed", seed, "--plan", plan)
        self.assertEqual(rc, 0, out)
        t = paths.TASKS / "a_f1_supplier-credit-review"
        meta = tomllib.loads((t / "task.toml").read_text())
        self.assertEqual((meta["task"]["name"], meta["task"]["version"]), ("arena/a_f1_supplier-credit-review", "1.0.0"))
        self.assertEqual(meta["metadata"]["faithfulness"], "F1")
        self.assertEqual(meta["metadata"]["source_trace"], seed)
        self.assertEqual(meta["metadata"]["source_seeds"], [f"{seed}::<seed index>"])
        self.assertEqual(meta["steps"][0]["name"], "01-task")
        traps = json.loads((t / "authoring/traps.json").read_text())
        self.assertEqual(traps, {"schema": "b8/premises/1", "premises": [], "coverage_checks": [], "leak_allow": []})
        self.assertEqual((t / "authoring/PLAN.md").read_text(), plan.read_text())
        prov = json.loads((t / "provenance/ledger.json").read_text())
        self.assertEqual((prov["schema"], prov["source_trace"]), ("arena/provenance-ledger/1", seed))
        self.assertTrue((t / "tests/_arena_runtime/contracts.py").is_file() and (t / "environment/Dockerfile").is_file())
        self.assertEqual(b6ctl.dockerfile_problems(t), [])
        self.assertIn(f"NEXT    {b6ctl.ME} prompt author {t}", out)
        rc, out, _ = self.cli("new", "supplier-credit-review")
        self.assertEqual(rc, 3, out)
        self.assertIn("REFUSED", out)
        rc, out, _ = self.cli("next", t)
        self.assertEqual(rc, 0, out)
        self.assertIn("STAGE   author-check", out)

    def test_level_and_refusals(self):
        rc, out, _ = self.cli("new", "deck-check", "--level", "f2")
        self.assertEqual(rc, 0, out)
        meta = tomllib.loads((paths.TASKS / "a_f2_deck-check/task.toml").read_text())
        self.assertEqual((meta["task"]["name"], meta["metadata"]["faithfulness"]), ("arena/a_f2_deck-check", "F2"))
        self.assertIn("<full session uuid", meta["metadata"]["source_trace"])
        self.assertFalse((paths.TASKS / "a_f2_deck-check/authoring/PLAN.md").exists())
        for bad in ("Bad_Slug", "-x", "a--b", "x y"):
            rc, out, _ = self.cli("new", bad)
            self.assertEqual(rc, 2, (bad, out))
        rc, out, _ = self.cli("new", "ok-slug", "--seed", "bad seed;rm")
        self.assertEqual(rc, 2, out)
        rc, out, _ = self.cli("new", "ok-slug", "--plan", self.root / "nope.md")
        self.assertEqual(rc, 2, out)
        rc, out, _ = self.cli("new", "x", "--level", "f3")
        self.assertEqual(rc, 2)
        self.save({"entries": [{"name": "a_f1_taken", "version": "1.0.0", "stage": "pilot", "runs": {}}]})
        rc, out, _ = self.cli("new", "taken")
        self.assertEqual(rc, 3, out)
        self.assertIn("already taken", out)
        self.assertFalse((paths.TASKS / "a_f1_taken").exists() or (paths.TASKS / "a_f1_ok-slug").exists())


# --------------------------------------------------------------------------------------------------------- prompt
class Prompt(Workspace):
    def test_builtin_templates_when_none_exist(self):
        notes = self.root / "notes.md"
        notes.write_text("P7 needs a second anchor; keep {TASK} literal")
        scratch = self.root / "scratch"
        scratch.mkdir()
        for kind in ("author", "tune", "audit"):
            rc, out, err = self.cli("prompt", kind, self.task, "--notes", notes, "--out", scratch)
            self.assertEqual(rc, 0, out + err)
            self.assertIn(f"{b6ctl.PROMPTS / (kind + '.md')} not found: using the built-in minimal {kind} prompt", err)
            self.assertIsNone(PLACEHOLDER.search(out.replace("keep {TASK} literal", "")), out)
            for want in (str(self.task), NAME, VER, str(paths.ROOT), str(scratch), "keep {TASK} literal"):
                self.assertIn(want, out, kind)
        self.assertIn(f"VERDICT {NAME} {VER}: SHIP-WITH-DISCLOSURE", out)
        self.assertIn(str(paths.STATE / "audits" / f"{NAME}-{VER}.md"), out)
        self.assertTrue((paths.STATE / "audits").is_dir())
        rc, out, _ = self.cli("prompt", "author", self.task)
        self.assertIn("(no plan: authoring/PLAN.md is missing)", out)
        self.assertIn("(no scratch directory given", out)
        rc, out, _ = self.cli("prompt", "author", self.task, "--notes", self.root / "missing.md")
        self.assertEqual(rc, 2, out)

    def test_templates_are_filled_in_one_pass(self):
        b6ctl.PROMPTS.mkdir()
        (b6ctl.PROMPTS / "tune.md").write_text(
            "T={TASK} V={VERSION} D={TASK_DIR} R={REPO} S={SCRATCH}\nN={NOTES}\nP={PLAN}\nA={AUDIT_REPORT}\n"
            "C={CAMPAIGNS}\nX={UNKNOWN} json {\"a\": 1}\n")
        (self.task / "authoring/PLAN.md").write_text("lead T2, aim astra")
        notes = self.root / "n.md"
        notes.write_text("dial {VERSION} once")
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 1), "astra": done(3, 1)},
                   void_history=[{"astra": {**voided(3), "out": str(self.cdir("pilot", "astra", 1))}}])
        write_report(self.cdir("pilot", "astra", 1), voided(3), self.ident)
        os.environ["CLAUDE_SCRATCH"] = str(self.root)
        rc, out, err = self.cli("prompt", "tune", self.task, "--notes", notes)
        self.assertEqual(rc, 0, out)
        self.assertEqual(err, "")
        self.assertIn(f"T={NAME} V={VER} D={self.task} R={paths.ROOT} S={self.root}\n", out)
        self.assertIn("N=dial {VERSION} once", out)
        self.assertIn("P=lead T2, aim astra", out)
        self.assertIn("X={UNKNOWN} json {\"a\": 1}", out)
        self.assertIn(f"A={paths.STATE / 'audits' / (NAME + '-' + VER + '.md')}", out)
        self.assertIn(f"pilot campaign: {self.cdir('pilot', 'fable')}", out)
        self.assertIn(f"pilot campaign: {self.cdir('pilot', 'astra', 1)} (void: infrastructure loss, excluded)", out)
        self.assertRegex(out, r"pilot ledger: .* -> PILOT HARD")

    def test_blind(self):
        rc, out, _ = self.cli("prompt", "blind", self.task)
        self.assertEqual(rc, 2, out)
        readers = self.root / "readers"
        readers.mkdir()
        rc, out, err = self.cli("prompt", "blind", self.task, "--out", readers)
        self.assertEqual(rc, 0, out)
        self.assertIn("built-in minimal blind prompt", err)
        ws = Path(re.search(r"WORKSPACE (\S+)", out).group(1))
        self.assertEqual(ws.parent, readers)
        self.assertIn(f"WS = {ws}\n", out)
        self.assertNotIn("solve.py", out)
        self.assertEqual(b6ctl._read_rec("blind-prep", self.task)["workspace"], str(ws))
        b6ctl.PROMPTS.mkdir()
        (b6ctl.PROMPTS / "blind.md").write_text("Reader: work in {WORKSPACE}, read {INSTRUCTION} ({STEP}).")
        rc, out, err = self.cli("prompt", "blind", self.task, "--out", readers)
        ws2 = Path(re.search(r"WORKSPACE (\S+)", out).group(1))
        self.assertEqual((rc, err), (0, ""))
        self.assertIn(f"Reader: work in {ws2}, read instruction.md (01-task).", out)
        self.assertIn(f"blind-grade {self.task} {ws2}", out)

    @unittest.skipUnless((paths.PRODUCTION / "prompts").is_dir(), "production/prompts/ not written yet")
    def test_shipped_templates_fill_completely(self):
        notes = self.root / "notes.md"
        notes.write_text("controller notes")
        with mock.patch.object(b6ctl, "PROMPTS", paths.PRODUCTION / "prompts"):
            for kind in ("author", "tune", "audit"):
                if not (paths.PRODUCTION / "prompts" / f"{kind}.md").is_file():
                    continue
                rc, out, err = self.cli("prompt", kind, self.task, "--notes", notes, "--out", self.root)
                self.assertEqual((rc, err), (0, ""), kind)
                self.assertIsNone(PLACEHOLDER.search(out), (kind, out))
                self.assertIn("controller notes", out)
            if (paths.PRODUCTION / "prompts/blind.md").is_file():
                rc, out, err = self.cli("prompt", "blind", self.task, "--out", self.root)
                self.assertEqual((rc, err), (0, ""))
                self.assertNotRegex(out, r"\{(WORKSPACE|INSTRUCTION|STEP)\}")
                ws = re.search(r"WORKSPACE (\S+)", out).group(1)
                self.assertIn(f"WS = {ws}", out)


# ------------------------------------------------------------------------------------------------------------ run
class Run(Workspace):
    def pilot_ok(self, fable: list[dict], astra: list[dict]) -> None:
        self.outcomes = {("pilot", "oracle"): [ORACLE], ("pilot", "nop"): [NOP], ("pilot", "fable"): fable,
                         ("pilot", "astra"): astra}

    def test_pilot_hard(self):
        self.pilot_ok([RUNNING, done(3, 1)], [done(3, 1)])
        rc, out, _ = self.cli("run", self.task, "pilot")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.measured("launch")), 1)
        self.assertFalse(self.measured("rerun"))
        self.assertIn("ANTHROPIC_API_KEY 200", out)
        self.assertRegex(out, rf"VERDICT {NAME} {VER} pilot: PILOT HARD \(fable 1/3 pass@1 0\.33, astra 1/3 pass@1 "
                              r"0\.33\); signal gate \S+; census clean \(2 rows\)")
        self.assertIn(f"NEXT    {b6ctl.MEP} run {self.task} final", out)
        self.assertTrue((paths.GATES / f"{NAME}-{VER}-pilot.json").is_file())
        self.assertEqual(b6ctl._read_rec("census", self.task, "-pilot.json")["defects"], [])
        self.assertEqual(self.stage_of()[0], "author-check")  # nothing recorded an author-check here

    def test_void_is_rerun_once_and_the_void_dir_leaves_the_gate(self):
        self.pilot_ok([done(3, 1)], [voided(3), done(3, 0)])
        rc, out, _ = self.cli("run", self.task, "pilot")
        self.assertEqual(rc, 0, out)
        reruns = self.measured("rerun")
        self.assertEqual([c[-1] for c in reruns], ["astra"], "only the void model is re-run, once")
        self.assertIn("== re-run void astra (once)", out)
        self.assertIn(f"skipping {self.cdir('pilot', 'astra').name}: the ledger records it as void", out)
        g = json.loads((paths.GATES / f"{NAME}-{VER}-pilot.json").read_text())
        self.assertEqual(g["models"]["astra"]["valid"], 3, "the void campaign's trials must not count")
        self.assertIn("PILOT HARD", out)

    def test_void_twice_is_left_to_a_human(self):
        self.pilot_ok([done(3, 1)], [voided(3), voided(3)])
        rc, out, _ = self.cli("run", self.task, "pilot")
        self.assertEqual(rc, 3, out)
        self.assertEqual(len(self.measured("rerun")), 1)
        self.assertIn("VOID unresolved after one re-run", out)
        self.assertFalse((paths.GATES / f"{NAME}-{VER}-pilot.json").exists())

    def test_a_void_already_rerun_and_a_failed_run_are_not_rerun(self):
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": {"state": "failed", "error": "no report.json"},
                             "astra": voided(3)}, void_history=[{"astra": voided(3)}])
        rc, out, _ = self.cli("run", self.task, "pilot")
        self.assertEqual(rc, 3, out)
        self.assertFalse([c for c in self.calls if c[0] == "measure" and c[1] == "launch"], "nothing is launched")
        self.assertIn("astra is void again after its one re-run", out)
        self.assertIn("fable is failed: rerun-void re-runs void-auth runs only", out)
        self.assertIn("is already in the ledger: resuming", out)

    def test_timeout_resumes(self):
        self.pilot_ok([RUNNING] * 3, [RUNNING] * 3)
        rc, out, _ = self.cli("run", self.task, "pilot", "arena-calib-3", "--max", "0")
        self.assertEqual(rc, 124, out)
        self.assertIn("--ws arena-calib-3", " ".join(self.measured("launch")[0]))
        self.assertIn(f"NEXT    {b6ctl.MEP} run {self.task} pilot   (resumes the wait)", out)
        self.outcomes = {k: [done(3, 0)] if k[1] in ("fable", "astra") else [ORACLE if k[1] == "oracle" else NOP]
                         for k in self.outcomes}
        rc, out, _ = self.cli("run", self.task, "pilot")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.measured("launch")), 1, "the second run resumes; it never launches again")

    def test_easy_near_and_controls(self):
        for fable, astra, verdict, rc_want, text in ((done(3, 3), done(3, 3), "easy", 1, "tune or retire"),
                                                     (done(3, 2), done(3, 1), "near", 1, "harden"),
                                                     (done(3, 1), done(3, 1), "controls fail", 1, "controls fail")):
            with self.subTest(verdict=verdict):
                self.save({"entries": []})
                nop = {**NOP, "mean_reward": 0.9} if verdict == "controls fail" else NOP
                self.outcomes = {("pilot", "oracle"): [ORACLE], ("pilot", "nop"): [nop], ("pilot", "fable"): [fable],
                                 ("pilot", "astra"): [astra]}
                for m in ("fable", "astra", "oracle", "nop"):
                    shutil.rmtree(self.cdir("pilot", m), ignore_errors=True)
                rc, out, _ = self.cli("run", self.task, "pilot")
                self.assertEqual(rc, rc_want, out)
                self.assertIn(f"pilot: {verdict} (", out)
                self.assertIn(text, out)
                self.assertIn("prompt tune" if verdict != "controls fail" else "prompt author", out)

    def test_census_defect_or_error_blocks_a_hard_task(self):
        for rows, word in (("    -final-fable ccccccc 01-task reward=1.0 diff_fields=['f.json.n: ref=1 got=2']\n",
                            "census DEFECT: 1 full-reward step(s)"), ("", "census ERROR")):
            with self.subTest(word=word):
                self.save({"entries": []})
                self.census_rows(rows)
                self.pilot_ok([done(3, 1)], [done(3, 1)])
                rc, out, _ = self.cli("run", self.task, "pilot")
                self.assertEqual(rc, 1, out)
                self.assertIn("PILOT HARD", out)
                self.assertIn(word, out)
                self.assertIn("prompt author", out)

    def test_final_needs_a_pilot_and_preflight_refusal(self):
        rc, out, _ = self.cli("run", self.task, "final")
        self.assertEqual(rc, 2, out)
        self.assertIn(f"NEXT    {b6ctl.MEP} run {self.task} pilot", out)
        self.http_code = "401"
        rc, out, _ = self.cli("run", self.task, "pilot")
        self.assertEqual(rc, 3, out)
        self.assertIn("REFUSED: a provider key did not answer 200", out)
        self.assertIn("NOT LAUNCHED", out)
        self.assertFalse(self.calls, "nothing reached measure.py")

    def clean_pilot_census(self):
        b6ctl._write_rec("census", self.task, {"stage": "pilot", "rc": 0, "rows": 2, "defects": [], "dirs": [],
                                               "log": "x"}, "-pilot.json")

    def test_final_only_after_a_pilot_that_meets_the_criteria(self):
        """user 2026-10-16: the 10 x 2 final is launched only when the 3 x 2 pilot meets the bar."""
        for fable, astra, want in ((done(3, 2), done(3, 1), "pilot is near"),
                                   (done(3, 3), done(3, 0), "pilot is easy"),
                                   (done(3, 1), done(3, 1), "census has not run")):
            with self.subTest(want=want):
                self.save({"entries": []})
                self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": fable, "astra": astra})
                rc, out, _ = self.cli("run", self.task, "final")
                self.assertEqual(rc, 2, out)
                self.assertIn(want, out)
                rc, out, _ = self.cli("launch", self.task, "final", "--no-preflight")
                self.assertEqual(rc, 3, out)
                self.assertIn("REFUSED: final", out)
                self.assertFalse(self.measured("launch"), "no final reached measure.py")
        self.save({"entries": []})
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 1), "astra": done(3, 0)})
        b6ctl._write_rec("census", self.task, {"stage": "pilot", "rc": 0, "rows": 2, "defects": ["x"], "dirs": [],
                                               "log": "x"}, "-pilot.json")
        rc, out, _ = self.cli("run", self.task, "final")
        self.assertEqual(rc, 2, out)
        self.assertIn("census DEFECT", out)
        self.assertFalse(self.measured("launch"))

    def test_final_hard_points_at_the_blind_reader(self):
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 1), "astra": done(3, 1)})
        self.clean_pilot_census()
        self.outcomes = {("final", "fable"): [done(10, 3)], ("final", "astra"): [done(10, 2)]}
        rc, out, _ = self.cli("run", self.task, "final")
        self.assertEqual(rc, 0, out)
        self.assertIn("FINAL HARD (fable 3/10 pass@1 0.30, astra 2/10 pass@1 0.20)", out)
        self.assertIn(f'NEXT    {b6ctl.ME} prompt blind {self.task} --out "$CLAUDE_SCRATCH"', out)


# ----------------------------------------------------------------------------------------------------------- next
class Next(Workspace):
    def record_ready(self):
        b6ctl._write_rec("author-check", self.task, {"verdict": "READY", "identity": self.ident, "items": []})

    def checks(self, stage: str, rows: str = CLEAN_ROWS) -> None:
        paths.GATES.mkdir(parents=True, exist_ok=True)
        (paths.GATES / f"{NAME}-{VER}-{stage}.json").write_text(json.dumps({"verdict": "IN_BAND", "models": {}}))
        self.census_rows(rows)
        with contextlib.redirect_stdout(io.StringIO()):
            b6ctl.census(self.task, stage, [self.cdir(stage, "fable")])

    def test_every_stage_in_order(self):
        T, ME, MEP = str(self.task), b6ctl.ME, b6ctl.MEP
        stage, out = self.stage_of()
        self.assertEqual(stage, "author-check")
        self.assertIn(f"NEXT    {ME} author-check {T}", out)
        b6ctl._write_rec("author-check", self.task, {"verdict": "NOT READY", "identity": self.ident,
                                                     "items": [{"where": "lint", "what": "x", "fix": "y"}]})
        stage, out = self.stage_of()
        self.assertEqual(stage, "author-check")
        self.assertIn(f"prompt author {T} --notes", out)
        self.record_ready()
        stage, out = self.stage_of()
        self.assertEqual(stage, "pilot")
        self.assertIn(f"NEXT    {MEP} run {T} pilot", out)
        self.assertIn("STOP    unless PILOT HARD (3 x 2: pass@1 <= 0.5 on both, clean controls) with a clean census", out)
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": RUNNING, "astra": done(3, 1)})
        stage, out = self.stage_of()
        self.assertEqual(stage, "pilot")
        self.assertIn("resumes the wait", out)
        self.save({"entries": []})
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 1), "astra": voided(3)})
        stage, out = self.stage_of()
        self.assertIn("-> VOID", out)
        self.assertIn("infrastructure loss", out)
        self.save({"entries": []})
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 1), "astra": done(3, 1)})
        stage, out = self.stage_of()
        self.assertEqual(stage, "pilot")
        self.assertIn("gate + census on the finished campaign", out)
        self.checks("pilot")
        stage, out = self.stage_of()
        self.assertEqual(stage, "final")
        self.assertIn(f"NEXT    {MEP} run {T} final", out)
        self.entry("final", {"fable": done(10, 3), "astra": done(10, 1)})
        self.checks("final")
        stage, out = self.stage_of()
        self.assertEqual(stage, "blind")
        self.assertIn(f"prompt blind {T}", out)
        b6ctl._write_rec("blind-prep", self.task, {"workspace": "/scratch/blind-x", "steps": ["01-task"]})
        stage, out = self.stage_of()
        self.assertIn(f"NEXT    {ME} blind-grade {T} /scratch/blind-x", out)
        b6ctl._write_rec("blind", self.task, {"identity": self.ident, "workspace": "/scratch/blind-x",
                                              "steps": {"01-task": {"reward": 0.79, "failed": ["obj_designs"]}}})
        stage, out = self.stage_of()
        self.assertEqual(stage, "audit")
        self.assertIn("01-task reward 0.7900 failed obj_designs  (misses: the audit must show each is the reader's)", out)
        rep = paths.STATE / "audits" / f"{NAME}-{VER}.md"
        rep.parent.mkdir(parents=True)
        rep.write_text(f"# audit {NAME} {VER}\n\nVERDICT: WITHHOLD -- P2 double charge\n")
        stage, out = self.stage_of()
        self.assertEqual(stage, "audit")
        self.assertIn("WITHHOLD: back to the author", out)
        rep.write_text(f"# audit\n\nVERDICT: WITHHOLD\n\nre-audit\n\nVERDICT {NAME} {VER}: SHIP-WITH-DISCLOSURE\n")
        stage, out = self.stage_of()
        self.assertEqual(stage, "ship")
        self.assertIn(f"NEXT    {MEP} ship {T} --audit {rep}", out)
        frozen = paths.TASKS / "_versions" / f"{NAME}-{VER}"
        shutil.copytree(self.task, frozen)
        (frozen / "verification").mkdir()
        (frozen / "verification/harbor-tasks-check.json").write_text(json.dumps({"status": "pass",
                                                                                 "artifact_sha256": self.ident}))
        stage, out = self.stage_of()
        self.assertEqual(stage, "ship")
        self.assertIn("harbor         receipt pass", out)
        z = paths.STATE / "deliveries" / f"{NAME}__01-task.zip"
        z.parent.mkdir(parents=True)
        z.write_bytes(b"PK")
        b6ctl._write_rec("ship", self.task, {"zips": [str(z)], "ok": True})
        stage, out = self.stage_of()
        self.assertEqual(stage, "done")
        self.assertIn("STOP    uploading to Drive or the tracking sheet needs the user's go-ahead", out)
        self.assertIn(f"--grep {NAME}", out)

    def test_changed_tree_near_defect_and_failed_receipt(self):
        self.record_ready()
        (self.task / "environment/files/extra.md").write_text("an edit after author-check\n")
        stage, out = self.stage_of()
        self.assertEqual(stage, "author-check")
        self.assertIn("but the tree has changed since", out)
        shutil.rmtree(self.task)
        shutil.copytree(REF, self.task, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 2), "astra": done(3, 1)})
        self.checks("pilot")
        stage, out = self.stage_of()
        self.assertEqual(stage, "pilot")
        self.assertIn("near: harden", out)
        self.assertIn(f"prompt tune {self.task}", out)
        self.save({"entries": []})
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 1), "astra": done(3, 1)})
        self.checks("pilot", "    -pilot-fable d 01-task reward=1.0 diff_fields=['f.json.n: ref=1 got=2']\n")
        stage, out = self.stage_of()
        self.assertEqual(stage, "pilot")
        self.assertIn("a grader defect", out)
        self.assertIn("census DEFECT", out)

    def test_author_check_records_its_verdict(self):
        ok = {"rc": 0, "lint_rc": 0, "lint": {"fails": [], "warns": [], "oks": []}, "selftest_bad": [], "pycache": [],
              "stale_left": 0}
        tp = self.task / "authoring/traps.json"
        tp.write_text(json.dumps({**json.loads(tp.read_text()), "schema": "b6/premises/1"}))
        self.ident = b6ctl._identity(self.task)
        with mock.patch.object(b6ctl, "_check", lambda t, a=(): ok), \
                mock.patch.object(b6ctl, "_validate", lambda t, s: {"rc": 0, "fails": [], "stale": 0, "log": None,
                                                                    "why": ""}):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = b6ctl.author_check(self.task, 10)
            self.assertEqual(rc, 1, out.getvalue())  # traps.json is not b8/premises/1 now
            rec = b6ctl._read_rec("author-check", self.task)
            self.assertEqual((rec["verdict"], rec["identity"]), ("NOT READY", self.ident))
            self.assertIn("[traps] authoring/traps.json schema", b6ctl._rec_path("author-check", self.task,
                                                                                ".notes.md").read_text())
            self.assertIn("prompt author", out.getvalue())
            tp.write_text(json.dumps({**json.loads(tp.read_text()), "schema": "b8/premises/1"}))
            ident = b6ctl._identity(self.task)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = b6ctl.author_check(self.task, 10)
            self.assertEqual(rc, 0, out.getvalue())
            self.assertEqual(b6ctl._read_rec("author-check", self.task)["identity"], ident)
            self.assertFalse(b6ctl._rec_path("author-check", self.task, ".notes.md").exists())


# ----------------------------------------------------------------------------------------------------------- ship
class Ship(Workspace):
    def ready(self, verdict: str | None = None) -> Path:
        self.save({"entries": []})
        os.environ["CLAUDE_SCRATCH"] = str(self.root)  # the staging dir goes here, not to the system temp
        b6ctl._write_rec("author-check", self.task, {"verdict": "READY", "identity": self.ident, "items": []})
        paths.GATES.mkdir(parents=True, exist_ok=True)
        (paths.GATES / f"{NAME}-{VER}-final.json").write_text(json.dumps(
            {"verdict": "IN_BAND", "models": {"fable": {"pass_at_1": 0.3}, "astra": {"pass_at_1": 0.1}}}))
        self.entry("pilot", {"oracle": ORACLE, "nop": NOP, "fable": done(3, 1), "astra": done(3, 1)})
        self.void0 = self.cdir("final", "astra")
        write_report(self.void0, done(10, 0), self.ident)  # a void-auth report can look valid; the ledger decides
        self.rerun = self.cdir("final", "astra", 1)
        self.entry("final", {"fable": done(10, 3)}, void_history=[{"astra": {**voided(10), "out": str(self.void0)}}])
        write_report(self.rerun, done(10, 1), self.ident)
        led = self.ledger()
        led["entries"][-1]["runs"]["astra"] = {**done(10, 1), "out": str(self.rerun)}
        self.save(led)
        rep = paths.STATE / "audits" / f"{NAME}-{VER}.md"
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text(f"# §14 audit: {NAME} {VER}\n\nbody\n\n"
                       + (verdict or f"VERDICT {NAME} {VER}: SHIP-WITH-DISCLOSURE -- disclose FLAT"))
        self.tc_pulls = ["no receipt yet", "install:pass"]
        return rep

    def test_ship_freezes_checks_harbor_and_assembles(self):
        rep = self.ready()
        frozen = paths.TASKS / "_versions" / f"{NAME}-{VER}"
        rc, out, _ = self.cli("ship", self.task, "--audit", rep)
        self.assertEqual(rc, 0, out)
        self.assertEqual(b6ctl._identity(frozen), self.ident)
        launches = [c for c in self.calls if c[:2] == ("tc", "launch")]
        self.assertEqual(launches, [("tc", "launch", str(frozen), "arena-calib-9")])
        self.assertEqual(len([c for c in self.calls if c[:2] == ("tc", "pull")]), 2)
        self.assertEqual(self.asm["--fable"], str(self.cdir("final", "fable")))
        self.assertEqual(self.asm["--astra"], str(self.rerun), "the -rerun dir replaces the void final")
        self.assertEqual((self.asm["--oracle"], self.asm["--nop"]),
                         (str(self.cdir("pilot", "oracle")), str(self.cdir("pilot", "nop"))))
        self.assertEqual(self.asm["-o"], str(paths.STATE / "deliveries"))
        self.assertTrue(self.asm["staged_was_dir"] and self.asm["staged"].name == NAME)
        self.assertEqual(self.asm["staged_identity"], self.ident)
        self.assertFalse(self.asm["staged"].parent.exists(), "the staging dir is removed")
        z = paths.STATE / "deliveries" / f"{NAME}__01-task.zip"
        self.assertIn(f"  {z}: OK", out)
        self.assertIn(f"SHIP {NAME} {VER}: OK", out)
        self.assertFalse((self.task / "verification").exists(), "the live tree stays receipt-free")
        self.assertEqual(self.stage_of()[0], "done")
        n = len(self.calls)
        rc, out, _ = self.cli("ship", self.task, "--audit", rep)
        self.assertEqual(rc, 0, out)
        self.assertIn("already holds this content: resuming", out)
        self.assertIn("receipt already installed: pass", out)
        self.assertIn("zips already assembled", out)
        self.assertEqual(len(self.calls), n, "a finished ship launches and assembles nothing again")

    def test_timeout_then_resume_without_a_second_launch(self):
        rep = self.ready()
        self.tc_pulls = []
        rc, out, _ = self.cli("ship", self.task, "--audit", rep, "--max", "0", "--out", self.root / "zips")
        self.assertEqual(rc, 124, out)
        self.tc_pulls = ["install:pass"]
        rc, out, _ = self.cli("ship", self.task, "--audit", rep, "--out", self.root / "zips")
        self.assertEqual(rc, 0, out)
        self.assertEqual(len([c for c in self.calls if c[:2] == ("tc", "launch")]), 1)
        self.assertIn("already launched: polling", out)
        self.assertEqual(self.asm["-o"], str(self.root / "zips"))

    def test_failed_receipts(self):
        for pull, text in (("install:fail", "installed fail"), ("receipt is for other content; not installed",
                                                                "not installed")):
            with self.subTest(pull=pull):
                rep = self.ready()
                shutil.rmtree(paths.TASKS / "_versions", ignore_errors=True)
                paths.TC_RUNS.unlink(missing_ok=True)
                self.tc_pulls = [pull]
                rc, out, _ = self.cli("ship", self.task, "--audit", rep)
                self.assertEqual(rc, 1, out)
                self.assertIn(text, out)
                self.assertIn("a human decides", out)
                self.assertFalse([c for c in self.calls if c[0] == "asm"])

    def refused(self, rep: Path, *want: str, rc_want: int = 3) -> None:
        rc, out, _ = self.cli("ship", self.task, "--audit", rep)
        self.assertEqual(rc, rc_want, out)
        for w in want:
            self.assertIn(w, out)
        self.assertFalse((paths.TASKS / "_versions").exists(), "nothing may be frozen on a refusal")
        self.assertFalse([c for c in self.calls if c[0] in ("tc", "asm")], "nothing may be launched on a refusal")

    def test_refuses_without_a_shippable_audit(self):
        self.ready()
        audits = paths.STATE / "audits"
        cases = (("missing.md", None, "no audit report at"),
                 ("w.md", f"VERDICT {NAME} {VER}: WITHHOLD", "audit verdict is WITHHOLD"),
                 ("o.md", f"VERDICT {NAME} 2.5.0: SHIP", f"names 2.5.0, not {NAME} {VER}"),
                 ("x.md", "VERDICT a_f1_other-task 2.6.0: SHIP", f"names a_f1_other-task, not {NAME} {VER}"),
                 ("n.md", "no verdict here", "has no VERDICT line"),
                 ("u.md", "VERDICT: SHIP", "cannot tell that u.md audits"))
        for fname, body, want in cases:
            with self.subTest(fname=fname):
                if body is not None:
                    (audits / fname).write_text(f"# some audit\n\n{body}\n")
                self.refused(audits / fname, want)
        (audits / "loose.md").write_text(f"# §14 audit: {NAME} {VER}\n\nVERDICT: SHIP. P2 GENUINE\n")
        self.assertEqual(b6ctl.audit_verdict(audits / "loose.md", self.task)[0], "SHIP")
        (audits / "late.md").write_text(f"# {NAME} {VER}\nVERDICT: SHIP\n...\n**VERDICT** {NAME} {VER}: WITHHOLD\n")
        self.assertEqual(b6ctl.audit_verdict(audits / "late.md", self.task)[0], "WITHHOLD")

    def test_refuses_easy_gate_stale_author_check_and_archived_trees(self):
        rep = self.ready()
        g = paths.GATES / f"{NAME}-{VER}-final.json"
        g.write_text(json.dumps({"models": {"fable": {"pass_at_1": 0.6}, "astra": {"pass_at_1": 0.1}}}))
        self.refused(rep, "final gate: pass@1 fable 0.6")
        g.unlink()
        self.refused(rep, "no final gate report")
        self.ready()
        (self.task / "environment/files/late-edit.md").write_text("changed after the measurement\n")
        self.refused(rep, "author-check is READY on other content", "measured other content than this tree")
        arch = paths.TASKS / "_versions" / f"{NAME}-{VER}"
        shutil.copytree(REF, arch)
        try:
            rc, out, _ = self.cli("ship", arch, "--audit", rep)
        finally:
            shutil.rmtree(paths.TASKS / "_versions")
        self.assertEqual(rc, 2, out)
        self.assertIn("is archived; ship takes the live tree", out)

    def test_refuses_ambiguous_campaigns_and_foreign_frozen_copy(self):
        rep = self.ready()
        write_report(self.cdir("final", "astra", 2), done(10, 2), self.ident)
        self.refused(rep, "astra: ambiguous final campaign with 10 valid runs")
        shutil.rmtree(self.cdir("final", "astra", 2))
        write_report(self.cdir("final", "astra", 2), done(8, 2, void=2), self.ident)
        self.refused(rep, "astra: ambiguous final campaign with 10 valid runs", "(8 valid)", "(void)")
        shutil.rmtree(self.cdir("final", "astra", 2))
        shutil.rmtree(self.cdir("pilot", "nop"))
        self.refused(rep, "no finished pilot nop control")
        self.ready()
        frozen = paths.TASKS / "_versions" / f"{NAME}-{VER}"
        shutil.copytree(self.task, frozen)
        (frozen / "environment/files/foreign.md").write_text("other content\n")
        rc, out, _ = self.cli("ship", self.task, "--audit", rep)
        self.assertEqual(rc, 3, out)
        self.assertIn("exists with other content", out)
        self.assertFalse([c for c in self.calls if c[0] in ("tc", "asm")])


# ------------------------------------------------------------------------------------------------------- setup.sh
class SetupScript(unittest.TestCase):
    """production/setup.sh on a fake checkout: stub uv, ./arena, traplib.py and b6ctl.py log their calls."""

    def fake_checkout(self) -> tuple[Path, Path, dict]:
        root = Path(tempfile.mkdtemp(prefix="setup-", dir=TMP.name)).resolve()
        log = root / "calls.log"
        (root / "production/tools").mkdir(parents=True)
        (root / "production/traps").mkdir()
        shutil.copy(paths.PRODUCTION / "setup.sh", root / "production/setup.sh")
        logger = f"import sys\nopen({str(log)!r}, 'a').write('NAME ' + ' '.join(sys.argv[1:]) + '\\n')\n"
        (root / "production/traps/traplib.py").write_text(logger.replace("NAME", "traplib"))
        (root / "production/tools/b6ctl.py").write_text(logger.replace("NAME", "b6ctl")
                                                        + "print('FAIL dump -- fix: ./arena dump --set <path>')\n"
                                                          "raise SystemExit(1)\n")
        bindir = root / "bin"
        bindir.mkdir()
        for name, path in (("uv", bindir / "uv"), ("arena", root / "arena")):
            path.write_text(f"#!/bin/sh\necho {name} \"$@\" >> '{log}'\n")
            path.chmod(0o755)
        (bindir / "python3").symlink_to(sys.executable)
        env = {"PATH": f"{bindir}:/usr/bin:/bin", "HOME": str(root), "ANTHROPIC_AUTH_TOKEN": "wf-setup-token"}
        return root, log, env

    def setup_sh(self, root: Path, env: dict) -> subprocess.CompletedProcess:
        return REAL_RUN(["/bin/bash", str(root / "production/setup.sh")], env=env, capture_output=True, text=True,
                        stdin=subprocess.DEVNULL, timeout=120)

    def test_every_step_in_order_and_doctors_exit_code(self):
        root, log, env = self.fake_checkout()
        p = self.setup_sh(root, env)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        steps = ["uv sync", "uv python install 3.11", "traplib build", "b6ctl doctor"]
        self.assertEqual(log.read_text().splitlines(), steps)
        self.assertIn("keys.env is missing and there is no terminal to ask on", p.stdout)
        self.assertIn("FAIL dump -- fix: ./arena dump --set <path>", p.stdout)
        self.assertIn("b6ctl.py new <slug>", p.stdout)
        (root / "keys.env").write_text("ANTHROPIC_API_KEY=wf-setup-secret-value\n")
        log.unlink()
        p = self.setup_sh(root, env)
        self.assertEqual(log.read_text().splitlines(), steps, "a rerun repeats the same idempotent steps")
        self.assertIn("keys.env is present (contents never shown)", p.stdout)
        self.assertNotIn("wf-setup-", p.stdout + p.stderr)

    def test_stops_without_uv(self):
        root, log, env = self.fake_checkout()
        (root / "bin/uv").unlink()
        if shutil.which("uv", path="/usr/bin:/bin"):
            self.skipTest("uv is installed system-wide")
        p = self.setup_sh(root, env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("FAIL uv not found -- fix: install uv", p.stdout)
        self.assertFalse(log.exists(), "nothing runs before uv is there")


# --------------------------------------------------------------------------------------------------- census (real)
@unittest.skipUnless(Path(paths.PY311).is_file(), f"verifier python not found at {paths.PY311} (set ARENA_PY311)")
class CensusReal(Workspace):
    def test_reference_answer_is_clean_and_a_changed_full_reward_answer_is_a_defect(self):
        camp = self.cdir("final", "fable")
        step = camp / "jobs/run/package__x1/steps/01-task"
        deliv = step / "artifacts/app/deliverables"
        deliv.mkdir(parents=True)
        (step / "verifier").mkdir()
        (step / "verifier/reward.json").write_text(json.dumps({"reward": 1.0}))
        env = {**os.environ, "ARENA_SOURCE": str(self.task / "environment/files"), "ARENA_OUT": str(deliv),
               "ARENA_SUBMITTED": str(deliv), "ARENA_MISREAD": ""}
        REAL_RUN([paths.PY311, "-I", "-B", str(self.task / "steps/01-task/solution/solve.py")], env=env, check=True,
                 capture_output=True, cwd=deliv)
        with mock.patch.object(b6ctl, "CENSUS", TOOLS / "census_answers.py"), \
                contextlib.redirect_stdout(io.StringIO()):
            c = b6ctl.census(self.task, "final", [camp])
            self.assertEqual((c["rows"], c["defects"], c.get("error")), (1, [], None), c)
            f = next(deliv.glob("*.json"))
            data = json.loads(f.read_text())
            key = next(k for k, v in data.items() if isinstance(v, int) and not isinstance(v, bool))
            data[key] += 1
            f.write_text(json.dumps(data, ensure_ascii=False))
            c = b6ctl.census(self.task, "final", [camp])
        self.assertEqual(len(c["defects"]), 1, c)
        self.assertIn(key, c["defects"][0])
        self.assertEqual(b6ctl._census_text(c), "census DEFECT: 1 full-reward step(s) differ from the reference")


if __name__ == "__main__":
    unittest.main()
