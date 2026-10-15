"""Whole-pipeline runs on Coder: launch, status, pull and the pause guard, offline.

Ported 2026-10-05 from the coding-v2 checkout's suite, plus what this
checkout adds: keys parsed by one function, only-read remote settings, the
cited campaign evidence a named bundle needs, and retried provisioning.
Nothing here reaches a deployment: the launcher and status scripts are
executed locally against a temporary root, and every fixture lives in a
TemporaryDirectory.
"""
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.benchmark import coder, coder_run

PIPELINE = Path(coder_run.__file__).resolve().parents[1]


class Arguments(unittest.TestCase):
    def test_arena_args_and_checkout_scripts_become_remote_argv(self):
        argv = coder_run.command_argv(["build", "-n", "10"])
        self.assertEqual(argv[1:4], ["-m", "pipeline.cli", "build"])
        self.assertTrue(argv[0].endswith(".venv/bin/python"))
        script = coder_run.command_argv(["category_batch.py", "--out", "envs-x"])
        self.assertTrue(script[1].endswith("category_batch.py"))
        with self.assertRaises(ValueError):
            coder_run.command_argv(["../elsewhere.py"])
        with self.assertRaises(ValueError):
            coder_run.command_argv([])

    def test_remote_env_runs_calibration_locally_and_refuses_credentials(self):
        with patch.object(coder_run, "dump_path", return_value=Path("/data/dump")):
            env = coder_run.remote_env({"ARENA_REVIEW_CONCURRENCY": "4"})
            self.assertEqual(env["ARENA_NATIVE_BACKEND"], "local")
            self.assertEqual(env["ARENA_DUMP"], "/data/dump")
            self.assertEqual(env["ARENA_REVIEW_CONCURRENCY"], "4")
            for name in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "X_SECRET_KEY"):
                with self.assertRaises(ValueError):
                    coder_run.remote_env({name: "x"})
            with self.assertRaises(ValueError):
                coder_run.remote_env({"BAD-NAME": "x"})

    def test_every_default_remote_setting_has_a_reader_in_this_checkout(self):
        sources = "".join(p.read_text() for p in PIPELINE.rglob("*.py")
                          if "tests" not in p.parts and p.name != "coder_run.py")
        for name in coder_run.DEFAULT_REMOTE_ENV:
            if name.startswith("ARENA_"):
                self.assertIn(f"{name}", sources, f"{name} is set on the workspace but nothing reads it")

    def test_credentials_come_from_keys_env_never_the_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            keys = Path(tmp) / "keys.env"
            keys.write_text("# ANTHROPIC_AUTH_TOKEN=commented-out\nANTHROPIC_API_KEY=from-file\nOPENAI_API_KEY=\n")
            with patch.dict(os.environ, {"ANTHROPIC_AUTH_TOKEN": "inherited", "OPENAI_API_KEY": "inherited"}):
                values = coder_run.keys_values(keys)
        self.assertEqual(values, {"ANTHROPIC_API_KEY": "from-file"})
        with tempfile.TemporaryDirectory() as tmp:
            keys = Path(tmp) / "keys.env"
            keys.write_text("ANTHROPIC_API_KEY=k\nOPENAI_BASE_URL=http://198.18.240.3:18443/v1\nOPEN_AI_API_KEY1=o\n")
            self.assertEqual(coder_run.keys_values(keys), {"ANTHROPIC_API_KEY": "k", "OPEN_AI_API_KEY1": "o"})
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "keys.env"
            empty.write_text("OPENAI_API_KEY=x\n")
            with patch.dict(os.environ, {"ANTHROPIC_AUTH_TOKEN": "inherited"}), self.assertRaises(ValueError):
                coder_run.keys_values(empty)

    def test_load_keys_parses_keys_env_with_the_same_reader(self):
        from pipeline import cli, credentials
        body = 'ANTHROPIC_API_KEY="quoted"\n# comment\n\nMOONSHOT_API_KEY = spaced \nnot a line\n'
        with tempfile.TemporaryDirectory() as tmp:
            keys = Path(tmp) / "keys.env"
            keys.write_text(body)
            expected = credentials.read_key_file(keys)
            with patch.object(cli, "KEYS", keys), patch.dict(os.environ, {}, clear=True), \
                    patch.object(credentials, "_enabled_keys_file", credentials._enabled_keys_file):
                loaded = cli.load_keys(prompt_if_missing=False)
        self.assertEqual(expected, {"ANTHROPIC_API_KEY": "quoted", "MOONSHOT_API_KEY": "spaced"})
        self.assertEqual(loaded, expected)

    def test_persistence_bind_mounts_every_synced_path_once(self):
        script = coder_run.persist_script([Path("/Users/u/repo"), Path("/Users/u/dump")])
        self.assertEqual(script.count("mount --bind"), 2)
        self.assertIn("arena-mirror", script)
        self.assertIn("persistent=", script)
        # This checkout's dump lives under its root, which is already mirrored.
        nested = coder_run.persist_script([Path("/Users/u/repo"), Path("/Users/u/repo/datasets/dump")])
        self.assertEqual(nested.count("mount --bind"), 1)
        # ...but it still exists for rsync, after the parent's mount.
        self.assertIn("mkdir -p /Users/u/repo/datasets/dump", nested)
        self.assertGreater(nested.index("mkdir -p /Users/u/repo/datasets/dump"), nested.index("mount --bind"))
        with tempfile.TemporaryDirectory() as tmp:
            root, mirror = Path(tmp) / "root", Path(tmp) / "home"
            mirror.mkdir()
            # Run the real script with mount/sudo stubbed out: the nested target exists afterwards.
            stub = Path(tmp) / "bin"
            stub.mkdir()
            for name in ("sudo", "mountpoint"):
                (stub / name).write_text("#!/bin/sh\n[ \"$1\" = mount ] && exit 1\n"
                                         "[ \"$(basename \"$0\")\" = mountpoint ] && exit 1\nexec \"$@\"\n")
                (stub / name).chmod(0o755)
            script = coder_run.persist_script([root, root / "datasets/dump"])
            out = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                                 env={"PATH": f"{stub}:/usr/bin:/bin", "HOME": str(mirror)})
            self.assertTrue((root / "datasets/dump").is_dir(), out.stderr)
            self.assertIn("persistent=0", out.stdout)              # mount refused -> said so

    def test_constants_match_this_checkout(self):
        self.assertEqual(coder_run.AUTHORING_PYTHON, (coder_run.ROOT / ".python-version").read_text().strip())
        tops = {Path(p).parts[0] for p in coder_run.CODE_PATHS}
        # Everything artifacts.policy_identity hashes, so a remote run computes
        # the same identity its evidence is bound to.
        for name in ("pipeline", "rulesets", "CLAUDE.md", "requirements-native.lock",
                     "requirements-evidence.lock", "pyproject.toml", "uv.lock", "arena"):
            self.assertIn(name, tops)
        self.assertIn("category_batch.py", tops)
        for rel in coder_run.CODE_PATHS:
            self.assertTrue((coder_run.ROOT / rel).exists(), f"{rel} is synced but absent here")


class DataSync(unittest.TestCase):
    def test_peer_and_artifact_pushes_never_delete_or_overwrite_newer_remote_work(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ("envs-a/t", "envs-b", "reference", "pipeline-artifacts/classify-cache"):
                (root / d).mkdir(parents=True)
            with patch.object(coder_run, "ROOT", root), \
                    patch.object(coder_run, "dump_path", return_value=root / "dump"), \
                    patch.object(coder_run, "remote_trees", return_value=set()), \
                    patch.object(coder_run, "rsync", side_effect=lambda *a, **k: calls.append((a, k))):
                coder_run.sync_data("ws")
        targets = {a[1]: k for a, k in calls}
        for name in ("envs-a", "envs-b", "reference", "pipeline-artifacts"):
            kwargs = next(k for t, k in targets.items() if t.rstrip("/").endswith(name))
            self.assertFalse(kwargs.get("delete"), name)
            self.assertTrue(kwargs.get("update"), name)
        rules = next(k for t, k in targets.items() if t.rstrip("/").endswith("pipeline-artifacts"))["filters"]
        self.assertEqual(rules[-1], "- /*")
        self.assertIn("+ /releases/**", rules)
        self.assertNotIn("+ /native/", rules)

    def test_a_tree_a_live_run_is_writing_is_never_pushed(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ("envs-s1/t", "envs-s2/t", "reference"):
                (root / d).mkdir(parents=True)
            run = root / coder_run.RUNS / "r1"
            run.mkdir(parents=True)
            (run / "launch.json").write_text(json.dumps({"workspace": "ws", "argv": ["py", "-m", "pipeline.cli",
                                                                                      "build", "-o", "envs-s1"]}))
            with patch.object(coder_run, "ROOT", root), \
                    patch.object(coder_run, "dump_path", return_value=root / "dump"), \
                    patch.object(coder_run, "remote_trees", return_value=set()), \
                    patch.object(coder_run, "rsync", side_effect=lambda *a, **k: calls.append(a[1])):
                done = coder_run.sync_data("ws", dump=False, artifacts=False)
            self.assertEqual(done["skipped_live_trees"], ["envs-s1"])
            self.assertFalse(any("envs-s1" in c for c in calls))
            self.assertTrue(any("envs-s2" in c for c in calls))
            (run / "finished.json").write_text("{}")
            with patch.object(coder_run, "ROOT", root):
                self.assertEqual(coder_run.live_trees(), set())

    def test_a_tree_the_workspace_already_has_is_never_pushed_again(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for d in ("envs-s1/t", "envs-s9/t"):
                (root / d).mkdir(parents=True)
            with patch.object(coder_run, "ROOT", root), \
                    patch.object(coder_run, "remote_trees", return_value={"envs-s1"}), \
                    patch.object(coder_run, "rsync", side_effect=lambda *a, **k: calls.append(a[1])):
                coder_run.sync_data("ws", dump=False, artifacts=False)
        self.assertFalse(any("envs-s1" in c for c in calls))
        self.assertTrue(any("envs-s9" in c for c in calls))

    def test_the_rsync_command_carries_update_and_the_coder_transport(self):
        seen = {}
        def fake(args, **kwargs):
            seen["args"] = args
            return subprocess.CompletedProcess(args, 0, b"", b"")
        with patch.object(coder_run.coder_mod, "_binary", return_value="/usr/bin/coder"), \
                patch.object(coder_run.subprocess, "run", side_effect=fake):
            coder_run.rsync("ws", "/a/", "/a/", push=True, update=True)
        self.assertIn("--update", seen["args"])
        self.assertNotIn("--delete", seen["args"])
        self.assertEqual(seen["args"][-1], "ws:/a/")

    def test_code_sync_is_refused_while_a_run_is_alive_or_unreadable(self):
        with patch.object(coder_run, "runs", return_value=[{"run": "r", "alive": True}]), \
                patch.object(coder_run, "rsync", side_effect=AssertionError("synced under a live run")):
            with self.assertRaises(RuntimeError):
                coder_run.sync_code("ws")
        with patch.object(coder_run, "runs", side_effect=RuntimeError("coder ssh failed: run command: EOF")), \
                patch.object(coder_run, "rsync", side_effect=AssertionError("synced blind")):
            with self.assertRaises(RuntimeError):
                coder_run.sync_code("ws")


class NamedInputs(unittest.TestCase):
    """A named bundle carries the campaigns its records cite; checkout files go too."""

    def _tree(self, root: Path):
        bundle = root / "envs-v9/target-F2-scenario/a-001-x"
        (bundle / "authoring").mkdir(parents=True)
        (bundle / "authoring/spec.json").write_text("{}")
        native = root / "pipeline-artifacts/native"
        screen_a, screen_b, hardened = (native / "screen-1/calibration-a", native / "screen-1/calibration-b",
                                        native / "screen-2/calibration-c")
        for d in (screen_a, screen_b, hardened):
            d.mkdir(parents=True)
        (bundle / "verification").mkdir()
        (bundle / "verification/screen.json").write_text(json.dumps({
            "index": {"campaigns": [str(screen_a), str(native / "gone/calibration-z")], "topups": {}},
            "per_model": {"m": {"campaign": str(screen_b), "topups": []}},
            "bundle_path": str(bundle)}))
        (bundle / "hardened/v1/verification").mkdir(parents=True)
        (bundle / "hardened/v1/verification/screen.json").write_text(json.dumps(
            {"index": {"campaigns": [str(hardened), str(native / "screen-2")]}}))
        (root / "research/harden").mkdir(parents=True)
        (root / "research/harden/traps.json").write_text("{}")
        (root / "pipeline").mkdir()
        (root / "pipeline/policy.py").write_text("")
        (root / "keys.env").write_text("SECRET=1")
        return bundle, native

    def test_bundles_cite_their_campaigns_and_files_outside_code_are_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bundle, native = self._tree(root)
            with patch.object(coder_run, "ROOT", root), \
                    patch.object(coder_run, "dump_path", return_value=root / "datasets/dump"):
                files, bundles = coder_run.input_paths(
                    ["harden", str(bundle.relative_to(root)), "--apply", "--traps=research/harden/traps.json",
                     "pipeline/policy.py", "keys.env", "envs-v9", "/etc/passwd", "-o", "envs-v9"])
                evidence = coder_run.cited_evidence(bundle)
            self.assertEqual(bundles, [bundle])
            self.assertEqual(files, [root / "research/harden/traps.json"])
            # Existing directories only, none nested inside another cited one.
            self.assertEqual(evidence, [native / "screen-1/calibration-a", native / "screen-1/calibration-b",
                                        native / "screen-2"])

    def test_pushing_inputs_only_ever_adds(self):
        calls, made = [], []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bundle, native = self._tree(root)
            with patch.object(coder_run, "ROOT", root), \
                    patch.object(coder_run, "dump_path", return_value=root / "datasets/dump"), \
                    patch.object(coder_run.coder_mod, "ssh", side_effect=lambda ws, s, **k: made.append(s)), \
                    patch.object(coder_run, "rsync", side_effect=lambda *a, **k: calls.append((a, k))):
                done = coder_run.push_inputs("ws", ["harden", str(bundle), "--traps", "research/harden/traps.json"])
        self.assertEqual(len(done["evidence"]), 3)
        self.assertEqual(len(done["files"]), 1)
        self.assertTrue(made and made[0].startswith("mkdir -p "))
        for (ws, source, target), kwargs in calls:
            self.assertEqual(source, target)
            self.assertTrue(kwargs.get("update"))
            self.assertFalse(kwargs.get("delete"))

    def test_nothing_named_means_no_remote_call(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(coder_run, "ROOT", Path(tmp).resolve()), \
                patch.object(coder_run.coder_mod, "ssh", side_effect=AssertionError("remote call")):
            self.assertEqual(coder_run.push_inputs("ws", ["--help"]), {"files": [], "evidence": []})


class Retries(unittest.TestCase):
    def test_a_dropped_session_is_retried_and_a_real_failure_is_not(self):
        attempts = []

        def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("coder ssh failed (1): error: run command: EOF")
            return "ok"
        with patch.object(coder_run.time, "sleep"):
            self.assertEqual(coder_run.retrying("step", flaky), "ok")
        self.assertEqual(len(attempts), 3)
        refused = []

        def busy():
            refused.append(1)
            raise RuntimeError("a run is alive on ws; one code version per workspace")
        with patch.object(coder_run.time, "sleep"), self.assertRaises(RuntimeError):
            coder_run.retrying("step", busy)
        self.assertEqual(len(refused), 1)
        self.assertTrue(coder_run.transient("rsync: connection unexpectedly closed (0 bytes received)"))

    def test_a_launch_is_never_retried(self):
        sent = []

        def ssh(ws, command, stdin=None, timeout=None, check=True):
            sent.append(command)
            raise RuntimeError("coder ssh failed (1): error: run command: EOF")
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(coder_run, "ROOT", Path(tmp)), \
                patch.object(coder_run, "keys_values", return_value={"ANTHROPIC_API_KEY": "k"}), \
                patch.object(coder_run, "dump_path", return_value=Path("/data/dump")), \
                patch.object(coder_run.coder_mod, "ssh", ssh), patch.object(coder_run.time, "sleep"):
            with self.assertRaises(RuntimeError):
                coder_run.launch("ws", ["--help"], sync=False)
        self.assertEqual(len(sent), 1)


class Sharding(unittest.TestCase):
    def test_ranges_expand_and_split_round_robin_without_overlap(self):
        ranks = coder_run.expand_ranks("1-7,10")
        self.assertEqual(ranks, [1, 2, 3, 4, 5, 6, 7, 10])
        plan = coder_run.shard_plan(["a", "b", "c"], ranks)
        self.assertEqual(plan, {"a": [1, 4, 7], "b": [2, 5, 10], "c": [3, 6]})
        self.assertEqual(sorted(r for rs in plan.values() for r in rs), ranks)
        for bad in ("0-2", "1,1", "x", ""):
            with self.assertRaises(ValueError):
                coder_run.expand_ranks(bad)
        with self.assertRaises(ValueError):
            coder_run.shard_plan(["a", "a"], [1])

    def test_shard_owns_the_ranks_flag_and_names_each_shard(self):
        seen = {}

        def launch(ws, args, **k):
            seen[ws] = k["env"]["ARENA_SHARD"]
            return {"workspace": ws, "run": "r", "args": args}
        with patch.object(coder_run, "launch", side_effect=launch):
            rows = coder_run.shard(["a", "b"], [1, 2, 3], ["build", "-o", "envs-x"])
        self.assertEqual({r["workspace"]: r["args"][-1] for r in rows}, {"a": "1,3", "b": "2"})
        self.assertEqual(seen, {"a": "a", "b": "b"})
        self.assertIn('os.environ.get("ARENA_SHARD"', (PIPELINE / "orchestrate.py").read_text())
        with self.assertRaises(ValueError):
            coder_run.shard(["a"], [1], ["build", "--ranks", "1"])


class LauncherAndStatus(unittest.TestCase):
    def test_a_launched_run_is_detached_records_its_exit_and_keeps_keys_off_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, shm = Path(tmp) / "root", Path(tmp) / "shm"
            root.mkdir(); shm.mkdir()
            run_dir = root / coder_run.RUNS / "r1"
            request = {"root": str(root), "run_dir": str(run_dir), "keys_dir": str(shm),
                       "argv": [sys.executable, "-c",
                                "import os; print('hello', os.environ['ARENA_X'], "
                                "os.environ.get('ANTHROPIC_AUTH_TOKEN'))"],
                       "env": {"ARENA_X": "1"}, "keys": {"ANTHROPIC_API_KEY": "tok"}, "code_sha": "abc"}
            with patch.dict(os.environ, {"ANTHROPIC_AUTH_TOKEN": "inherited"}):
                out = subprocess.run([sys.executable, "-c", coder_run.LAUNCHER], input=json.dumps(request),
                                     capture_output=True, text=True, check=True)
            started = json.loads(out.stdout.strip().splitlines()[-1])
            self.assertTrue(started["pid"])
            deadline = time.time() + 20
            while not (run_dir / "exit_code").is_file() and time.time() < deadline:
                time.sleep(0.1)
            self.assertEqual((run_dir / "exit_code").read_text().strip(), "0")
            # The detached process never sees the launching shell's token.
            self.assertIn("hello 1 None", (run_dir / "run.log").read_text())
            link = root / "keys.env"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (shm / "arena-keys.env").resolve())
            self.assertEqual(oct((shm / "arena-keys.env").stat().st_mode & 0o777), "0o600")
            cmd = json.loads((run_dir / "cmd.json").read_text())
            self.assertNotIn("tok", json.dumps(cmd))
            status = subprocess.run([sys.executable, "-c", coder_run.STATUS, str(root / coder_run.RUNS)],
                                    capture_output=True, text=True, check=True)
            rows = json.loads(status.stdout)
            self.assertEqual(rows[0]["run"], "r1")
            self.assertEqual(rows[0]["exit_code"], "0")
            self.assertFalse(rows[0]["alive"])

    def test_the_runtime_probe_reports_a_missing_checkout_without_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run([sys.executable, "-c", coder_run.RUNTIME, str(Path(tmp) / "absent")],
                                 capture_output=True, text=True, check=True)
        state = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertIsNone(state["code_sha"])
        self.assertFalse(state["harbor_runtime"])
        self.assertFalse(state["root_mounted"])


class Staged(unittest.TestCase):
    def test_the_link_farm_links_everything_but_code_and_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, dest = Path(tmp) / "root", Path(tmp) / "root/.staged/abc"
            for name in ("pipeline", "rulesets", "envs-s1", "pipeline-artifacts", "datasets", ".venv"):
                (root / name).mkdir(parents=True)
            for name in ("CLAUDE.md", "workspace.toml", "keys.env", "arena"):
                (root / name).write_text("x")
            dest.mkdir(parents=True)
            subprocess.run([sys.executable, "-c", coder_run.LINK_FARM, str(root), str(dest),
                            "pipeline,rulesets,CLAUDE.md,arena"], check=True, capture_output=True)
            links = sorted(p.name for p in dest.iterdir())
            self.assertEqual(links, sorted(["envs-s1", "pipeline-artifacts", "datasets", ".venv", "workspace.toml"]))
            self.assertTrue(all((dest / name).is_symlink() for name in links))
            self.assertEqual((dest / "envs-s1").resolve(), (root / "envs-s1").resolve())
            # idempotent: a second pass adds nothing
            again = subprocess.run([sys.executable, "-c", coder_run.LINK_FARM, str(root), str(dest),
                                    "pipeline,rulesets,CLAUDE.md,arena"], check=True, capture_output=True, text=True)
            self.assertEqual(again.stdout.strip(), "0")

    def test_a_staged_launch_runs_from_the_snapshot_and_writes_to_root_artifacts(self):
        sent = {}

        def ssh(ws, command, stdin=None, timeout=None, check=True):
            if stdin:
                sent["request"] = json.loads(stdin.decode())
            out = json.dumps({"pid": 7, "run_dir": "x"}).encode()
            return subprocess.CompletedProcess([], 0, out, b"")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            snapshot = root / coder_run.STAGED / "abc"
            with patch.object(coder_run, "ROOT", root), \
                    patch.object(coder_run, "ensure_running"), patch.object(coder_run, "sync_data"), \
                    patch.object(coder_run, "prepare") as prepare, \
                    patch.object(coder_run, "stage_code", return_value=snapshot), \
                    patch.object(coder_run, "keys_values", return_value={}), \
                    patch.object(coder_run, "dump_path", return_value=Path("/data/dump")), \
                    patch.object(coder_run.coder_mod, "ssh", ssh):
                record = coder_run.launch("ws", ["harden", "/abs/bundle", "--apply"], staged=True)
            prepare.assert_not_called()                      # no code sync under live runs
            self.assertEqual(sent["request"]["root"], str(snapshot))
            self.assertEqual(sent["request"]["env"]["ARENA_PIPELINE_ARTIFACTS"], str(root / "pipeline-artifacts"))
            self.assertEqual(record["code_root"], str(snapshot))
            self.assertTrue((root / coder_run.RUNS / record["run"] / "launch.json").is_file())
        # config.ARTIFACTS is what the staged process's campaigns and receipts follow.
        self.assertIn("ARENA_PIPELINE_ARTIFACTS", (PIPELINE / "config.py").read_text())


class Pull(unittest.TestCase):
    def _blob(self, tmp, members):
        blob = Path(tmp) / "pull.tgz"
        with tarfile.open(blob, "w:gz") as tar:
            for name, data, mtime in members:
                info = tarfile.TarInfo(name)
                info.size, info.mtime = len(data), mtime
                tar.addfile(info, io.BytesIO(data))
        return blob

    def test_only_result_trees_are_written_and_newer_local_files_are_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            (root / "envs/t").mkdir(parents=True)
            newer = root / "envs/t/kept.json"
            newer.write_text("local")
            blob = self._blob(tmp, [
                ("envs/t/new.json", b"remote", time.time()),
                ("envs/t/kept.json", b"remote-old", time.time() - 3600),
                ("pipeline-artifacts/native/x/report.json", b"{}", time.time()),
                ("pipeline/policy.py", b"evil", time.time()),
                ("keys.env", b"evil", time.time()),
                ("../outside.txt", b"evil", time.time())])
            counts = coder_run.extract_pull(blob, root)
            self.assertEqual((root / "envs/t/new.json").read_text(), "remote")
            self.assertEqual(newer.read_text(), "local")
            self.assertTrue((root / "pipeline-artifacts/native/x/report.json").is_file())
            self.assertFalse((root / "pipeline/policy.py").exists())
            self.assertFalse((root / "keys.env").exists())
            self.assertFalse((Path(tmp) / "outside.txt").exists())
            self.assertEqual(counts, {"written": 2, "kept_newer_local": 1, "refused": 3})


class PauseGuard(unittest.TestCase):
    def test_no_launch_record_means_no_remote_call(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(coder_run, "ROOT", Path(tmp)), \
                patch.object(coder_run, "runs", side_effect=AssertionError("no remote call")):
            self.assertFalse(coder._remote_run_alive("arena-calib-9"))

    def test_an_open_launch_blocks_the_pause_even_when_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(coder_run, "ROOT", Path(tmp)):
            run = Path(tmp) / coder_run.RUNS / "r1"
            run.mkdir(parents=True)
            (run / "launch.json").write_text(json.dumps({"workspace": "ws"}))
            with patch.object(coder_run, "runs", side_effect=RuntimeError("ssh dropped")):
                self.assertTrue(coder._remote_run_alive("ws"))
            with patch.object(coder_run, "runs", return_value=[{"run": "r1", "alive": False}]):
                self.assertFalse(coder._remote_run_alive("ws"))
            self.assertTrue((run / "finished.json").is_file())
            self.assertEqual(coder_run.open_launches("ws"), [])

    def test_the_pool_never_pauses_a_workspace_a_remote_run_is_on(self):
        p = coder.Pool(coder.Settings(template="t", copy_parameters_from="ref", idle_stop_after=0))
        inst = coder.Instance("arena-calib-9", p.cfg)
        inst.state = "ready"
        p.instances.append(inst)
        with patch.object(coder, "_remote_run_alive", return_value=True), \
                patch.object(coder, "coder", side_effect=AssertionError("stopped under a run")):
            self.assertEqual(p.pause(), [])


class Cli(unittest.TestCase):
    def test_the_arena_cli_routes_remote_actions(self):
        from pipeline import cli
        with patch("pipeline.benchmark.coder_run.main", return_value=0) as main:
            self.assertEqual(cli.main(["coder", "runs", "ws"]), 0)
        main.assert_called_once_with(["runs", "ws"])
        with patch("pipeline.benchmark.coder_run.main", return_value=0) as main:
            cli.main(["coder", "run", "ws", "--", "build", "-n", "5"])
        main.assert_called_once_with(["run", "ws", "--", "build", "-n", "5"])
        with patch("pipeline.benchmark.coder_run.main", return_value=0) as main:
            cli.main(["coder", "prepare", "--help"])
        main.assert_called_once_with(["prepare", "--help"])
        with patch("pipeline.benchmark.coder.main", return_value=0) as pool_main:
            cli.main(["coder", "status"])
        pool_main.assert_called_once_with(["status"])


if __name__ == "__main__":
    unittest.main()
