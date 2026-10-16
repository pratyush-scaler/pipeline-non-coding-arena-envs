"""Regressions for the guards added after the 2026-09-17 batch.

Every test here names a defect that shipped GREEN through the sixteen gates and
was found by reading an artefact rather than by a check. A guard without a test
is how the same defect returns, and two of these were themselves wrong when
first written -- the heading detector matched `intersection` on a substring, and
the read-off share counted abstention checks it should have exempted.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.author.build import WEIGHT_TOTAL, normalise_weights
from pipeline.author.checks import normalise
from pipeline.calibrate.agent import Rollout
from pipeline.calibrate.run import classify_zero, _miss_shape
from pipeline.gates import integrity as I
from pipeline.gates.base import GateContext, Severity


def _ctx(root: Path) -> GateContext:
    return GateContext(task_dir=root, repo_root=root, extras={})


def _bundle(tmp: Path, checks: list[dict], solution: dict) -> Path:
    (tmp / "tests").mkdir(parents=True, exist_ok=True)
    (tmp / "solution" / "submission").mkdir(parents=True, exist_ok=True)
    (tmp / "tests" / "checks.json").write_text(json.dumps({"checks": checks}))
    (tmp / "solution" / "submission" / "out.json").write_text(json.dumps(solution))
    return tmp


def _obj(cid, weight=10, target=None, path=None):
    return {"id": cid, "kind": "objective", "weight": weight, "band": "core",
            "dimension": "d", "basis": "b", "assertion": "set_equals",
            "actual": {"op": "field", "file": "out.json", "path": path or cid},
            **({"target": target} if target else {})}


class Normalisation(unittest.TestCase):
    """kw-a007: four checks scored 0 across ten rollouts on submissions that
    were the reference answer verbatim, differing only by the markdown `#`."""

    def test_atx_heading_prefix_folds(self):
        self.assertEqual(normalise("# BLOCK 5"), normalise("BLOCK 5"))
        self.assertEqual(normalise("### Heading ###"), normalise("Heading"))

    def test_bullet_and_quote_markers_fold(self):
        self.assertEqual(normalise("- item"), normalise("item"))
        self.assertEqual(normalise("> quoted"), normalise("quoted"))

    def test_hash_without_space_is_not_a_heading(self):
        # `C# programming` and `#NoSpace` must survive: the fold requires
        # whitespace after the marker, or it eats real content.
        self.assertEqual(normalise("C# programming"), "c# programming")
        self.assertEqual(normalise("#NoSpace"), "#nospace")

    def test_numeric_strings_still_fold(self):          # the original kw-002 fix
        self.assertEqual(normalise("1960"), normalise(1960))


class WeightBudget(unittest.TestCase):
    """Totals ran 84-128 across one batch, so `weight: 20` meant 24% in one
    task and 16% in another while reading identically in both rubrics."""

    def test_rescales_to_exactly_one_hundred(self):
        for weights in ([12, 16, 18, 16, 20, 10, 14], [14, 24, 18, 28], [3, 97]):
            checks = [_obj(f"c{i}", w) for i, w in enumerate(weights)]
            normalise_weights(checks)
            self.assertEqual(sum(c["weight"] for c in checks), WEIGHT_TOTAL)

    def test_no_check_rounds_away_to_zero(self):
        checks = [_obj(f"c{i}", 1) for i in range(25)]
        normalise_weights(checks)
        self.assertTrue(all(c["weight"] >= 1 for c in checks))
        self.assertEqual(sum(c["weight"] for c in checks), WEIGHT_TOTAL)

    def test_guardrails_are_left_alone(self):
        g = {"id": "g", "kind": "guardrail", "weight": 0, "band": "floor",
             "dimension": "restraint", "basis": "b", "assertion": "absent",
             "actual": {"op": "field", "file": "out.json", "path": "x"}}
        checks = [_obj("a", 50), _obj("b", 50), g]
        normalise_weights(checks)
        self.assertEqual(g["weight"], 0)

    def test_ratios_are_preserved(self):
        checks = [_obj("a", 10), _obj("b", 20), _obj("c", 70)]
        normalise_weights(checks)
        self.assertEqual([c["weight"] for c in checks], [10, 20, 70])


class ReferenceAnswerGate(unittest.TestCase):
    """These shipped GREEN: a004's answer was [None]*15, a003's was 250 CSS
    property names with 193 duplicates, a005's was four hand-typed lists."""

    def _run(self, checks, solution):
        with tempfile.TemporaryDirectory() as d:
            root = _bundle(Path(d), checks, solution)
            findings, _ = I._reference_answer(_ctx(root))
            return {f.code for f in findings if f.severity is Severity.BLOCKER}

    def test_null_scalar_blocks(self):
        self.assertIn("reference-null",
                      self._run([_obj("a", 100)], {"a": None}))

    def test_all_null_list_blocks(self):
        self.assertIn("reference-null",
                      self._run([_obj("a", 100)], {"a": [None] * 15}))

    def _warnings(self, checks, solution):
        with tempfile.TemporaryDirectory() as d:
            root = _bundle(Path(d), checks, solution)
            findings, _ = I._reference_answer(_ctx(root))
            return {f.code for f in findings if f.severity is Severity.WARN}

    # v2 (user, 2026-10-02): answer-shape heuristics are advisories (a label
    # list can legitimately repeat); they are reported, never blocking.
    def test_mostly_duplicate_answer_is_advised(self):
        self.assertIn("reference-mostly-repeats",
                      self._warnings([_obj("a", 100)], {"a": ["x"] * 9 + ["y"]}))
        self.assertNotIn("reference-mostly-repeats",
                         self._run([_obj("a", 100)], {"a": ["x"] * 9 + ["y"]}))

    def test_one_value_dominating_is_advised(self):
        # a010: 'Setting' x15 of 29 -- 52% distinct, over the ratio floor, so
        # only the repetition test catches it.
        val = ["Setting"] * 15 + [f"u{i}" for i in range(14)]
        self.assertIn("reference-value-dominates",
                      self._warnings([_obj("a", 100)], {"a": val}))
        self.assertNotIn("reference-value-dominates",
                         self._run([_obj("a", 100)], {"a": val}))

    def test_legitimate_distinct_answer_passes(self):
        val = ["category 1", "category 2", "category 3", "estimated royalty",
               "list price", "subtitle", "title", "trim size"]
        # One objective is under the per-task floor, which this test is not
        # about; the floor has its own tests below.
        self.assertEqual(set(), self._run([_obj("a", 100)], {"a": val}) - {"objective-count"})

    def test_fewer_than_eight_objectives_blocks(self):
        from pipeline.policy import MIN_OBJECTIVES
        checks = [_obj(f"c{i}", 100 // (MIN_OBJECTIVES - 1) + (i == 0) * (100 % (MIN_OBJECTIVES - 1)))
                  for i in range(MIN_OBJECTIVES - 1)]
        solution = {f"c{i}": [f"answer {i}"] for i in range(MIN_OBJECTIVES - 1)}
        self.assertIn("objective-count", self._run(checks, solution))

    def test_eight_objectives_summing_to_the_total_pass_the_shape_checks(self):
        from pipeline.policy import MIN_OBJECTIVES
        self.assertEqual(MIN_OBJECTIVES, 8)
        weights = [16, 14, 14, 12, 12, 12, 10, 10]
        checks = [_obj(f"c{i}", w) for i, w in enumerate(weights)]
        solution = {f"c{i}": [f"answer {i}"] for i in range(8)}
        found = self._run(checks, solution)
        self.assertNotIn("objective-count", found)
        self.assertNotIn("weight-budget", found)

    def test_hand_typed_literal_list_blocks(self):
        checks = [_obj("a", 100, target={"op": "literal", "value": ["x", "y"],
                                         "why": "a plausible paragraph"})]
        self.assertIn("hand-typed-answer-set", self._run(checks, {"a": ["x", "y"]}))

    def test_scalar_sentinel_literal_is_allowed(self):
        checks = [_obj("a", 100, target={"op": "literal", "value": "NOT_RECORDED",
                                         "why": "recorded nowhere"})]
        self.assertNotIn("hand-typed-answer-set", self._run(checks, {"a": "NOT_RECORDED"}))

    def test_weight_budget_blocks(self):
        self.assertIn("weight-budget",
                      self._run([_obj("a", 37)], {"a": ["v"]}))


class VoidClassification(unittest.TestCase):
    """kw-a008: ten rollouts stopped on `max_tokens` with an empty deliverables
    directory and were recorded as ten model failures at mean 0.0."""

    def _r(self, **kw):
        r = Rollout(id="r")
        r.tool_calls = kw.pop("tool_calls", 5)
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def test_max_tokens_is_void(self):
        self.assertEqual("void", classify_zero(
            self._r(stop_reason="max_tokens", reward=0.0)))

    def test_step_cap_is_void(self):
        self.assertEqual("void", classify_zero(
            self._r(stop_reason="step_cap", reward=0.0)))

    def test_no_tool_calls_is_void(self):
        self.assertEqual("void", classify_zero(
            self._r(stop_reason="end_turn", reward=0.0, tool_calls=0)))

    def test_clean_zero_is_a_model_failure(self):
        self.assertEqual("model_failure", classify_zero(
            self._r(stop_reason="end_turn", reward=0.0)))

    def test_nonzero_reward_is_not_classified(self):
        self.assertIsNone(classify_zero(
            self._r(stop_reason="end_turn", reward=0.42)))


class MissShape(unittest.TestCase):
    """A binary score cannot tell a wrong answer from a right one the grader
    could not read. kw-a007 failed four checks on the reference answer."""

    def test_formatting_only_difference_is_flagged(self):
        self.assertEqual("equal_normalised",
                         _miss_shape(["# A", "## B"], ["A", "B"]))

    def test_near_miss_reports_jaccard(self):
        self.assertEqual("overlap_0.67", _miss_shape(["a", "b", "c"], ["a", "b"]))

    def test_unrelated_answer_reports_zero(self):
        self.assertEqual("overlap_0.00", _miss_shape(["a", "b"], ["x", "y"]))

    def test_scalar_equality_after_normalisation(self):
        self.assertEqual("equal_normalised", _miss_shape("# Heading", "Heading"))


class AgentSandbox(unittest.TestCase):
    """The bundle holds `authoring/extraction/after/` -- the accepted repair,
    i.e. the answer. A designer that reads it writes a task it has been told
    the answer to, and no gate downstream can tell."""

    def test_fixture_file_is_readable(self):
        from pipeline.author.agent_designer import _Sandbox
        with tempfile.TemporaryDirectory() as d:
            fx = Path(d) / "environment" / "files"
            fx.mkdir(parents=True)
            (fx / "doc.md").write_text("# hi")
            self.assertTrue(_Sandbox(fx).resolve("doc.md").is_file())

    def test_traversal_to_the_answer_is_denied(self):
        from pipeline.author.agent_designer import _Sandbox
        with tempfile.TemporaryDirectory() as d:
            fx = Path(d) / "environment" / "files"
            fx.mkdir(parents=True)
            after = Path(d) / "authoring" / "extraction" / "after"
            after.mkdir(parents=True)
            (after / "answer.md").write_text("the answer")
            with self.assertRaises(PermissionError):
                _Sandbox(fx).resolve("../../authoring/extraction/after/answer.md")

    def test_absolute_path_escape_is_denied(self):
        from pipeline.author.agent_designer import _Sandbox
        with tempfile.TemporaryDirectory() as d:
            fx = Path(d) / "environment" / "files"
            fx.mkdir(parents=True)
            with self.assertRaises((PermissionError, FileNotFoundError)):
                _Sandbox(fx).resolve("/etc/passwd")


class NestedHandTypedAnswers(unittest.TestCase):
    """The first version of this check read only the top-level `op`. The very
    next design wrapped the same hand-typed list inside a `difference` and
    passed -- kw-a005, five checks, 67% of the weight, reading no fixture file
    at all while the bundle sat GREEN."""

    def test_top_level_literal_list_is_found(self):
        from pipeline.gates.integrity import _typed_literals
        self.assertEqual(["target"],
                         _typed_literals({"op": "literal", "value": ["a", "b"]}))

    def test_literal_list_nested_in_difference_is_found(self):
        from pipeline.gates.integrity import _typed_literals
        expr = {"op": "difference",
                "a": {"op": "literal", "value": ["x.md", "y.md"], "why": "..."},
                "b": {"op": "pluck", "field": "h", "of": {"op": "rows", "file": "p.jsonl"}}}
        self.assertEqual(["target.a"], _typed_literals(expr))

    def test_literal_list_two_levels_down_is_found(self):
        from pipeline.gates.integrity import _typed_literals
        expr = {"op": "intersection",
                "a": {"op": "difference",
                      "a": {"op": "literal", "value": ["2", "3"]},
                      "b": {"op": "rows", "file": "p.jsonl"}},
                "b": {"op": "rows", "file": "q.jsonl"}}
        self.assertEqual(["target.a.a"], _typed_literals(expr))

    def test_scalar_sentinel_is_allowed_at_any_depth(self):
        from pipeline.gates.integrity import _typed_literals
        expr = {"op": "difference",
                "a": {"op": "literal", "value": "NOT_RECORDED", "why": "..."},
                "b": {"op": "rows", "file": "p.jsonl"}}
        self.assertEqual([], _typed_literals(expr))

    def test_pure_expression_is_clean(self):
        from pipeline.gates.integrity import _typed_literals
        expr = {"op": "intersection",
                "a": {"op": "pluck", "field": "h", "of": {"op": "rows", "file": "a.jsonl"}},
                "b": {"op": "pluck", "field": "h", "of": {"op": "rows", "file": "b.jsonl"}}}
        self.assertEqual([], _typed_literals(expr))


class ShippedGrader(unittest.TestCase):
    """The bundle must grade in the container, not only in our harness.

    `criteria.py` was constructed without `derived` or `projections` while 65 of
    84 objectives read a `.jsonl` projection. Every score in the 2026-09 batch
    came from our own Workspace; the delivered bundle raised on its first check.
    Adopted from the upstream fork, which found it.
    """

    def test_runner_passes_projections_and_derived(self):
        from pipeline.author.build import CRITERIA_RUNNER
        self.assertIn("projections.json", CRITERIA_RUNNER)
        self.assertIn("derived", CRITERIA_RUNNER)
        self.assertIn("projections=projections", CRITERIA_RUNNER)

    def test_runner_imports_from_the_shipped_package(self):
        from pipeline.author.build import CRITERIA_RUNNER
        self.assertIn("_arena_runtime.checks_runtime", CRITERIA_RUNNER)

    def test_builder_ships_oracle_beside_the_grader(self):
        import inspect
        from pipeline.author import build
        from pipeline.author import runtime
        src = inspect.getsource(build.build)
        self.assertIn("runtime.stage(bundle / \"tests\" / runtime.PACKAGE)", src)
        self.assertEqual(runtime.PACKAGE, "_arena_runtime")
        self.assertIn(("oracle.py", "oracle.py"), runtime.FILES)


class ProjectionPathSafety(unittest.TestCase):
    """`spec["file"]` is designer-written, so a projection can name any path."""

    def test_traversal_out_of_the_fixture_is_refused(self):
        import tempfile
        from pipeline.author.oracle import _inside
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "files"; root.mkdir()
            (Path(d) / "secret.json").write_text("the answer")
            with self.assertRaises(ValueError):
                _inside(root, "../secret.json")

    def test_a_normal_relative_path_resolves(self):
        import tempfile
        from pipeline.author.oracle import _inside
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "files"; (root / "sub").mkdir(parents=True)
            (root / "sub" / "a.md").write_text("x")
            self.assertTrue(_inside(root, "sub/a.md").is_file())


class CredentialRouting(unittest.TestCase):
    """Route on the credential, not on which variable happened to hold it."""

    def _headers(self, **env):
        import os, importlib
        from pipeline.calibrate import agent
        for k in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
            os.environ.pop(k, None)
        os.environ.update(env)
        importlib.reload(agent)
        return agent._auth_headers()

    def test_oauth_token_in_the_key_variable_still_uses_bearer(self):
        h = self._headers(ANTHROPIC_API_KEY="sk-ant-oat-abc")
        self.assertIn("Authorization", h)

    def test_api_key_uses_x_api_key(self):
        h = self._headers(ANTHROPIC_API_KEY="sk-ant-api-abc")
        self.assertIn("x-api-key", h)

    def test_missing_credential_raises(self):
        with self.assertRaises(RuntimeError):
            self._headers()


class ModelAndEffort(unittest.TestCase):
    """`budget_tokens` is rejected with a 400 on this model, and thinking is
    adaptive and on by default -- effort is the only dial."""

    def test_every_call_site_shares_one_model_and_effort(self):
        from pipeline.config import ARENA_EFFORT, ARENA_MODEL
        from pipeline.author.designer import MODEL as design_model
        from pipeline.select.classify import MODEL as classify_model
        self.assertEqual(ARENA_MODEL, design_model)
        self.assertEqual(ARENA_MODEL, classify_model)
        self.assertIn(ARENA_EFFORT, ("low", "medium", "high", "xhigh", "max"))

    def test_no_call_site_sends_budget_tokens(self):
        root = Path(__file__).resolve().parent.parent
        for name in ("author/designer.py", "author/agent_designer.py",
                     "select/classify.py", "calibrate/agent.py"):
            text = (root / name).read_text()
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("#:"):
                    continue
                self.assertNotIn("budget_tokens", line,
                                 f"{name} sends budget_tokens; it 400s on this model")


if __name__ == "__main__":
    unittest.main()


class HarborIntegration(unittest.TestCase):
    """The bundle declares a Harbor contract the pipeline had never executed.

    `schema_version = "1.4"`, `artifacts = ["/app/deliverables"]` and a grader
    defaulting to `/app/reward.json` are a promise about a container. Every
    score in the 2026-09 batch came from a three-tool file agent instead, and
    the delivered grader turned out to be broken the whole time.
    """

    def test_benchmark_imports_without_the_factory(self):
        # The runner is taken; the campaign layer it shipped beside is not.
        from pipeline.benchmark import harbor
        self.assertTrue(hasattr(harbor, "run_campaign"))
        source = Path(harbor.__file__).read_text()
        self.assertNotIn("pipeline.factory", source)

    def test_container_is_bounded(self):
        # PLAYBOOK §9: an unbounded verifier is OOM-killed with no exception,
        # no output and no score file -- a silent void, after the agent ran.
        from pipeline.benchmark.harbor import _lifecycle_bytes
        overlay = _lifecycle_bytes().decode()
        self.assertIn("mem_limit:", overlay)
        self.assertIn("cpus:", overlay)

    def test_limits_are_overridable(self):
        import importlib, os
        os.environ["ARENA_HARBOR_MEM"] = "7g"
        try:
            from pipeline.benchmark import harbor
            importlib.reload(harbor)
            self.assertIn("7g", harbor._lifecycle_bytes().decode())
        finally:
            os.environ.pop("ARENA_HARBOR_MEM", None)
            importlib.reload(harbor)

    def test_void_is_never_folded_into_the_mean(self):
        from pipeline.benchmark.harbor import summarize
        trials = [{"valid": True, "reward": 1.0, "steps": []},
                  {"valid": False, "reward": 0.0, "steps": []}]
        out = summarize(trials, requested=3)
        self.assertEqual(out["valid"], 1)
        self.assertEqual(out["void"], 2)          # 3 requested, 1 valid
        self.assertEqual(out["mean_reward"], 1.0)  # the invalid trial excluded

    def test_no_valid_trial_reports_none_not_zero(self):
        from pipeline.benchmark.harbor import summarize
        out = summarize([{"valid": False, "reward": 0.0, "steps": []}], requested=1)
        self.assertIsNone(out["mean_reward"])

    def test_doctor_refuses_rather_than_guesses(self):
        from pipeline.benchmark.harbor import doctor
        report = doctor(check_docker=False)
        self.assertIn("ok", report)
        self.assertIsInstance(report["errors"], list)


class PackageHygiene(unittest.TestCase):
    """Importing the pipeline must be free of work and free of Harbor.

    Two defects found by the module-import sweep. `pipeline.benchmark
    .history_verifier` imported `harbor` at module scope -- correct inside the
    pinned verifier image, an ImportError anywhere else, so the package could
    not be scanned at all. And `pipeline.audit` was a bare script: importing it
    ran a full 11-bundle audit and rewrote `deep-audit.json`, which makes any
    tool that merely inspects the package a writer.
    """

    def _modules(self):
        import pkgutil
        import pipeline
        return sorted(m.name for m in pkgutil.walk_packages(pipeline.__path__, "pipeline."))

    def test_every_module_imports_without_harbor(self):
        import importlib
        import sys
        self.assertNotIn("harbor", sys.modules, "test bed must not have Harbor loaded")
        failed = []
        for name in self._modules():
            try:
                importlib.import_module(name)
            except Exception as exc:  # noqa: BLE001 - reporting, not handling
                failed.append(f"{name}: {type(exc).__name__}: {exc}")
        self.assertEqual(failed, [], "modules failed to import")

    def test_import_writes_nothing_to_stdout(self):
        import contextlib
        import importlib
        import io
        noisy = []
        for name in self._modules():
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                importlib.import_module(name)
            if buf.getvalue().strip():
                noisy.append(f"{name} ({len(buf.getvalue())} bytes)")
        self.assertEqual(noisy, [], "import-time side effects")

    def test_audit_is_callable_not_a_script(self):
        from pipeline import audit
        self.assertTrue(callable(getattr(audit, "main", None)),
                        "pipeline.audit must expose main(); ./arena audit runs it via -m")

    def test_history_verifier_refuses_to_run_without_harbor(self):
        import subprocess
        import sys
        # Exercise the missing-dependency path in an isolated interpreter even
        # when this suite itself runs inside the real pinned Harbor environment.
        code = f"""import sys
sys.path.insert(0, {str(Path(__file__).resolve().parents[2])!r})
from pipeline.benchmark import history_verifier
assert history_verifier.HARBOR_ERROR is not None
try:
    history_verifier.HistoryVerifier()
except ImportError as exc:
    assert 'Harbor is not installed' in str(exc)
else:
    raise AssertionError('Missing Harbor was silently accepted')
"""
        result = subprocess.run([sys.executable, "-I", "-S", "-c", code],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_doctor_reports_every_fault_not_just_the_first(self):
        """A missing Harbor must not hide a missing Docker.

        doctor() used to return early when the executable was absent, which
        skipped the Docker probes and the base-image provenance entirely. You
        fixed Harbor, re-ran, and only then learned Docker was down too.
        """
        import os
        from pipeline.benchmark import harbor
        missing = "/nonexistent/arena-harbor-test/bin/harbor"
        previous = os.environ.get("ARENA_HARBOR_BIN")
        os.environ["ARENA_HARBOR_BIN"] = missing
        try:
            report = harbor.doctor(check_docker=True)
        finally:
            if previous is None:
                os.environ.pop("ARENA_HARBOR_BIN", None)
            else:
                os.environ["ARENA_HARBOR_BIN"] = previous
        self.assertFalse(report["ok"])
        self.assertTrue(any("executable missing" in e for e in report["errors"]))
        self.assertIn("base_image", report,
                      "Docker section skipped: doctor returned before probing")

    def test_either_anthropic_credential_satisfies_the_gate(self):
        """An OAuth token is a usable credential; the CLI gate must accept it.

        Every call site reads `ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY`, but
        the gate required the key by name -- so a workspace holding only the
        OAuth token was told to "create keys.env", which it already had. This
        stopped a real end-to-end run.
        """
        from pipeline import cli
        self.assertEqual(cli._unsatisfied({"ANTHROPIC_AUTH_TOKEN": "sk-ant-oat-x"}), [])
        self.assertEqual(cli._unsatisfied({"ANTHROPIC_API_KEY": "sk-ant-api-x"}), [])
        self.assertEqual(cli._unsatisfied({"OPENAI_API_KEY": "sk-x"}),
                         ["ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY"])
        self.assertEqual(cli._unsatisfied({}),
                         ["ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY"])
        self.assertEqual(cli._unsatisfied({"ANTHROPIC_AUTH_TOKEN": ""}),
                         ["ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY"],
                         "an empty value must not count as set")


class StepHistoryContainment(unittest.TestCase):
    """The vendored history builder is a containment layer, so attack it.

    `build_history` copies earlier-step captures into a packet that is uploaded
    into the verifier container. Everything it trusts comes from a task config
    and a trial directory, so a path that escapes, a symlink that redirects, or
    a device node that blocks on read is the whole threat model. It arrived
    with no tests; these are the ones that matter.
    """

    def setUp(self):
        import tempfile
        from pipeline.benchmark import step_history
        self.sh = step_history
        self.tmp = tempfile.TemporaryDirectory(prefix="arena-hist-test-")
        # .resolve() matters. On macOS a temp dir sits under /var, which is a
        # symlink to /private/var, so _safe() refuses EVERY path beneath it --
        # including benign ones. Without resolving, an "attack was rejected"
        # assertion passes no matter what you feed it, which is why
        # test_benign_path_is_accepted below is a required control: it fails
        # loudly if the guard has gone back to refusing everything.
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)

    def test_benign_path_is_accepted(self):
        """Control. Every other test here asserts a refusal; this proves the
        guard discriminates rather than rejecting its whole input space."""
        (self.root / "ordinary.txt").write_text("x")
        accepted = self.sh._safe(self.root, "ordinary.txt")
        self.assertEqual(accepted.name, "ordinary.txt")
        nested = self.root / "a" / "b"
        nested.mkdir(parents=True)
        (nested / "deep.txt").write_text("y")
        self.assertEqual(self.sh._safe(self.root, "a/b/deep.txt").name, "deep.txt")

    def test_relative_path_traversal_is_refused(self):
        for bad in ("../etc/passwd", "a/../../b", "..", "a/..",):
            with self.subTest(path=bad), self.assertRaises(self.sh.HistoryEvidenceError):
                self.sh._safe(self.root, bad)

    def test_absolute_and_malformed_paths_are_refused(self):
        for bad in ("/etc/passwd", "", "a\\b", "a\0b"):
            with self.subTest(path=bad), self.assertRaises(self.sh.HistoryEvidenceError):
                self.sh._path(bad, absolute=False)

    def test_absolute_flag_is_enforced_both_ways(self):
        with self.assertRaises(self.sh.HistoryEvidenceError):
            self.sh._path("app/out", absolute=True)      # wanted absolute
        with self.assertRaises(self.sh.HistoryEvidenceError):
            self.sh._path("/app/out", absolute=False)    # wanted relative
        self.assertEqual(self.sh._path("/app/out", absolute=True).parts[1], "app")

    def test_symlinked_leaf_is_refused(self):
        (self.root / "real").write_text("x")
        (self.root / "link").symlink_to(self.root / "real")
        with self.assertRaises(self.sh.HistoryEvidenceError):
            self.sh._safe(self.root, "link")

    def test_symlinked_parent_directory_is_refused(self):
        """The escape is the directory, not the file -- checking the leaf alone misses it."""
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret").write_text("x")
        (self.root / "via").symlink_to(outside)
        with self.assertRaises(self.sh.HistoryEvidenceError):
            self.sh._safe(self.root, "via/secret")

    def test_non_regular_file_is_refused(self):
        import os
        fifo = self.root / "pipe"
        try:
            os.mkfifo(fifo)
        except (AttributeError, OSError):
            self.skipTest("mkfifo unavailable")
        with self.assertRaises(self.sh.HistoryEvidenceError):
            self.sh._regular(fifo)

    def test_missing_file_is_an_evidence_error_not_a_silent_skip(self):
        with self.assertRaises(self.sh.HistoryEvidenceError):
            self.sh._regular(self.root / "never-written")

    def test_declaration_restricted_to_app_on_the_main_service(self):
        self.assertEqual(self.sh._declaration("/app/deliverables")["host"].as_posix(),
                         "app/deliverables")
        for bad in ({"source": "/etc/shadow"}, {"source": "/app/x", "service": "sidecar"},
                    {"source": "/"}, 42):
            with self.subTest(declaration=bad), self.assertRaises(self.sh.HistoryEvidenceError):
                self.sh._declaration(bad)

    def test_duplicate_manifest_keys_are_refused(self):
        """Last-wins JSON parsing lets a second key quietly override the first."""
        with self.assertRaises(self.sh.HistoryEvidenceError):
            self.sh._json(b'{"a": 1, "a": 2}')
        self.assertEqual(self.sh._json(b'{"a": 1}'), {"a": 1})

    def test_all_three_call_sites_share_one_credential_router(self):
        """The routing lived in three byte-identical copies; now one module.

        The shapes are not interchangeable -- an OAuth token sent as x-api-key
        401s and reads like a bad key -- so every call site must agree.
        """
        from pipeline import credential
        from pipeline.author import designer
        from pipeline.calibrate import agent
        from pipeline.select import classify
        env = {"ANTHROPIC_AUTH_TOKEN": "sk-ant-oat-fixture"}
        expected = {"Authorization": "Bearer sk-ant-oat-fixture",
                    "anthropic-beta": "oauth-2025-04-20"}
        self.assertEqual(credential.auth_headers(env), expected)
        self.assertEqual(credential.auth_headers({"ANTHROPIC_API_KEY": "sk-ant-api-x"}),
                         {"x-api-key": "sk-ant-api-x"})
        for module in (designer, agent, classify):
            with self.subTest(module=module.__name__):
                self.assertIs(module._shared_auth_headers, credential.auth_headers)

    def test_oauth_token_pasted_into_the_key_variable_still_routes_as_oauth(self):
        """Keying on the variable name instead of the prefix is the 401 bug."""
        from pipeline import credential
        self.assertEqual(
            credential.auth_headers({"ANTHROPIC_API_KEY": "sk-ant-oat-pasted"}),
            {"Authorization": "Bearer sk-ant-oat-pasted",
             "anthropic-beta": "oauth-2025-04-20"})


class GateRepairLoop(unittest.TestCase):
    """A gate blocker must reach the designer, not just end the task.

    The gates run after the bundle is built, so their findings used to be
    terminal: `blocked`, and nothing learned from it. The designer already
    repairs concrete named defects -- it had simply never been shown these.
    """

    def _orchestrate(self):
        from pipeline import orchestrate
        return orchestrate

    def test_gate_repairs_default_to_the_policy_budget_and_stay_overridable(self):
        """Bounded repair, not zero repair.

        This asserted `GATE_REPAIRS == 0` -- "only an explicit repair allowance
        enables a revision". Measured, that default discarded 47 of 86
        candidates in `envs-cat-v2`, every one of them holding review findings
        that named the exact file and the exact line to change. It also
        silently disabled the difficulty loop: a draft the presolve screen
        rejects as too easy had nothing to spend on a redesign, so it was
        blocked rather than made harder, which is the opposite of the point.

        What replaced it is a budget AND an invariant, because a budget alone
        still permits two futile passes: `repair.admissible` requires the
        finding set to strictly shrink and treats a repeated finding as
        terminal. Zero remains available for a run that genuinely wants one
        shot.
        """
        import importlib
        import os
        from pipeline import policy
        orchestrate = self._orchestrate()
        self.assertEqual(orchestrate.GATE_REPAIRS, policy.MAX_REPAIR_PASSES)
        previous = os.environ.get("ARENA_GATE_REPAIRS")
        try:
            for requested in ("0", "1"):
                os.environ["ARENA_GATE_REPAIRS"] = requested
                reloaded = importlib.reload(orchestrate)
                self.assertEqual(reloaded.GATE_REPAIRS, int(requested),
                                 "an explicit allowance always wins")
        finally:
            if previous is None:
                os.environ.pop("ARENA_GATE_REPAIRS", None)
            else:
                os.environ["ARENA_GATE_REPAIRS"] = previous
            importlib.reload(orchestrate)

    def test_both_designers_accept_gate_feedback(self):
        import inspect
        from pipeline.author import agent_designer, designer
        for fn in (designer.design, agent_designer.design):
            with self.subTest(fn=fn.__module__):
                self.assertIn("feedback", inspect.signature(fn).parameters)

    def _patched_build_one(self, verdicts, review_results=None, events=None, repairs=1):
        """Run build_one with every stage faked; return (result, designer calls).

        `verdicts` is the gate verdict to return on each successive round.
        """
        import json
        import os
        import tempfile
        import types
        from pipeline import orchestrate
        from pipeline.calibrate import run as calibrate_run

        calls = []
        events = events if events is not None else []
        reviews = iter(review_results) if review_results is not None else None

        def fake_review(bundle, budget):
            events.append("review")
            return next(reviews) if reviews is not None else {"verdict": "green", "findings": []}

        self.revision_flags = []

        def fake_designer(row, extraction, bundle, feedback=None, **options):
            events.append("design")
            calls.append(feedback)
            self.revision_flags.append(options.get("revision"))
            return {"forged_applicable": False, "forged_reason": ""}

        rounds = iter(verdicts)

        def fake_run_bundle(bundle, cwd, calibration=None):
            verdict = next(rounds)
            blockers = ([] if verdict == "green" else
                        [{"code": "trap-not-discriminating",
                          "detail": "trap abbreviated_prose catches nothing"}])
            return {"verdict": verdict,
                    "results": [{"gate": "trap.beatable", "blockers": blockers}]}

        def fake_probe_run(bundle, work, forged_applicable=False, forged_reason=""):
            return {"results": {}}

        def fake_campaign(bundle, model, rollouts, workers=1, rollout_budget=None):
            events.append("calibrate")
            # The validity probe now runs in every build, not only under
            # --calibrate. A clean campaign raises no suspicion, so the loop
            # must accept and stop.
            return {"summary": {"requested": rollouts, "void": 0,
                                "mean_reward": 0.5},
                    "checks": {**{f"c{i}": {"kind": "objective", "passed": 1,
                                      "failed": 2, "weight": 20} for i in range(4)},
                               "stretch": {"kind": "objective", "passed": 0, "failed": 3, "weight": 20}},
                    "rollouts": []}

        def fake_build(spec, bundle):
            # The real build stage creates the bundle and writes traps.json;
            # the orchestrator reads it back immediately afterwards.
            (bundle / "authoring").mkdir(parents=True, exist_ok=True)
            (bundle / "authoring" / "traps.json").write_text(json.dumps({"traps": []}))

        # These exercise the repair LOOP through the injected designer.
        saved = {}
        targets = [(orchestrate, "GATE_REPAIRS", repairs),
                   (orchestrate, "run_bundle", fake_run_bundle),
                   (orchestrate, "_review_candidate", fake_review),
                   (orchestrate.extract_stage, "extract",
                    lambda s, i: types.SimpleNamespace(moments=[1, 2, 3])),
                   (orchestrate.extract_stage, "write", lambda e, b: None),
                   (orchestrate.build_stage, "build", fake_build),
                   (orchestrate.assurance_stage, "generated_problems", lambda b: []),
                   (orchestrate.assurance_stage, "controls", lambda b: {"ok": True, "errors": []}),
                   (orchestrate.probe_stage, "run", fake_probe_run),
                   (orchestrate.faithfulness, "build",
                    lambda b, s, i: {"faithfulness_by_bytes": 1.0}),
                   # A build must never reach a solver: the screen runs once
                   # the whole batch exists, so this fake must stay uncalled.
                   (calibrate_run, "campaign", fake_campaign)]
        for obj, name, replacement in targets:
            saved[(obj, name)] = getattr(obj, name)
            setattr(obj, name, replacement)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = orchestrate.build_one(
                    {"session_id": "s", "seed_index": 0, "tier": 1,
                     "classification": {"domain": "x", "usable_moments": 3}},
                    1, root, fake_designer, orchestrate.Budget(4))
        finally:
            for (obj, name), original in saved.items():
                setattr(obj, name, original)
        assert "calibrate" not in events, "a single task's build reached a solver"
        return result, calls

    def test_green_on_the_first_gate_does_not_redesign(self):
        """Control: the loop must not cost a second design call when nothing is wrong."""
        result, calls = self._patched_build_one(["green"])
        self.assertEqual(result.status, "validated")
        self.assertEqual(len(calls), 1, "redesigned a bundle that had already passed")
        self.assertEqual(result.gate_rounds, 1)

    def test_blocked_bundle_is_redesigned_with_the_blocker(self):
        result, calls = self._patched_build_one(["blocked", "green"])
        self.assertEqual(result.status, "validated", "repair round did not recover the bundle")
        self.assertEqual(len(calls), 2)
        self.assertIsNone(calls[0], "first attempt must carry no feedback")
        self.assertTrue(any("trap-not-discriminating" in line for line in calls[1]),
                        f"second attempt did not receive the blocker: {calls[1]}")
        self.assertEqual(result.gate_rounds, 2)

    def test_only_a_repair_round_is_designed_as_a_revision(self):
        # Re-review: the mandate followed "was feedback passed", so a first
        # design carrying a brief was told to revise; now the build says which.
        self._patched_build_one(["blocked", "green"])
        self.assertEqual(self.revision_flags, [False, True])

    def test_every_revision_caller_says_it_is_one(self):
        import inspect
        from pipeline import harden, repair
        from pipeline.author import agent_designer
        self.assertIn("revision: bool = False", inspect.getsource(agent_designer.design))
        self.assertIn("(REVISION_MANDATE if revision else AUTHORING_MANDATE)",
                      inspect.getsource(agent_designer.design))
        self.assertIn("revision=True", inspect.getsource(harden.propose))
        self.assertIn("revision=True", inspect.getsource(repair.revise))

    def test_blocked_bundle_is_retained_without_automatic_revision(self):
        result, calls = self._patched_build_one(["blocked"], repairs=0)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(len(calls), 1)
        self.assertTrue(result.repair_feedback)

    def test_still_blocked_after_the_repair_is_reported_not_retried_forever(self):
        result, calls = self._patched_build_one(["blocked", "blocked"])
        self.assertEqual(result.status, "blocked")
        self.assertEqual(len(calls), 2, "must stop at GATE_REPAIRS, not loop")
        self.assertTrue(result.blockers)


class TrapProbeDemonstration(unittest.TestCase):
    """A trap must name a probe that can score below the reference.

    kw-a013 was built, probed and gated before anyone noticed its
    `abbreviated_prose` trap pointed at `untidy_correct` -- the reference answer
    reformatted, which the grader is required to accept, so it scores 1.0 by
    construction. `trap.beatable` blocked the bundle after a full build. The
    same fault is decidable from the spec alone.
    """

    def _spec(self, probe):
        return {
            "checks": [{"id": "c1", "kind": "objective", "weight": 100}],
            "traps": [{"id": "t1", "probe": probe, "checks": ["c1"],
                       "provenance": "trace_derived", "derived_from": "turn 3",
                       "quote": "no, keep the full prose"}],
        }

    def _trap_problems(self, probe):
        from pipeline.author import validate as v
        spec = self._spec(probe)
        ids = {"c1"}
        problems = []
        for trap in spec["traps"]:
            tid = trap["id"]
            for cid in trap.get("checks") or []:
                if cid not in ids:
                    problems.append(f"trap {tid!r}: drives check {cid!r}")
            if trap.get("probe") in v.UNDEMONSTRATING_PROBES:
                problems.append(f"trap {tid!r}: probe {trap['probe']!r} always scores")
        return problems

    def test_golden_and_untidy_correct_are_rejected(self):
        for probe in ("golden", "untidy_correct"):
            with self.subTest(probe=probe):
                self.assertTrue(self._trap_problems(probe),
                                f"{probe} cannot demonstrate a trap")

    def test_discriminating_probes_are_accepted(self):
        """Control: the rule must not reject every probe."""
        for probe in ("plausible_wrong", "destructive", "answer_lookup", "per_trap"):
            with self.subTest(probe=probe):
                self.assertEqual(self._trap_problems(probe), [])

    def test_the_guarded_set_matches_the_probes_that_must_score_one(self):
        """`golden` and `untidy_correct` are the two REQUIRED probes pinned to 1.0."""
        from pipeline.author import probes
        from pipeline.author.validate import UNDEMONSTRATING_PROBES
        self.assertTrue(UNDEMONSTRATING_PROBES <= set(probes.REQUIRED),
                        "guarded probes must be real probe names")


class DeclaredProbeExpectationsAreEnforced(unittest.TestCase):
    """REQUIRED_PROBES stated contracts that nothing checked.

    The table said `plausible_wrong` must score < 1.0 and `untidy_correct` must
    still score 1.0. Only `forged_state` and `answer_lookup` were ever asserted,
    so the other two were documentation.

    The subtlety that a first version of this gate got wrong: the probe mutates
    ONE numeric scalar and stops. When it finds none it mutates nothing and
    grades a byte-identical copy of the reference, where 1.0 is the correct
    result. Blocking on that reads an inert probe as a task defect. It is a
    WARN -- no evidence -- and only a corrupted-but-unnoticed value blocks.
    """

    def _findings(self, results):
        import json
        import tempfile
        from pipeline.gates import difficulty
        from pipeline.gates.base import GateContext
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "verification").mkdir()
            (bundle / "verification" / "probes.json").write_text(
                json.dumps({"results": results}))
            # _trap_beatable reads the trap list too; an empty one isolates the
            # probe expectations from trap-specific findings.
            (bundle / "authoring").mkdir()
            (bundle / "authoring" / "traps.json").write_text(
                json.dumps({"traps": []}))
            ctx = GateContext(task_dir=bundle, repo_root=bundle,  # gates re-run probes; logic tests hand them the report
                             extras={"probe_report": json.loads((bundle / "verification" / "probes.json").read_text())})
            findings, _ = difficulty._trap_beatable(ctx)
        return {f.code for f in findings}

    def _base(self, **over):
        results = {
            "seed_zero": {"reward": 0.0, "objectives": {}, "guardrails": {}},
            "golden": {"reward": 1.0},
            "untidy_correct": {"reward": 1.0},
            "plausible_wrong": {"reward": 0.5, "mutated": ["audit.json:count"]},
            "destructive": {"reward": 0.0},
            "forged_state": {"reward": 0.0},
            "answer_lookup": {"reward": 0.0},
        }
        results.update(over)
        return results

    def test_healthy_probe_set_is_clean(self):
        """Control: a good bundle must not trip the new rules."""
        codes = self._findings(self._base())
        self.assertNotIn("plausible-wrong-scores-reference", codes)
        self.assertNotIn("plausible-wrong-margin-thin", codes)
        self.assertNotIn("untidy-correct-penalised", codes)

    def test_corrupted_value_scoring_the_reference_blocks(self):
        """The probe shifted a real value and the grader did not notice."""
        codes = self._findings(self._base(
            plausible_wrong={"reward": 1.0, "mutated": ["audit.json:count"]}))
        self.assertIn("plausible-wrong-scores-reference", codes)

    def test_inert_probe_warns_rather_than_blocking(self):
        """kw-a005/a006: nothing to mutate, so 1.0 is correct, not a defect.

        Blocking here would reject a bundle for a probe that never ran -- and
        passing silently would let an unprobed surface read as a clean one.
        """
        codes = self._findings(self._base(
            plausible_wrong={"reward": 1.0, "mutated": []}))
        self.assertIn("plausible-wrong-inert", codes)
        self.assertNotIn("plausible-wrong-scores-reference", codes)

    def test_thin_margin_is_not_itself_a_finding(self):
        """One shifted scalar costs that check's weight, about 1/n. Normal."""
        codes = self._findings(self._base(
            plausible_wrong={"reward": 0.93, "mutated": ["audit.json:count"]}))
        self.assertNotIn("plausible-wrong-scores-reference", codes)
        self.assertNotIn("plausible-wrong-inert", codes)
        self.assertFalse({c for c in codes if "margin" in c},
                         "margin measures 1/n, not task quality")

    def test_penalising_untidy_but_correct_work_blocks(self):
        """A grader scoring formatting makes right answers read as failures."""
        codes = self._findings(self._base(untidy_correct={"reward": 0.8}))
        self.assertIn("untidy-correct-penalised", codes)

    def test_inapplicable_probes_are_not_double_punished(self):
        codes = self._findings(self._base(
            plausible_wrong={"reward": 1.0, "mutated": ["a.json:b"],
                             "applicable": False, "reason": "x" * 50}))
        self.assertNotIn("plausible-wrong-scores-reference", codes)


class PlausibleWrongCoversSetAnswers(unittest.TestCase):
    """The decoy probe must reach set-valued objectives, not only numbers.

    Measured on this batch: 1 of 84 objectives is numeric and 46 are
    `set_equals`. Requiring a float meant the probe found nothing to touch in
    two bundles, graded a byte-identical copy of the reference, scored 1.0, and
    read like proof that wrong answers are caught. Dropping one member of a set
    is the missed-one-item error -- the same shape as the off-by-one.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory(prefix="arena-decoy-")
        self.root = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)

    def _check(self, **over):
        from pipeline.author.checks import Check
        kwargs = dict(id="c1", kind="objective", weight=100.0, basis="b",
                      assertion="set_equals",
                      actual={"op": "field", "file": "out.json", "path": "items"},
                      target={"op": "literal", "value": ["a", "b", "c"],
                              "why": "fixed test vector; this probe test does not exercise fixture derivation"})
        kwargs.update(over)
        return Check(**kwargs)

    def _ws(self):
        """A real Workspace: `literal` targets still go through evaluate()."""
        from pipeline.author.checks import Workspace
        source = self.root / "src"
        source.mkdir(exist_ok=True)
        return Workspace(source=source, submitted=self.root)

    def _run(self, payload, check):
        import json
        from pipeline.author import probes
        (self.root / "out.json").write_text(json.dumps(payload))
        changed = probes._plausible_wrong(self.root, [check], self._ws())
        return changed, json.loads((self.root / "out.json").read_text())

    def test_a_set_valued_answer_loses_one_member(self):
        changed, data = self._run({"items": ["a", "b", "c"]}, self._check())
        self.assertTrue(changed, "probe found nothing to mutate on a set answer")
        self.assertEqual(data["items"], ["a", "b"])
        self.assertIn("dropped", changed[0])

    def test_a_single_member_set_is_left_alone(self):
        """Emptying it is the empty_deliverable probe's job, and reads as
        'not attempted' rather than 'wrong'."""
        changed, data = self._run({"items": ["only"]}, self._check())
        self.assertEqual(changed, [])
        self.assertEqual(data["items"], ["only"])

    def test_a_numeric_target_is_still_preferred(self):
        """The documented off-by-one stays first choice where one exists."""
        import json
        from pipeline.author import probes
        numeric = self._check(id="n1", assertion="equals",
                              actual={"op": "field", "file": "out.json",
                                      "path": "count"},
                              target={"op": "literal", "value": 3,
                                      "why": "fixed test vector; this probe test does not exercise fixture derivation"})
        sets = self._check()
        (self.root / "out.json").write_text(json.dumps({"count": 3, "items": ["a", "b", "c"]}))
        changed = probes._plausible_wrong(self.root, [sets, numeric], self._ws())
        data = json.loads((self.root / "out.json").read_text())
        self.assertTrue(changed)
        self.assertEqual(data["count"], 4, "numeric shift should have been used")
        self.assertEqual(data["items"], ["a", "b", "c"], "set left untouched")

    def test_only_one_mutation_is_made(self):
        """A probe that corrupts everything measures nothing in particular."""
        import json
        from pipeline.author import probes
        second = self._check(id="c2",
                             actual={"op": "field", "file": "out.json",
                                     "path": "others"})
        (self.root / "out.json").write_text(
            json.dumps({"items": ["a", "b", "c"], "others": ["x", "y", "z"]}))
        changed = probes._plausible_wrong(self.root, [self._check(), second], self._ws())
        data = json.loads((self.root / "out.json").read_text())
        self.assertEqual(len(changed), 1)
        intact = [v for v in (data["items"], data["others"]) if len(v) == 3]
        self.assertEqual(len(intact), 1, "exactly one answer should have been touched")


class PlausibleWrongCoversVerdictAnswers(PlausibleWrongCoversSetAnswers):
    """a-111 (2026-09-28): every objective an `equals` over booleans, enums and
    flag objects. The probe found nothing numeric or set-valued, graded the
    reference itself, scored 1.0 and was counted as a confirmed hack. The wrong
    yes/no is this construct's plausible mistake."""

    def _flag(self, path, value):
        return self._check(id=path, assertion="equals",
                           actual={"op": "field", "file": "out.json", "path": path},
                           target={"op": "literal", "value": value,
                                   "why": "fixed test vector; this probe test does not exercise fixture derivation"})

    def test_a_yes_no_answer_is_flipped(self):
        changed, data = self._run({"covered": False, "action": "pin"}, self._flag("covered", False))
        self.assertEqual(data["covered"], True)
        self.assertIn("False -> True", changed[0])

    def test_a_flag_inside_an_object_is_flipped(self):
        changed, data = self._run({"dep": {"name": "zod", "conflict": True}},
                                  self._flag("dep", {"name": "zod", "conflict": True}))
        self.assertEqual(data["dep"], {"name": "zod", "conflict": False})
        self.assertIn("dep.conflict", changed[0])

    def test_a_numeric_answer_still_comes_first(self):
        import json
        from pipeline.author import probes
        (self.root / "out.json").write_text(json.dumps({"covered": True, "count": 3}))
        changed = probes._plausible_wrong(self.root, [self._flag("covered", True), self._flag("count", 3)], self._ws())
        data = json.loads((self.root / "out.json").read_text())
        self.assertEqual((data["count"], data["covered"]), (4, True))


class LiteralTargetErrorIsActionable(unittest.TestCase):
    """The repair message must show the fix, not only name the rule.

    kw-a005 failed design three times -- nine repair attempts -- re-emitting
    the same literal target. It was told the rule every time and never the
    shape of the correction.
    """

    def _raise(self, expr):
        import tempfile
        from pipeline.author.checks import CheckError, Workspace, evaluate
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "src").mkdir()
            ws = Workspace(source=root / "src", submitted=root)
            with self.assertRaises(CheckError) as caught:
                evaluate(expr, ws, "source")
            return str(caught.exception)

    def test_message_carries_a_paste_ready_expression(self):
        message = self._raise({"op": "literal", "value": "(?i)workflow"})
        self.assertIn("replace it with:", message)
        self.assertIn('"why"', message)
        self.assertIn("(?i)workflow", message, "must echo the original value")

    def test_the_rule_still_holds(self):
        """Control: a literal without 'why' is still refused, not repaired for it."""
        from pipeline.author.checks import CheckError
        self.assertIn("must carry a 'why'",
                      self._raise({"op": "literal", "value": 3}))

    def test_a_literal_with_why_is_accepted(self):
        import tempfile
        from pipeline.author.checks import Workspace, evaluate
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "src").mkdir()
            ws = Workspace(source=root / "src", submitted=root)
            value = evaluate({"op": "literal", "value": "ABSTAIN",
                              "why": "the instruction fixes this sentinel"},
                             ws, "source")
        self.assertEqual(value, "ABSTAIN")

    def test_submitted_role_needs_no_why(self):
        """`why` guards hand-typed ANSWERS; an actual-side literal is not one."""
        import tempfile
        from pipeline.author.checks import Workspace, evaluate
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "src").mkdir()
            ws = Workspace(source=root / "src", submitted=root)
            self.assertEqual(evaluate({"op": "literal", "value": 1}, ws, "submitted"), 1)


class ShippedGraderVerification(unittest.TestCase):
    """`arena verify` runs the grader as the container gets it.

    Everything upstream grades through our harness, which imports the runtime
    from the repository. The container has only `tests/`, the fixture and the
    submission. Eleven bundles once shipped with a `criteria.py` that raised on
    its first check while every gate was green.
    """

    def test_incomplete_bundle_is_skipped_not_failed(self):
        """A half-built tree is 'could not check', never 'checked and wrong'."""
        import tempfile
        from pipeline import verify_shipped
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "kw-a001-x"
            (bundle / "tests").mkdir(parents=True)
            result = verify_shipped.verify(bundle)
        self.assertTrue(result["incomplete"])
        self.assertFalse(result["ok"])
        self.assertIn("not built yet", " ".join(result["errors"]))

    def test_built_bundle_missing_its_grader_is_a_failure(self):
        """Control: with task.toml present, a missing grader IS a defect."""
        import tempfile
        from pipeline import verify_shipped
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "kw-a001-x"
            bundle.mkdir(parents=True)
            (bundle / "task.toml").write_text('schema_version = "1.4"\n')
            result = verify_shipped.verify(bundle)
        self.assertFalse(result.get("incomplete"))
        self.assertFalse(result["ok"])
        self.assertIn("no tests/criteria.py", " ".join(result["errors"]))

    def test_a_relative_root_grades_the_same_as_an_absolute_one(self):
        """The grader runs with cwd=scratch, so relative paths resolved wrong.

        `./arena verify envs-cat` passes a relative path where the default is
        absolute, so every fixture read raised and the whole tree reported
        FAIL. Built synthetically rather than against `envs/`: which trees
        exist changes as batches are archived, and a test whose result depends
        on that is testing the repository, not the code.
        """
        import os
        import subprocess
        import sys
        import tempfile
        from pipeline.author.build import CRITERIA_RUNNER

        repo = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "envs-probe"
            bundle = tree / "a-001-relative"
            (bundle / "tests" / "_arena_runtime").mkdir(parents=True)
            (bundle / "environment" / "files").mkdir(parents=True)
            (bundle / "solution" / "submission").mkdir(parents=True)
            import shutil
            runtime = bundle / "tests" / "_arena_runtime"
            (runtime / "__init__.py").write_text('"""Self-contained grader runtime generated by the Arena builder."""\n')
            shutil.copy(repo / "pipeline/author/checks.py", runtime / "checks_runtime.py")
            shutil.copy(repo / "pipeline/author/oracle.py", runtime / "oracle.py")
            shutil.copy(repo / "pipeline/author/contracts.py", runtime / "contracts.py")
            shutil.copy(repo / "pipeline/author/path_witness.py", runtime / "path_witness.py")
            shutil.copy(repo / "pipeline/author/subset_witness.py", runtime / "subset_witness.py")
            (bundle / "tests" / "criteria.py").write_text(CRITERIA_RUNNER)
            (bundle / "task.toml").write_text('schema_version = "1.4"\n[[steps]]\nname = "01-main"\n')
            (bundle / "tests/rubric.json").write_text(json.dumps({"01-main": ["c1"]}))
            why = "fixed sentinel; this path test does not exercise derivation"
            (bundle / "tests" / "checks.json").write_text(json.dumps({"checks": [
                {"id": "c1", "kind": "objective", "weight": 100, "band": "core",
                 "dimension": "core", "basis": "b", "assertion": "equals",
                 "actual": {"op": "field", "file": "out.json", "path": "value"},
                 "target": {"op": "literal", "value": "A", "why": why}}]}))
            (bundle / "solution" / "submission" / "out.json").write_text(
                json.dumps({"value": "A"}))
            # `verify` now also executes the shipped reference; stage one.
            from pipeline.author import solution
            solution.stage(bundle, {"steps": [{"name": "01-main"}], "projections": [],
                                    "checks": json.loads((bundle / "tests/checks.json").read_text())["checks"]},
                           "01-main", bundle / "steps/01-main/solution")

            def sweep(root, cwd):
                proc = subprocess.run(
                    [sys.executable, "-m", "pipeline.verify_shipped", root],
                    cwd=cwd, capture_output=True, text=True, timeout=300,
                    env={**os.environ, "PYTHONPATH": str(repo)})
                return proc.stdout.strip().splitlines()[-1]

            relative = sweep("envs-probe", tmp)
            absolute = sweep(str(tree), tmp)

        self.assertEqual(relative, absolute,
                         "a relative root must grade identically to an absolute one")
        self.assertIn("1/1", relative, "the synthetic bundle must grade cleanly")

    def test_both_naming_schemes_are_found(self):
        """`a-001-` is current, `kw-a001-` names everything built before it.

        A sweep that silently skipped one scheme would report a clean result
        over half the corpus.
        """
        import tempfile
        from pipeline.config import bundle_paths
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("a-001-new-scheme", "kw-a001-old-scheme", "notes"):
                (root / name).mkdir()
            found = {p.name for p in bundle_paths(root)}
        self.assertEqual(found, {"a-001-new-scheme", "kw-a001-old-scheme"})

    def test_delivered_names_are_found(self):
        """`arena verify F2-scenario/` used to report "no bundles" on a real batch."""
        import tempfile
        from pipeline.config import bundle_paths
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("F2-scenario/a_f2_content-writing", "F3-replay/a_f3_x", "F2-scenario/notes"):
                (root / name).mkdir(parents=True)
            self.assertEqual({p.name for p in bundle_paths(root)}, {"a_f2_content-writing", "a_f3_x"})
            self.assertEqual([p.name for p in bundle_paths(root / "F2-scenario")], ["a_f2_content-writing"])


class GatingConcentration(unittest.TestCase):
    """One check must not decide most of the score through `requires`.

    Measured: kw-a006 puts 51% of its weight behind one check and kw-a011 40%;
    both calibrated to an inter-model spread of exactly 0.000. The new kw-a010
    puts 31% behind one and left 4 of 14 checks never attempted at mean 0.033.
    Either everyone clears the prerequisite and that weight is free, or nobody
    does and it cannot be attempted -- both collapse the reachable set.
    """

    def _run(self, checks):
        from pipeline.author.validate import _gating_concentration
        return _gating_concentration({"checks": checks})

    def test_a_long_chain_is_refused(self):
        problems = self._run([
            {"id": "root", "weight": 20},
            {"id": "mid", "weight": 40, "requires": ["root"]},
            {"id": "leaf", "weight": 40},
        ])
        self.assertTrue(problems)
        self.assertIn("root", problems[0])
        self.assertIn("60%", problems[0])

    def test_transitive_dependants_are_counted(self):
        """root -> mid -> leaf: root gates everything, not just mid."""
        problems = self._run([
            {"id": "root", "weight": 10},
            {"id": "mid", "weight": 10, "requires": ["root"]},
            {"id": "leaf", "weight": 30, "requires": ["mid"]},
            {"id": "free", "weight": 50},
        ])
        self.assertTrue(any("'root'" in p and "50%" in p for p in problems),
                        f"transitive weight not counted: {problems}")

    def test_independent_checks_are_clean(self):
        """Control: no requires anywhere means nothing gates anything."""
        self.assertEqual(self._run([{"id": "x", "weight": 50},
                                    {"id": "y", "weight": 50}]), [])

    def test_a_heavy_check_with_no_dependants_is_not_a_gating_fault(self):
        """Weight concentration is a different question; do not conflate them."""
        self.assertEqual(self._run([{"id": "big", "weight": 80},
                                    {"id": "small", "weight": 20}]), [])

    def test_a_short_chain_under_the_threshold_passes(self):
        self.assertEqual(self._run([
            {"id": "a", "weight": 10},
            {"id": "b", "weight": 15, "requires": ["a"]},
            {"id": "c", "weight": 75}]), [])


class ScoringShapeIsDefensible(unittest.TestCase):
    """Enough checks, weights that differ, and every weight argued for.

    The schema described `weight` as `{"type": "number"}` and nothing more, so
    nothing ever asked the designer to justify one. Weights that cannot be
    defended cannot be reviewed, and a rubric nobody can review is where an
    incidental detail comes to outweigh the answer.
    """

    def _weights(self, values, basis="the user corrected this judgement twice in turn 7"):
        return [{"id": f"o{i}", "kind": "objective", "weight": w,
                 "weight_basis": basis} for i, w in enumerate(values)]

    def _run(self, checks):
        from pipeline.author.validate import _scoring_shape
        return _scoring_shape({"checks": checks})

    def _healthy(self):
        checks = self._weights([18, 15, 14, 12, 11, 10, 10, 10])
        checks += [{"id": "g1", "kind": "guardrail", "weight": 0},
                   {"id": "g2", "kind": "guardrail", "weight": 0}]
        return checks

    def test_a_well_formed_rubric_is_clean(self):
        """Control: these rules must not fire on a good task."""
        self.assertEqual(self._run(self._healthy()), [])

    def test_too_few_objectives_is_refused(self):
        problems = self._run(self._weights([20, 18, 16, 14, 12, 10, 10]))
        self.assertTrue(any("at least 8" in p for p in problems), problems)

    def test_uniform_weights_are_refused(self):
        checks = self._healthy()
        for c in checks:
            if c["kind"] == "objective":
                c["weight"] = 12
        self.assertTrue(any("weights must reflect importance" in p
                            for p in self._run(checks)))

    def test_two_buckets_is_not_a_ranking(self):
        checks = self._weights([20, 20, 20, 20, 5, 5, 5, 5])
        checks += [{"id": "g1", "kind": "guardrail", "weight": 0},
                   {"id": "g2", "kind": "guardrail", "weight": 0}]
        self.assertTrue(any("distinct weights" in p for p in self._run(checks)))

    def test_a_weight_without_a_reason_is_refused(self):
        checks = self._healthy()
        checks[0]["weight_basis"] = ""
        self.assertTrue(any("no reasoned basis" in p for p in self._run(checks)))

    def test_important_is_not_a_justification(self):
        checks = self._healthy()
        checks[0]["weight_basis"] = "important"
        self.assertTrue(any("'o0'" in p for p in self._run(checks)))

    def test_one_check_may_not_dominate_the_score(self):
        checks = self._weights([50, 8, 7, 7, 7, 7, 7, 7])
        checks += [{"id": "g1", "kind": "guardrail", "weight": 0},
                   {"id": "g2", "kind": "guardrail", "weight": 0}]
        # The share reported is the EFFECTIVE one -- per step, then the step
        # mean -- because that is the share the grader applies. Asserting on
        # the raw weight share would pass a spec whose lone heavy check sits
        # in a small second step and decides far more than its weight says.
        problems = self._run(checks)
        self.assertTrue(any("of the task reward as graded" in p for p in problems),
                        msg=f"dominance guard silent: {problems}")
        self.assertTrue(any("'o0' carries 50%" in p for p in problems),
                        msg=f"guard did not name the dominant check: {problems}")

    def test_a_weighted_guardrail_double_counts(self):
        checks = self._healthy()
        checks[-1]["weight"] = 10
        self.assertTrue(any("guardrails must be weight 0" in p
                            for p in self._run(checks)))

    def test_weight_basis_survives_onto_the_check(self):
        """It must reach checks.json, or the justification is lost at build."""
        import dataclasses
        from pipeline.author.checks import Check
        self.assertIn("weight_basis", [f.name for f in dataclasses.fields(Check)])


class DifficultyRepairLoop(unittest.TestCase):
    """Well formed is not the same as discriminating.

    A bundle can pass every gate with all of its checks at 0% or 100%. Measured
    on the first batch: 66% floor, 24% stretch, 10.6% trainable, and the five
    bundles with no trainable check all calibrated to an inter-model spread of
    exactly 0.000. The designer never saw a difficulty signal because nothing
    measured one until calibration, which fed back into nothing.
    """

    def test_bands_sort_by_pass_rate(self):
        from pipeline.orchestrate import check_bands
        bands = check_bands({"checks": {
            "always":  {"kind": "objective", "passed": 6, "failed": 0},
            "never":   {"kind": "objective", "passed": 0, "failed": 6},
            "half":    {"kind": "objective", "passed": 3, "failed": 3},
            "twothird":{"kind": "objective", "passed": 4, "failed": 2},
        }})
        self.assertEqual([c for c, _ in bands["floor"]], ["always"])
        self.assertEqual([c for c, _ in bands["stretch"]], ["never"])
        self.assertEqual(sorted(c for c, _ in bands["core"]), ["half", "twothird"])

    def test_gated_out_is_not_counted_as_a_failure(self):
        """`gated_out` is not `failed` -- a check never attempted says nothing."""
        from pipeline.orchestrate import check_bands
        bands = check_bands({"checks": {
            "blocked": {"kind": "objective", "passed": 0, "failed": 0}}})
        self.assertEqual([c for c, _ in bands["unreachable"]], ["blocked"])
        self.assertEqual(bands["stretch"], [],
                         "an unattempted check must not be read as unpassable")

    def test_guardrails_are_excluded_from_the_bands(self):
        """Guardrails protect; they are not part of the difficulty picture."""
        from pipeline.orchestrate import check_bands
        bands = check_bands({"checks": {
            "g": {"kind": "guardrail", "passed": 6, "failed": 0}}})
        self.assertEqual(sum(len(v) for v in bands.values()), 0)

    def test_a_hard_task_is_not_treated_as_a_broken_one(self):
        """Every attempt failing is a legitimate outcome, not a repair trigger.

        The user's rule: a task models score zero on is fine, provided the zero
        is theirs. Redesigning toward a mid-band pass rate would turn a hard
        task into an easier one, which is the opposite of the goal.
        """
        from pipeline.orchestrate import check_bands, suspect_zeros
        campaign = {"summary": {"requested": 6, "void": 0},
                    "checks": {f"h{i}": {"kind": "objective", "passed": 0, "failed": 6}
                               for i in range(8)},
                    "rollouts": [{"misses": {"h0": "overlap_0.05"}}]}
        bands = check_bands(campaign)
        self.assertEqual(len(bands["stretch"]), 8)
        self.assertEqual(suspect_zeros(campaign, bands), [],
                         "a uniformly hard task must raise no suspicion")

    def test_void_rollouts_make_the_run_untrustworthy(self):
        from pipeline.orchestrate import check_bands, suspect_zeros
        campaign = {"summary": {"requested": 6, "void": 3},
                    "checks": {"a": {"kind": "objective", "passed": 0, "failed": 6}},
                    "rollouts": []}
        suspect = suspect_zeros(campaign, check_bands(campaign))
        self.assertTrue(any("VOID" in s for s in suspect))

    def test_unattempted_checks_are_flagged_as_unreachable_not_hard(self):
        from pipeline.orchestrate import check_bands, suspect_zeros
        campaign = {"summary": {"requested": 6, "void": 0},
                    "checks": {"dead": {"kind": "objective", "passed": 0, "failed": 0}},
                    "rollouts": []}
        suspect = suspect_zeros(campaign, check_bands(campaign))
        self.assertTrue(any("NEVER ATTEMPTED" in s for s in suspect))
        self.assertTrue(any("requires" in s for s in suspect))

    def test_a_near_miss_points_at_an_unstated_convention(self):
        """High overlap requests adjudication without presuming a grader defect."""
        from pipeline.orchestrate import check_bands, suspect_zeros
        campaign = {"summary": {"requested": 6, "void": 0},
                    "checks": {"c": {"kind": "objective", "passed": 0, "failed": 6}},
                    "rollouts": [{"misses": {"c": "overlap_0.98"}},
                                 {"misses": {"c": "overlap_0.98"}}]}
        suspect = suspect_zeros(campaign, check_bands(campaign))
        self.assertTrue(any("Similarity alone cannot decide" in s for s in suspect))

    def test_the_reference_answer_scoring_zero_is_always_suspect(self):
        from pipeline.orchestrate import check_bands, suspect_zeros
        campaign = {"summary": {"requested": 6, "void": 0},
                    "checks": {"c": {"kind": "objective", "passed": 0, "failed": 6}},
                    "rollouts": [{"misses": {"c": "equal_normalised"}}]}
        suspect = suspect_zeros(campaign, check_bands(campaign))
        self.assertTrue(any("reference answer verbatim" in s for s in suspect))

    def test_no_difficulty_feedback_reaches_the_build_loop(self):
        """The in-build difficulty loop is gone (2026-09-25): bands and suspect
        zeros are reported by the calibration screen, never fed back into a
        design one task at a time."""
        from pipeline import orchestrate
        for gone in ("difficulty_feedback", "DIFFICULTY_REPAIRS", "MIN_CORE_CHECKS",
                     "pilot_selection", "selection_feedback"):
            self.assertFalse(hasattr(orchestrate, gone), gone)


class SeedCategories(unittest.TestCase):
    """Seeds are classified into Arena's four faithfulness levels (as targets)
    on two independent axes (user, 2026-09-26: the categories are the spec's).

    `replay_readiness` is how much of the workspace we can lift verbatim -- the
    fixture we get free. `corrections` is how often the user pushed back -- the
    failure modes a task can be built around. A seed can be rich in either,
    both, or neither, and what it can carry differs in each case.
    """

    def _row(self, rr, corrections):
        return {"replay_readiness": rr, "corrections": corrections}

    def test_the_four_corners(self):
        from pipeline.select.categories import categorise
        self.assertEqual(categorise(self._row(0.90, 5)), "F3")  # both: Replay
        self.assertEqual(categorise(self._row(0.40, 5)), "F2")  # pushback only: Scenario
        self.assertEqual(categorise(self._row(0.90, 0)), "F2")  # fixture only: Scenario
        self.assertEqual(categorise(self._row(0.40, 1)), "F1")  # a correction pattern only
        self.assertEqual(categorise(self._row(0.40, 0)), "F0")  # nothing recoverable

    def test_boundaries_are_inclusive_at_the_threshold(self):
        from pipeline.select import categories as cat
        self.assertEqual(cat.categorise(
            self._row(cat.RR_RICH, cat.CORRECTIONS_STRONG)), "F3")
        self.assertEqual(cat.categorise(
            self._row(cat.RR_LIFTABLE, cat.CORRECTIONS_STRONG - 1)), "F2")

    def test_correction_signal_outranks_a_thin_fixture(self):
        """A real dispute is worth more than documents: still F2, not F1."""
        from pipeline.select import categories as cat
        just_under = cat.RR_LIFTABLE - 0.01
        self.assertEqual(cat.categorise(self._row(just_under, 9)), "F2")

    def test_every_seed_lands_in_exactly_one_category(self):
        from pipeline.select.categories import CATEGORIES, categorise
        for rr in (0.0, 0.3, 0.52, 0.64, 0.9, 1.0):
            for corrections in (0, 1, 2, 3, 20):
                with self.subTest(rr=rr, corrections=corrections):
                    self.assertIn(categorise(self._row(rr, corrections)), CATEGORIES)

    def test_missing_fields_degrade_to_the_authored_category(self):
        """An unmeasured seed must not be mistaken for a rich one."""
        from pipeline.select.categories import categorise
        self.assertEqual(categorise({}), "F0")

    def test_annotate_marks_every_row(self):
        from pipeline.select.categories import annotate
        rows = [self._row(0.9, 5), self._row(0.1, 0)]
        self.assertEqual([r["category"] for r in annotate(rows)], ["F3", "F0"])

    def test_legacy_letters_read_as_the_level_they_aimed_at(self):
        from pipeline.policy import target_level
        self.assertEqual([target_level(c) for c in "ABCD"], ["F3", "F2", "F2", "F2"])
        self.assertEqual([target_level(c) for c in ("F3", "F2", "F1", "F0")],
                         ["F3", "F2", "F1", "F0"])
        self.assertIsNone(target_level("Z"))
        self.assertIsNone(target_level(None))


class CategoryReachesTheDesigner(unittest.TestCase):
    """The category decides what the fixture may honestly be built from.

    It is only useful if the designer is told. D in particular permits
    authoring documents outright, which is legitimate there and nowhere else --
    and even there the scenario is fixed.
    """

    def test_all_four_categories_carry_guidance(self):
        from pipeline.author.designer import CATEGORY_GUIDANCE
        from pipeline.select.categories import CATEGORIES
        self.assertEqual(set(CATEGORY_GUIDANCE), set(CATEGORIES))

    def test_category_d_permits_authoring_but_fixes_the_scenario(self):
        from pipeline.author.designer import CATEGORY_GUIDANCE
        text = CATEGORY_GUIDANCE["F1"]
        self.assertIn("AUTHOR the fixture", text)
        self.assertIn("Invent the CONTENT, never the SITUATION", text)

    def test_category_c_forbids_inventing_a_dispute(self):
        """C has documents and no pushback; a manufactured argument reads as one."""
        from pipeline.author.designer import CATEGORY_GUIDANCE
        self.assertIn("do not invent a dispute", CATEGORY_GUIDANCE["F2"])
        self.assertIn("AUTHOR the whole fixture", CATEGORY_GUIDANCE["F0"])


class SecondGradedStep(unittest.TestCase):
    """Two graded steps over one set of documents.

    Far cheaper than a second environment, and the harder task -- but only when
    step 2 introduces information step 1 could not have had and asks whether the
    earlier decision survives it. A step 2 that repeats step 1's work doubles
    the cost and measures the same thing twice.
    """

    def _good(self):
        return {
            "deliverable_file": "register.json",
            "steps": [{"name": "01-x"}, {"name": "02-x"}],
            "checks": [{"id": "c1", "kind": "objective", "step": "02-x"}],
            "second_step": {
                "instruction": "The supplier has now confirmed that two of the "
                               "items you classified as settled were reopened "
                               "last week. Record which of your earlier "
                               "conclusions no longer hold, and why.",
                "deliverable_file": "revision.json",
                "new_information": "two items previously recorded as settled "
                                   "were reopened after the register was drawn"},
        }

    def _run(self, spec):
        from pipeline.author.validate import _second_step
        return _second_step(spec)

    def test_a_well_formed_second_step_is_clean(self):
        self.assertEqual(self._run(self._good()), [])

    def test_no_second_step_is_fine(self):
        """Control: most seeds carry one step, and that is not a defect."""
        self.assertEqual(self._run({"deliverable_file": "a.json"}), [])

    def test_reusing_step_ones_deliverable_is_refused(self):
        spec = self._good()
        spec["second_step"]["deliverable_file"] = "register.json"
        self.assertTrue(any("same file as step 1" in p for p in self._run(spec)))

    def test_new_information_must_be_stated(self):
        spec = self._good()
        spec["second_step"]["new_information"] = "more"
        self.assertTrue(any("could not have known" in p for p in self._run(spec)))

    def test_an_ungraded_second_step_is_refused(self):
        """A graded step with no checks is not graded."""
        spec = self._good()
        spec["checks"] = [{"id": "c1", "kind": "objective", "step": "01-x"}]
        self.assertTrue(any("no objective check is assigned" in p
                            for p in self._run(spec)))

    def test_step_names_are_ordinal_and_path_safe(self):
        from pipeline.author.designer import _step_name
        self.assertEqual(_step_name("education/exam_prep"), "01-education-exam-pre")
        self.assertEqual(_step_name("education/exam_prep", ordinal=2),
                         "02-education-exam-pre")
        for name in (_step_name("a/b"), _step_name("a/b", 2)):
            self.assertNotIn("/", name, "a separator makes the step invisible "
                                        "to the gates' steps/*/instruction.md glob")


class HardeningLoop(unittest.TestCase):
    """Hardening requires intact versioned evidence, not plausible timestamps."""

    def measured_bundle(self, root):
        import json
        from unittest.mock import patch
        from pipeline.tests.test_production import synthetic_bundle, ProductionEvidence
        from pipeline.calibrate.run import campaign
        bundle = synthetic_bundle(Path(root))
        with patch("pipeline.calibrate.run._rollout_for", return_value=ProductionEvidence.solver):
            report = campaign(bundle, "m", 2, workers=1)
        (bundle / "verification/calibration-m.json").write_text(json.dumps(report))
        return bundle

    def test_refuses_without_a_calibration(self):
        import tempfile
        from pipeline.harden import baseline
        from pipeline.tests.test_production import synthetic_bundle
        with tempfile.TemporaryDirectory() as tmp:
            report = baseline(synthetic_bundle(Path(tmp)))
        self.assertFalse(report["ok"])
        self.assertTrue(any("no calibration on record" in e for e in report["errors"]))

    def test_refuses_a_baseline_containing_voids(self):
        import tempfile, json
        from pipeline.harden import baseline
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.measured_bundle(tmp)
            path = bundle / "verification/calibration-m.json"
            report = json.loads(path.read_text())
            report["rollouts"][0]["zero_class"] = "void"
            path.write_text(json.dumps(report))
            result = baseline(bundle)
        self.assertFalse(result["ok"])
        self.assertTrue(any("void" in e for e in result["errors"]))

    def test_instruction_change_invalidates_baseline_even_with_same_grader(self):
        import tempfile
        from pipeline.harden import baseline
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.measured_bundle(tmp)
            next((bundle / "steps").glob("*/instruction.md")).write_text("Changed task")
            result = baseline(bundle)
        self.assertFalse(result["ok"])
        self.assertTrue(any("stale task version" in e for e in result["errors"]))

    def test_bytecode_does_not_count_as_a_grader_change(self):
        import tempfile
        from pipeline.harden import baseline
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self.measured_bundle(tmp)
            cache = bundle / "tests/_arena_runtime/__pycache__"
            cache.mkdir(exist_ok=True)
            (cache / "irrelevant.pyc").write_bytes(b"compiled")
            result = baseline(bundle)
        self.assertTrue(result["ok"], result["errors"])

    def test_only_easy_objectives_are_offered_for_revision(self):
        import tempfile
        from pipeline.harden import hardenable
        with tempfile.TemporaryDirectory() as tmp:
            result = hardenable(self.measured_bundle(tmp))
        self.assertEqual({c["id"] for c in result["floor"]}, {"open_ids", "open_count", "total_effort"})
        self.assertEqual(result["in_band"], [])

    def test_the_loop_is_never_called_automatically(self):
        # The build may TELL the operator to harden; it may never do it.
        for module in ("pipeline/orchestrate.py", "pipeline/run.py", "pipeline/screen.py"):
            source = Path(module).read_text()
            for call in ("import harden", "from .harden import attempt", "harden.main",
                         "harden.attempt", "harden.propose", "screen_round("):
                self.assertNotIn(call, source, f"{module} reaches hardening via {call}")


class DesignerSeesTheWholeFixture(unittest.TestCase):
    """The designer must be able to read what it is writing checks about.

    Measured across the first batch: the one-shot designer is handed the first
    fourteen lines of each fixture document, which is 3% of the fixture -- 1%
    on three bundles, 2% of kw-a010's 885,761 characters. It then specifies
    targets, weights and difficulty against that sample. That is the most
    likely single cause of the band collapse, and it is how kw-a005 came to
    target a file that does not exist.
    """

    def test_the_batch_designer_is_the_agent_designer(self):
        """One design path: the batch's designer forwards to the agent designer."""
        from unittest.mock import patch
        from types import SimpleNamespace
        from pipeline.author import designer
        with patch("pipeline.author.agent_designer.design", return_value={"ok": 1}) as agent:
            self.assertEqual(designer.design({}, SimpleNamespace(evidence_summary={"n": 1}), Path("b"),
                                             budget="B", feedback=["f"], initial_spec={"s": 1}), {"ok": 1})
        self.assertEqual(agent.call_args.kwargs, {"budget": "B", "feedback": ["f"], "initial_spec": {"s": 1}})

    def test_the_agent_can_read_documents_trace_and_its_own_answers(self):
        """Full visibility means all three, plus seeing what its targets compute."""
        from pipeline.author import agent_designer
        source = Path("pipeline/author/agent_designer.py").read_text()
        for tool in ("list_fixture", "read_fixture", "read_trace",
                     "list_corrections", "run_parser", "evaluate", "check_spec"):
            self.assertIn(f'"name": "{tool}"', source,
                          f"the designer cannot {tool}; it would be specifying "
                          "checks it cannot verify")


class HardeningAcceptance(unittest.TestCase):
    """Validity and usefulness for the target cohort are separate obligations."""

    def _base(self):
        from pipeline.tests.test_measurement import measured
        return measured([10] * 6), measured([5, 5, 5, 5, 10, 1])

    def test_a_clean_informative_revision_is_accepted(self):
        from pipeline.harden import acceptance
        before, after = self._base()
        self.assertTrue(acceptance(before, after, True, True, [])["accept"])

    def test_all_fail_is_admitted_only_when_every_zero_is_the_models(self):
        from pipeline.harden import acceptance
        from pipeline.tests.test_measurement import measured
        before, _ = self._base()
        clean = acceptance(before, measured([0] * 6), True, True, [])
        self.assertTrue(clean["accept"])
        self.assertEqual(clean["disposition"], "hard")
        unproven = acceptance(before, measured([0] * 6), True, True,
                              ["one: c0 has no executed source counterfactual"])
        self.assertFalse(unproven["accept"])
        self.assertEqual(unproven["disposition"], "invalid")

    def test_too_few_valid_episodes_rejects(self):
        from pipeline.harden import acceptance
        before, after = self._base()
        from pipeline.policy import SCREEN_EPISODES_PER_MODEL
        after["by_model"]["one"]["episodes_valid"] = SCREEN_EPISODES_PER_MODEL - 1
        self.assertFalse(acceptance(before, after, True, True, [])["accept"])

    def test_a_broken_gate_chain_rejects(self):
        from pipeline.harden import acceptance
        self.assertFalse(acceptance(*self._base(), False, True, [])["accept"])

    def test_an_unsolvable_reference_rejects(self):
        from pipeline.harden import acceptance
        result = acceptance(*self._base(), True, False, [])
        self.assertFalse(result["accept"])
        self.assertTrue(any("not difficulty" in r for r in result["reasons"]))

    def test_suspect_measurement_rejects(self):
        from pipeline.harden import acceptance
        self.assertFalse(acceptance(*self._base(), True, True, ["3 void attempts"])["accept"])

    def test_a_legitimate_but_ineffective_change_rejects(self):
        from pipeline.harden import acceptance
        before, _ = self._base()
        result = acceptance(before, before, True, True, [])
        self.assertFalse(result["accept"])
        self.assertTrue(result["valid"])

    def test_the_brief_forbids_the_levers_that_do_not_work(self):
        from pipeline.harden import HARDENING_BRIEF
        for text in ("Answer size does not predict difficulty", "`requires` chains",
                     "hidden rules", "PREMISE THAT CHANGES", "GOVERNING CONFLICT",
                     "RESIDUE", "INDEPENDENT PREMISES, EACH ON ITS OWN CHECKS", "write_scenario", "grounded",
                     "resolvable", "read_trace"):
            self.assertIn(text, HARDENING_BRIEF)


class DesignerVisibilityLimits(unittest.TestCase):
    """The designer must see enough to write checks it can stand behind.

    Being the default is not the same as being unrestricted. These caps decide
    how much of the fixture, the trace and the parsed data reach the model, and
    every one of them was previously tight enough to matter: trace messages cut
    at 1400 characters truncate the quote a trap must cite verbatim, and a
    parser sample of 12 rows with fields taken from the first 50 hides a column
    that appears later -- exactly the sort of thing a good check turns on.
    """

    def _source(self):
        return Path("pipeline/author/agent_designer.py").read_text()

    def test_the_step_budget_survives_a_large_fixture(self):
        """kw-a010 is 885,761 characters across 25 files."""
        from pipeline.author.agent_designer import MAX_STEPS
        self.assertGreaterEqual(MAX_STEPS, 120,
                                "a designer that runs out of budget mid-read "
                                "emits against a partial picture")

    def test_a_trace_message_is_not_cut_mid_correction(self):
        from pipeline.author.agent_designer import TRACE_MESSAGE_CHARS
        self.assertGreaterEqual(TRACE_MESSAGE_CHARS, 4000)

    def test_parser_fields_come_from_every_row(self):
        """A column appearing only in row 200 is a check worth writing."""
        self.assertIn("for r in rows for k in r", self._source())
        self.assertNotIn("for r in rows[:50] for k in r", self._source())

    def test_the_fixture_listing_is_uncapped(self):
        """Every document must be visible, or the designer cannot choose."""
        source = self._source()
        listing = source[source.index("def list_fixture"):source.index("def read_fixture")]
        self.assertIn("sorted(fixture.rglob", listing)
        self.assertNotIn("[:", listing.split("return")[0].split("rglob")[1][:200],
                         "the document list must not be truncated")

    def test_the_designer_still_cannot_read_the_answer(self):
        """Visibility is widened; containment is not. Both must hold.

        `authoring/extraction/after/` is the repair the user accepted -- the
        answer to the dispute the task is built on. A designer that reads it
        writes a task it was told the answer to, and no downstream gate can
        tell, because the grader agrees with itself either way. So "maximum
        visibility" stops exactly here, and this is not a limitation to relax.
        """
        import tempfile
        from pipeline.author.agent_designer import _Sandbox
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp).resolve()
            fixture = bundle / "environment" / "files"
            fixture.mkdir(parents=True)
            (fixture / "brief.md").write_text("visible")
            answer = bundle / "authoring" / "extraction" / "after"
            answer.mkdir(parents=True)
            (answer / "resolved.md").write_text("the accepted repair")
            box = _Sandbox(fixture)

            self.assertEqual(box.resolve("brief.md").read_text(), "visible")
            # Traversal out of the fixture is refused outright.
            for escape in ("../../authoring/extraction/after/resolved.md",
                           "../../solution/submission"):
                with self.subTest(path=escape), self.assertRaises(PermissionError):
                    box.resolve(escape)
            # An absolute path is confined into the fixture rather than
            # followed, so it resolves inside the root and is simply missing.
            # Either way the read never escapes; assert that, not the exception.
            with self.assertRaises((PermissionError, FileNotFoundError)):
                box.resolve("/etc/passwd")
            for probe in ("../../solution", "/etc/passwd", "..%2F..%2Fsolution"):
                try:
                    resolved = box.resolve(probe)
                except (PermissionError, FileNotFoundError):
                    continue
                self.assertTrue(
                    resolved == box.root or box.root in resolved.parents,
                    f"{probe!r} resolved outside the fixture: {resolved}")

    def test_a_symlink_out_of_the_fixture_is_refused(self):
        """Resolution happens before the check, so a link cannot smuggle a read."""
        import tempfile
        from pipeline.author.agent_designer import _Sandbox
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp).resolve()
            fixture = bundle / "environment" / "files"
            fixture.mkdir(parents=True)
            outside = bundle / "solution"
            outside.mkdir()
            (outside / "answer.md").write_text("the reference answer")
            (fixture / "innocent.md").symlink_to(outside / "answer.md")
            with self.assertRaises(PermissionError):
                _Sandbox(fixture).resolve("innocent.md")


class EveryEnforcedRuleIsStated(unittest.TestCase):
    """A rule the validator enforces must be one the designer was told.

    This is a whole class of defect, not a single bug. kw-a005 burned nine
    repair attempts on a literal target missing its `why` -- the rule was real
    and the message never said what the fix looked like. Then the check floor,
    the gating cap, the single-weight cap and the guardrail-weight rule were
    all added to the validator while the designer's contract said nothing about
    any of them. Each one costs a repair round at best and kills the design at
    worst, and the failure looks like a bad model rather than a missing brief.
    """

    def _contract(self):
        import json
        # What production sends: the agent designer's prompt plus the spec
        # tool. The one-shot designer's SYSTEM was deleted with that route.
        from pipeline.author.designer import SPEC_TOOL
        from pipeline.author.agent_designer import SYSTEM
        from pipeline.author.quality import QUALITY_PROMPT
        return (json.dumps(SPEC_TOOL) + SYSTEM + QUALITY_PROMPT).lower()

    def test_the_rubric_shape_rules_are_stated(self):
        from pipeline.author.validate import (MAX_GATED_WEIGHT_SHARE,
                                              MAX_SINGLE_WEIGHT_SHARE,
                                              MIN_OBJECTIVES)
        contract = self._contract()
        for needle, rule in [
            (f"at least {MIN_OBJECTIVES} objective", "the objective-count floor"),
            (f"{MAX_SINGLE_WEIGHT_SHARE:.0%}", "the single-weight cap"),
            (f"{MAX_GATED_WEIGHT_SHARE:.0%}", "the gating cap"),
            ("weight_basis", "the weight justification"),
            ("weight exactly 0", "the guardrail-weight rule"),
            # v2 (user, 2026-10-02): the trap count is an advisory target.
            (f"for {__import__('pipeline.config', fromlist=['MIN_TRAPS']).MIN_TRAPS} or more", "the trap target"),
        ]:
            with self.subTest(rule=rule):
                self.assertIn(needle.lower(), contract,
                              f"{rule} is enforced but never stated; the "
                              "designer cannot satisfy a rule it has not read")

    def test_the_thresholds_in_the_contract_match_the_code(self):
        """A stated rule that drifts from the enforced one is worse than silence."""
        from pipeline.author.validate import (MAX_GATED_WEIGHT_SHARE,
                                              MAX_SINGLE_WEIGHT_SHARE,
                                              MIN_OBJECTIVES)
        contract = self._contract()
        # v2: both shares are advisories, still stated with the code's numbers.
        self.assertIn(f"above {MAX_SINGLE_WEIGHT_SHARE:.0%}", contract)
        self.assertIn(f"under {MAX_GATED_WEIGHT_SHARE:.0%}", contract)
        self.assertIn(f"at least {MIN_OBJECTIVES} objective", contract)

    def test_the_repairable_errors_show_the_fix_not_just_the_rule(self):
        """An objection the designer cannot act on costs a whole attempt."""
        import tempfile
        from pipeline.author.checks import CheckError, Workspace, evaluate
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "src").mkdir()
            ws = Workspace(source=root / "src", submitted=root)
            with self.assertRaises(CheckError) as caught:
                evaluate({"op": "literal", "value": "(?i)x"}, ws, "source")
        self.assertIn("replace it with:", str(caught.exception))


class MeasurementValidityIsReadByTheScreen(unittest.TestCase):
    """The in-build validity probe went with the in-build difficulty loop.

    Its job -- no void rollouts, no check nothing can reach, no near-miss
    betraying an unstated convention -- is now the batch screen's: an unclean
    screen is `not-assessable`, never read as difficulty.
    """

    def test_the_screen_reads_attribution_proof_and_trajectories(self):
        import inspect
        from pipeline import screen
        source = inspect.getsource(screen.summarize)
        self.assertIn("attribution.attribute(bundle, measured, episodes)", source)
        self.assertIn("attribution.all_fail_problems(bundle, measured)", source)
        self.assertIn("attribution.trajectory_hacks(bundle, measured)", source)

    def test_an_unclean_screen_is_not_assessable(self):
        from pipeline import screen
        verdict = screen.outlook(Path("/nonexistent"), {
            "measurement_complete": False, "per_model": {}, "models": [],
            "shippable_problems": ["m: 2 void episodes leave 3 valid (need 5)"]})
        self.assertEqual(verdict["verdict"], "not-assessable")
        self.assertIn("m: 2 void episodes leave 3 valid (need 5)", verdict["reasons"])


class CategoryIsRecordedOnTheBundle(unittest.TestCase):
    """A finished bundle must say which category it was built as.

    Selection annotates the seed, the brief tells the designer, and nothing
    wrote it down -- so a shipped task could not be traced to the bucket it was
    chosen for, which is the entire basis of a category-wise batch.
    """

    def test_the_ledger_carries_the_category_and_its_inputs(self):
        source = Path("pipeline/orchestrate.py").read_text()
        self.assertIn('ledger["category"] = row.get("category")', source)
        self.assertIn('"replay_readiness": row.get("replay_readiness")', source,
                      "record what decided the category, not just the label")
        self.assertIn('"corrections": row.get("corrections")', source)


class ShippedGraderIsStepAware(unittest.TestCase):
    """Each graded step must score its own checks, not the whole task.

    `task.toml` sets ARENA_STEP per step and `rubric.json` maps steps to check
    ids, and the shipped `criteria.py` read neither. In a two-step environment
    that grades every check on every step: step 1 penalised for work it has not
    been asked to do, step 2 re-credited for step 1's. Single-step bundles were
    unaffected, which is why it survived a batch of them.

    The test has to DISCRIMINATE. Grading the reference submission proves
    nothing -- it scores 1.0 on every check, so routing and no routing give the
    same answer. So a step-2 deliverable is deliberately withheld: step 1 must
    still score 1.0, and step 2 must not.
    """

    def _grade(self, bundle, step=None):
        import os
        import subprocess
        import sys
        env = {**os.environ,
               "ARENA_SOURCE": str((bundle / "environment/files").resolve()),
               "ARENA_SUBMITTED": str((bundle / "submitted").resolve()),
               "ARENA_REWARD": str((bundle / "reward.json").resolve()),
               "PYTHONPATH": "", "PYTHONDONTWRITEBYTECODE": "1"}
        if step:
            env["ARENA_STEP"] = step
        else:
            env.pop("ARENA_STEP", None)
        proc = subprocess.run([sys.executable, str(bundle / "tests/criteria.py")],
                              capture_output=True, text=True, timeout=300,
                              cwd=str(bundle), env=env)
        if proc.returncode != 0:
            self.fail(f"grader failed: {proc.stderr[-400:]}")
        return json.loads((bundle / "reward.json").read_text())["reward"]

    def test_a_complete_submission_scores_one_on_every_step(self):
        """Control. The split itself must not break grading.

        Built synthetically rather than from `envs/`: which bundles exist
        differs between this checkout and the Coder workspace, and a test whose
        result depends on that is testing the repository, not the runner.
        """
        import json as _json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._synthetic(tmp)
            (bundle / "submitted" / "second.json").write_text(
                _json.dumps({"value": "B"}))
            self.assertEqual(self._grade(bundle, "01-first"), 1.0)
            self.assertEqual(self._grade(bundle, "02-second"), 1.0)
            with self.assertRaisesRegex(AssertionError, "ARENA_STEP"):
                self._grade(bundle)

    def _synthetic(self, tmp):
        """A minimal two-step bundle whose steps write DIFFERENT files.

        Built by hand rather than copied: the shipped bundles all have a single
        deliverable, so removing step 2's answer removes step 1's too and the
        test cannot tell routing from no routing.
        """
        import shutil
        from pipeline.author.build import CRITERIA_RUNNER
        bundle = Path(tmp) / "a-001-synthetic"
        (bundle / "tests" / "_arena_runtime").mkdir(parents=True)
        (bundle / "environment" / "files").mkdir(parents=True)
        (bundle / "submitted").mkdir(parents=True)

        repo = Path(__file__).resolve().parents[2]
        runtime = bundle / "tests" / "_arena_runtime"
        (runtime / "__init__.py").write_text("")
        shutil.copy(repo / "pipeline/author/checks.py", runtime / "checks_runtime.py")
        shutil.copy(repo / "pipeline/author/oracle.py", runtime / "oracle.py")
        shutil.copy(repo / "pipeline/author/contracts.py", runtime / "contracts.py")
        shutil.copy(repo / "pipeline/author/path_witness.py", runtime / "path_witness.py")
        shutil.copy(repo / "pipeline/author/subset_witness.py", runtime / "subset_witness.py")
        (bundle / "tests" / "criteria.py").write_text(CRITERIA_RUNNER)

        why = "fixed sentinel; this routing test does not exercise derivation"
        checks = [
            {"id": "one", "kind": "objective", "weight": 50, "band": "core",
             "dimension": "core", "basis": "step one", "assertion": "equals",
             "actual": {"op": "field", "file": "first.json", "path": "value"},
             "target": {"op": "literal", "value": "A", "why": why}},
            {"id": "two", "kind": "objective", "weight": 50, "band": "core",
             "dimension": "core", "basis": "step two", "assertion": "equals",
             "actual": {"op": "field", "file": "second.json", "path": "value"},
             "target": {"op": "literal", "value": "B", "why": why}},
        ]
        (bundle / "tests" / "checks.json").write_text(json.dumps({"checks": checks}))
        (bundle / "tests" / "rubric.json").write_text(json.dumps(
            {"01-first": ["one"], "02-second": ["two"]}))
        (bundle / "submitted" / "first.json").write_text(json.dumps({"value": "A"}))
        return bundle

    def test_a_step_is_not_penalised_for_another_steps_work(self):
        """The discriminating case: step 2's deliverable is never written.

        Without routing, step 1 grades the missing second.json and scores 0.5.
        With routing it scores 1.0 on its own check while step 2 scores 0.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._synthetic(tmp)
            first = self._grade(bundle, "01-first")
            second = self._grade(bundle, "02-second")
            with self.assertRaisesRegex(AssertionError, "ARENA_STEP"):
                self._grade(bundle)
        self.assertEqual(first, 1.0,
                         "step 1 was penalised for step 2's missing work -- "
                         "the grader is not honouring ARENA_STEP")
        self.assertEqual(second, 0.0,
                         "step 2 scored despite its deliverable never being written")

    def test_an_unknown_step_is_an_execution_error(self):
        """Typos cannot silently change which work the grader measures."""
        import json as _json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._synthetic(tmp)
            (bundle / "submitted" / "second.json").write_text(
                _json.dumps({"value": "B"}))
            with self.assertRaisesRegex(AssertionError, "ARENA_STEP"):
                self._grade(bundle, "99-not-a-step")


class SpecIsRetained(unittest.TestCase):
    """The design that produced a bundle must survive beside it.

    Nothing kept it. A shipped task could not be traced back to its own design,
    and `arena harden` had nothing to revise -- it would have had to
    reconstruct a spec from checks.json and guess whatever the spec carried
    that the bundle does not: the traps' reasoning, the second step, the
    category, every weight_basis.
    """

    def test_build_writes_the_spec(self):
        source = Path("pipeline/author/build.py").read_text()
        self.assertIn('"authoring" / "spec.json"', source)

    def test_it_is_written_before_the_derived_artefacts(self):
        """A build that fails later should still leave the intent on disk."""
        source = Path("pipeline/author/build.py").read_text()
        self.assertLess(source.index('"spec.json"'),
                        source.index('"tests" / "checks.json"'))


class HardeningApplyIsSafe(unittest.TestCase):
    """--apply must never damage the original and never accept a weaker task."""

    def test_it_refuses_a_bundle_with_no_retained_spec(self):
        """Bundles built before the spec was kept cannot be hardened honestly."""
        import tempfile
        from pipeline.harden import propose
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "a-001-x"
            (bundle / "authoring").mkdir(parents=True)
            with self.assertRaises(FileNotFoundError) as caught:
                propose(bundle, [])
        self.assertIn("no design to revise", str(caught.exception))

    def test_the_diff_names_every_kind_of_change(self):
        from pipeline.harden import diff_checks
        result = diff_checks(
            {"checks": [{"id": "keep", "weight": 10},
                        {"id": "edit", "weight": 10},
                        {"id": "drop", "weight": 10}]},
            {"checks": [{"id": "keep", "weight": 10},
                        {"id": "edit", "weight": 25},
                        {"id": "new", "weight": 10}]})
        self.assertEqual(result["unchanged"], ["keep"])
        self.assertEqual(result["changed"], ["edit"])
        self.assertEqual(result["removed"], ["drop"])
        self.assertEqual(result["added"], ["new"])

    def test_deleting_a_check_is_refused_by_the_apply_path(self):
        """The cheapest way to raise a pass rate is to drop the check."""
        from pipeline.harden import revision_problems
        before = {"checks": [{"id": "easy"}, {"id": "core"}]}
        after = {"checks": [{"id": "easy"}]}
        problems = revision_problems(before, after, [{"id": "easy"}, {"id": "core"}])
        self.assertTrue(any("removing work" in p for p in problems))

    def test_proposal_preserves_source_while_allowing_instruction_repair(self):
        import json, tempfile
        from unittest.mock import patch
        from pipeline.harden import propose
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "authoring").mkdir()
            old = {"source": {"session_id": "original", "seed_index": 0}, "category": "A",
                   "steps": [{"name": "one", "instruction": "old"}]}
            (bundle / "authoring/spec.json").write_text(json.dumps(old))
            reply = {"source": {"session_id": "invented"}, "category": "D",
                     "steps": [{"name": "one", "instruction": "repaired"}]}
            with patch("pipeline.repair.design_inputs", return_value=(old, {}, {"category": "A"})), \
                 patch("pipeline.author.extract.extract", return_value=object()), \
                 patch("pipeline.author.agent_designer.design", return_value=reply) as design:
                result = propose(bundle, [{"id": "c1", "weight": 10, "rate": 1.0}])
            self.assertEqual(result["source"], old["source"])
            self.assertEqual(result["category"], "A")
            self.assertEqual(result["steps"][0]["instruction"], "repaired")
            # The agent designer revises the retained spec inside the copy, with the brief.
            initial = design.call_args.kwargs["initial_spec"]
            self.assertEqual({field: initial[field] for field in old}, old)
            self.assertEqual(initial["quality"]["capability_plan"]["version"], 2)
            self.assertNotIn("quality", old)
            self.assertIn("HARDEN THIS TASK", design.call_args.kwargs["feedback"][0])
            self.assertIn("c1", design.call_args.kwargs["feedback"][0])

    def _apply(self, outcomes):
        import tempfile
        from unittest.mock import patch
        from pipeline import harden
        report = {"ok": True, "errors": [], "models": ["a", "b"], "by_model": {},
                  "floor": [{"id": "c1", "step": "s", "weight": 10, "rate": 1.0}],
                  "in_band": [], "already_hard": [], "unreachable": [], "free_weight": 10}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "a-001-x"
            bundle.mkdir()
            (bundle / "task.toml").write_text("")
            with patch("pipeline.harden.hardenable", return_value=report), \
                 patch("pipeline.harden.attempt", side_effect=outcomes) as attempt:
                code = harden.main([str(bundle), "--apply", "--no-screen"])
            original = sorted(p.name for p in bundle.iterdir())
        return code, attempt, original

    def test_a_repeated_finding_is_terminal(self):
        code, attempt, _ = self._apply([["gate chain is red"], ["gate chain is red"]])
        self.assertEqual(code, 1)
        self.assertEqual(attempt.call_count, 2)
        # The second pass is told what the first one found.
        self.assertEqual(attempt.call_args_list[1].args[3], ["gate chain is red"])

    def test_findings_must_shrink(self):
        code, attempt, _ = self._apply([["x"], ["y", "z"]])
        self.assertEqual((code, attempt.call_count), (1, 2))

    def test_a_clean_revision_is_built_beside_the_original(self):
        code, attempt, original = self._apply([["a", "b"], ["c"], []])
        self.assertEqual((code, attempt.call_count), (0, 3))
        self.assertEqual(original, ["hardened", "task.toml"])

    def test_the_original_bundle_is_never_written_to(self):
        source = Path("pipeline/harden.py").read_text()
        # Revisions are copies under <original>/hardened/, and so is the ledger.
        self.assertIn("shutil.copytree(source, target", source)
        self.assertIn('LEDGER = "hardened/hardening.json"', source)
        self.assertIn("The original is untouched", source)

    def test_it_does_not_self_accept(self):
        """A hardened task is a candidate until it has been calibrated."""
        source = Path("pipeline/harden.py").read_text()
        self.assertIn("NOT yet accepted", source)


class HardeningAttemptBudget(unittest.TestCase):
    """User, 2026-09-25: hardening must not become a redesign doom loop.

    At most `policy.MAX_HARDENING_ATTEMPTS` (3) designer calls per task lineage,
    across invocations, never reset. Attempt 1 is the full, extremely-hard
    redesign; later attempts repair or tighten. Measured outcomes end it early.
    """

    REPORT = {"ok": True, "errors": [], "models": ["a", "b"], "by_model": {},
              "floor": [{"id": "c1", "step": "s", "weight": 10, "rate": 1.0}],
              "in_band": [], "already_hard": [], "unreachable": [], "free_weight": 10}

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bundle = Path(self.tmp.name) / "a-001-x"
        self.bundle.mkdir()
        (self.bundle / "task.toml").write_text("")
        # These scripted screens state the target as a flag; the per-step goal
        # (user, 2026-10-02) follows it here and is tested on its own elsewhere.
        from unittest.mock import patch
        from pipeline import policy
        models = policy.resolve_calibration_models()
        patcher = patch("pipeline.harden.steps_too_easy", side_effect=lambda record: {
            model: ([] if record.get("meets_target") else ["01-task"]) for model in models})
        patcher.start()
        self.addCleanup(patcher.stop)
        # ...and so does the training-signal target (2026-10-13), tested on its own.
        signal = patch("pipeline.harden._signal_verdict", side_effect=lambda record: {
            "target_met": bool((record or {}).get("meets_target"))})
        signal.start()
        self.addCleanup(signal.stop)

    def _run(self, outcomes, screens=(), no_screen=False, bundle=None):
        """Drive `harden.main --apply` with scripted attempts and screens."""
        from unittest.mock import patch
        from pipeline import harden
        args = [str(bundle or self.bundle), "--apply"] + (["--no-screen"] if no_screen else [])
        with patch("pipeline.harden.hardenable", return_value=self.REPORT), \
             patch("pipeline.harden.attempt", side_effect=outcomes) as attempt, \
             patch("pipeline.harden.screen_round", side_effect=list(screens)) as screened:
            code = harden.main(args)
        return code, attempt, screened, harden.read_ledger(self.bundle)

    @staticmethod
    def _screen(meets_target=False, progress=True, clean=True):
        return {"record": {"meets_target": meets_target, "shippable": clean,
                           "meets_capability_target": meets_target,
                           "measurement_complete": clean,
                           "shippable_problems": [] if clean else ["m: 3 valid episodes of 5"]},
                "progress": progress,
                "summary": {"meets_target": meets_target, "progress": progress}}

    def test_the_budget_is_three_and_policy_owns_it(self):
        from pipeline import policy
        self.assertEqual(policy.MAX_HARDENING_ATTEMPTS, 3)

    def test_the_first_attempt_hardens_and_later_ones_repair(self):
        code, attempt, _, ledger = self._run([["a", "b", "c"], ["a2", "b2"], ["c3"]], no_screen=True)
        kinds = [(c.kwargs["number"], c.kwargs["kind"]) for c in attempt.call_args_list]
        self.assertEqual(kinds, [(1, "harden"), (2, "repair"), (3, "repair")])
        self.assertEqual((code, ledger["status"]), (1, "exhausted"))

    def test_an_exhausted_lineage_is_refused_without_designing(self):
        self._run([["a", "b", "c"], ["a2", "b2"], ["c3"]], no_screen=True)
        code, attempt, _, _ = self._run([[]], no_screen=True)
        self.assertEqual(code, 1)
        attempt.assert_not_called()

    def test_the_budget_spans_invocations_and_revisions(self):
        # One attempt, valid, left unscreened; the next run on the REVISION
        # spends from the original's budget, not a fresh one.
        code, attempt, _, ledger = self._run([[]], no_screen=True)
        self.assertEqual((code, len(ledger["attempts"])), (0, 1))
        revision = self.bundle / "hardened" / "v2"
        self.assertTrue(revision.is_dir())
        code, attempt, _, ledger = self._run([["x"], ["x"]], bundle=revision, no_screen=True)
        self.assertEqual(attempt.call_args_list[0].kwargs["number"], 2)
        self.assertEqual(len(ledger["attempts"]), 3)
        self.assertEqual(ledger["status"], "stopped")        # the finding repeated
        # Later revisions are siblings under the original, never nested.
        self.assertEqual(sorted(p.name for p in (self.bundle / "hardened").glob("v*")), ["v2", "v3"])

    def test_a_screened_revision_that_is_still_easy_is_tightened(self):
        code, attempt, screened, ledger = self._run(
            [[], [], []], screens=[self._screen(), self._screen(), self._screen()])
        self.assertEqual([c.kwargs["kind"] for c in attempt.call_args_list], ["harden"] * 3)
        self.assertEqual(screened.call_count, 3, "every valid revision is screened")
        self.assertEqual((code, ledger["status"]), (1, "exhausted"))
        # Each tightening revises the previous measured revision.
        froms = [a["from"] for a in ledger["attempts"]]
        self.assertEqual(froms, [".", "hardened/v2", "hardened/v3"])

    def test_meeting_the_target_ends_hardening_early(self):
        code, attempt, _, ledger = self._run([[]], screens=[self._screen(meets_target=True)])
        self.assertEqual((code, attempt.call_count, ledger["status"]), (0, 1, "target-met"))

    def test_a_revision_that_moved_nothing_ends_hardening(self):
        code, attempt, _, ledger = self._run([[], []], screens=[self._screen(progress=False)])
        self.assertEqual((code, attempt.call_count, ledger["status"]), (1, 1, "no-progress"))
        code, attempt, _, _ = self._run([[]])
        attempt.assert_not_called()

    def test_a_designer_that_returned_nothing_spends_nothing(self):
        from pipeline.harden import DesignerUnavailable
        code, attempt, _, ledger = self._run([DesignerUnavailable("transport interrupted")])
        self.assertEqual((code, len(ledger["attempts"]), ledger["status"]), (2, 0, "open"))
        self.assertEqual(len(ledger["interruptions"]), 1)
        self.assertEqual(list((self.bundle / "hardened").glob("v*")), [],
                         "an untouched copy is removed, so numbering stays honest")

    def test_a_failed_screen_keeps_the_valid_revision_and_spends_nothing_more(self):
        code, attempt, _, ledger = self._run([[]], screens=[RuntimeError("pool unavailable")])
        self.assertEqual((code, len(ledger["attempts"]), ledger["status"]), (2, 1, "open"))
        self.assertTrue((self.bundle / "hardened" / "v2").is_dir())
        self.assertIn("screen:", ledger["interruptions"][0]["error"])

    def test_an_unclean_screen_decides_nothing_and_keeps_the_lineage_open(self):
        # Review: 3 of 5 valid episodes produced a permanent "target-met".
        code, attempt, _, ledger = self._run([[]], screens=[self._screen(meets_target=True, clean=False)])
        self.assertEqual((code, len(ledger["attempts"]), ledger["status"]), (2, 1, "open"))
        self.assertIn("did not measure cleanly", ledger["interruptions"][0]["error"])

    def test_an_interrupted_attempt_is_still_counted(self):
        # Review: Ctrl-C after the designer returned recorded nothing, so the
        # budget could be exceeded. The attempt is recorded the moment it exists.
        from pipeline import harden

        def designed_then_interrupted(*args, on_proposed=None, **kwargs):
            on_proposed()
            raise KeyboardInterrupt()
        from unittest.mock import patch
        with patch("pipeline.harden.hardenable", return_value=self.REPORT), \
             patch("pipeline.harden.attempt", side_effect=designed_then_interrupted):
            with self.assertRaises(KeyboardInterrupt):
                harden.main([str(self.bundle), "--apply", "--no-screen"])
        ledger = harden.read_ledger(self.bundle)
        self.assertEqual([a["outcome"] for a in ledger["attempts"]], ["in-progress"])
        self.assertEqual(harden.attempts_left(ledger), 2)

    def _resume_revision(self, record, outcomes, parent_rate=1.0, child_rate=1.0):
        """Build v2 from one attempt, give it `record` as its screen, resume from it."""
        from unittest.mock import patch
        from pipeline import harden
        self._run([[]], no_screen=True)
        revision = self.bundle / "hardened" / "v2"

        def rates(path):
            return {"a": child_rate if "hardened" in str(path) else parent_rate}
        with patch("pipeline.harden.hardenable", return_value=self.REPORT), \
             patch("pipeline.screen.current", return_value=record), \
             patch("pipeline.harden._pass_at_1", side_effect=rates), \
             patch("pipeline.harden.attempt", side_effect=outcomes) as attempt, \
             patch("pipeline.harden.screen_round", side_effect=[]):
            code = harden.main([str(revision), "--apply", "--no-screen"])
        return code, attempt, harden.read_ledger(self.bundle)

    def test_resuming_from_a_revision_that_met_the_target_designs_nothing(self):
        code, attempt, ledger = self._resume_revision(
            {"measurement_complete": True, "meets_target": True, "meets_capability_target": True,
             "shippable": True}, [[]])
        attempt.assert_not_called()
        self.assertEqual((code, ledger["status"]), (0, "target-met"))

    def test_resuming_from_a_revision_that_made_no_progress_designs_nothing(self):
        code, attempt, ledger = self._resume_revision(
            {"measurement_complete": True, "meets_target": False, "shippable": True}, [[]],
            parent_rate=0.8, child_rate=0.8)
        attempt.assert_not_called()
        self.assertEqual((code, ledger["status"]), (1, "no-progress"))

    def test_resuming_from_an_unclean_revision_screen_is_refused(self):
        code, attempt, ledger = self._resume_revision(
            {"measurement_complete": False, "shippable_problems": ["m: 2 valid of 5"]}, [[]])
        attempt.assert_not_called()
        self.assertEqual((code, ledger["status"]), (1, "open"))

    def test_resuming_from_a_measured_better_revision_tightens_it(self):
        code, attempt, ledger = self._resume_revision(
            {"measurement_complete": True, "meets_target": False, "shippable": True}, [[]],
            parent_rate=1.0, child_rate=0.6)
        self.assertTrue(attempt.call_args.kwargs["tighten"])
        self.assertEqual(attempt.call_args.kwargs["number"], 2)

    def test_a_restart_from_the_original_is_a_full_redesign_not_a_tighten(self):
        # Review: any attempt numbered above 1 got the TIGHTEN header, even when
        # the run restarted from the unmeasured original.
        from pipeline.harden import DesignerUnavailable
        self._run([["a", "b"], DesignerUnavailable("down")], no_screen=True)
        code, attempt, _, ledger = self._run([[]], no_screen=True)
        self.assertEqual(attempt.call_args.kwargs["number"], 2)
        self.assertFalse(attempt.call_args.kwargs["tighten"])

    def test_a_repair_continues_from_the_rejected_draft(self):
        # Review: a revision rejected before its build left the copy's spec.json
        # unhardened, and the REPAIR attempt started from it -- traps lost.
        from unittest.mock import patch
        from pipeline import harden
        from pipeline.artifacts import atomic_json
        spec = {"source": {"session_id": "s", "seed_index": 0}, "checks": [], "traps": []}
        hardened = {**spec, "traps": [{"id": "t_new_premise"}]}
        (self.bundle / "authoring").mkdir()
        (self.bundle / "authoring/spec.json").write_text("{}")
        atomic_json(self.bundle / harden.HARDENING_DRAFT, hardened)
        with patch("pipeline.repair.design_inputs", return_value=(spec, {}, {})), \
             patch("pipeline.harden.faithfulness_budget", return_value={
                 "level": "F2", "traps_total": 0, "traps_trace_derived": 0, "fidelity": 1.0,
                 "authored_traps_left": None, "authored_bytes_left": 0}), \
             patch("pipeline.author.extract.extract", return_value=object()), \
             patch("pipeline.author.agent_designer.design", return_value={}) as design:
            harden.propose(self.bundle, [], ["tests/checks.json c1: x"], kind="repair", number=2)
        self.assertEqual(design.call_args.kwargs["initial_spec"], hardened)

    def test_a_stalled_hardening_design_keeps_its_draft_for_the_repair(self):
        # Re-review: a stall threw the new traps away -- the next REPAIR
        # continued from the pre-revision spec.
        from unittest.mock import patch
        from pipeline import harden
        from pipeline.artifacts import atomic_json
        from pipeline.author.outcomes import AuthoringStalled
        target = self.bundle / "hardened" / "v2"
        session = "verification/design-sessions/abc"
        atomic_json(target / session / "draft.json", {"traps": [{"id": "t_unfinished_premise"}]})
        stall = AuthoringStalled({"reason": "budget spent", "session": session})
        with patch("pipeline.repair.design_inputs", return_value=({}, {}, {})), \
             patch("pipeline.harden.propose", side_effect=stall):
            with self.assertRaises(AuthoringStalled):
                harden.attempt(self.bundle, target, [], [])
        saved = json.loads((target / harden.HARDENING_DRAFT).read_text())
        self.assertEqual(saved["traps"][0]["id"], "t_unfinished_premise")
        # A stall with no readable draft leaves nothing behind, and still raises.
        other = self.bundle / "hardened" / "v3"
        with patch("pipeline.repair.design_inputs", return_value=({}, {}, {})), \
             patch("pipeline.harden.propose", side_effect=AuthoringStalled({"reason": "x", "session": session})):
            with self.assertRaises(AuthoringStalled):
                harden.attempt(self.bundle, other, [], [])
        self.assertFalse((other / harden.HARDENING_DRAFT).exists())

    def test_progress_is_unknown_when_nothing_is_measured_on_both_sides(self):
        from pipeline.harden import _made_progress
        self.assertIsNone(_made_progress({}, {"a": 0.6}))
        self.assertIsNone(_made_progress({"a": None}, {"a": 0.6, "b": 0.4}))
        self.assertIs(_made_progress({"a": 0.8}, {"a": 0.8}), False)
        self.assertIs(_made_progress({"a": 0.8, "b": 0.6}, {"a": 0.8, "b": 0.4}), True)
        # Re-review: the only comparable model was already at 0 and could not
        # fall, and the other was never compared -- that proves nothing.
        self.assertIsNone(_made_progress({"a": 0.0, "b": None}, {"a": 0.0, "b": 0.2}))
        self.assertIsNone(_made_progress({"a": 0.0, "b": 0.0}, {"a": 0.0, "b": 0.0}))
        self.assertIs(_made_progress({"a": 0.0, "b": 0.8}, {"a": 0.0, "b": 0.8}), False)
        self.assertIs(_made_progress({"a": 0.8, "b": None}, {"a": 0.6, "b": 0.2}), True)

    def test_an_unmeasured_parent_never_ends_the_lineage_as_no_progress(self):
        # Re-review: a parent with no measurement read as "no progress", and
        # that status is terminal.
        code, attempt, ledger = self._resume_revision(
            {"measurement_complete": True, "meets_target": False, "shippable": True}, [[]],
            parent_rate=None, child_rate=0.6)
        self.assertEqual(ledger["status"], "open")
        self.assertTrue(attempt.call_args.kwargs["tighten"], "the revision is tightened, not ended")
        self.assertIsNone(ledger["screens"][0]["progress"])

    def test_an_uncomparable_screen_inside_the_loop_keeps_the_lineage_open(self):
        code, attempt, _, ledger = self._run(
            [[], []], screens=[self._screen(progress=None), self._screen(meets_target=True)])
        self.assertEqual((code, attempt.call_count, ledger["status"]), (0, 2, "target-met"))

    def test_the_screen_round_judges_progress_by_the_same_rule(self):
        import inspect
        from pipeline import harden
        self.assertIn("_made_progress(", inspect.getsource(harden.screen_round))
        self.assertIn('outcome["progress"] is False', inspect.getsource(harden.run_lineage))

    def _harden_root_again(self, record, parent_rate=1.0, child_rate=0.6):
        from unittest.mock import patch
        from pipeline import harden

        def rates(path):
            return {"a": child_rate if "hardened" in str(path) else parent_rate}
        with patch("pipeline.harden.hardenable", return_value=self.REPORT) as measured, \
             patch("pipeline.screen.current", return_value=record), \
             patch("pipeline.harden._pass_at_1", side_effect=rates), \
             patch("pipeline.harden.attempt", side_effect=[[]]) as attempt, \
             patch("pipeline.harden.screen_round", side_effect=[]):
            code = harden.main([str(self.bundle), "--apply", "--no-screen"])
        return code, attempt, measured, harden.read_ledger(self.bundle)

    def test_hardening_the_original_again_continues_from_its_measured_revision(self):
        # Re-review: `arena harden <original> --apply` after a measured revision
        # restarted the full redesign from the original, discarding the progress.
        self._run([[]], no_screen=True)
        code, attempt, measured, ledger = self._harden_root_again(
            {"measurement_complete": True, "meets_target": False, "shippable": True})
        self.assertEqual(ledger["attempts"][-1]["from"], "hardened/v2")
        self.assertTrue(attempt.call_args.kwargs["tighten"])
        self.assertEqual(attempt.call_args.args[0], (self.bundle / "hardened" / "v2").resolve())
        self.assertIn((self.bundle / "hardened" / "v2").resolve(),
                      [Path(c.args[0]).resolve() for c in measured.call_args_list],
                      "the free checks are read from the revision's own screen")

    def test_hardening_the_original_again_refuses_while_its_revision_is_unmeasured(self):
        self._run([[]], no_screen=True)
        code, attempt, _, ledger = self._harden_root_again(None)
        attempt.assert_not_called()
        self.assertEqual((code, len(ledger["attempts"]), ledger["status"]), (1, 1, "open"))

    def test_hardening_the_original_again_honours_a_met_target(self):
        self._run([[]], no_screen=True)
        code, attempt, _, ledger = self._harden_root_again(
            {"measurement_complete": True, "meets_target": True, "meets_capability_target": True,
             "shippable": True})
        attempt.assert_not_called()
        self.assertEqual((code, ledger["status"]), (0, "target-met"))

    def test_a_deleted_recorded_revision_never_lends_its_name(self):
        # Re-review: v3 was recorded valid, its directory deleted, and the next
        # copy was named v3 again -- inheriting the old row's "valid" status.
        import shutil
        from pipeline import harden
        (self.bundle / "hardened").mkdir()
        harden._save(self.bundle, {**harden.read_ledger(self.bundle), "attempts": [
            {"attempt": 1, "revision": "hardened/v2", "outcome": "valid"},
            {"attempt": 2, "revision": "hardened/v3", "outcome": "valid"}]})
        (self.bundle / "hardened" / "v2").mkdir()
        self.assertEqual(harden._next_revision(self.bundle, self.bundle).name, "v4")
        shutil.rmtree(self.bundle / "hardened" / "v2")
        self.assertEqual(harden._next_revision(self.bundle, self.bundle).name, "v5")

    def test_revision_names_stay_unique_after_one_is_removed(self):
        import shutil
        from pipeline.harden import _next_revision
        (self.bundle / "hardened").mkdir()
        first = _next_revision(self.bundle, self.bundle)
        second = _next_revision(self.bundle, self.bundle)
        shutil.rmtree(first)
        third = _next_revision(self.bundle, self.bundle)
        self.assertEqual([first.name, second.name, third.name], ["v2", "v3", "v4"])

    def test_a_rejected_source_is_terminal(self):
        from pipeline.author.outcomes import SeedRejected
        code, _, _, ledger = self._run([SeedRejected({"reason": "no genuine premise"})])
        self.assertEqual((code, ledger["status"]), (1, "source-rejected"))

    def test_the_first_attempt_is_told_to_do_all_the_work(self):
        from unittest.mock import patch
        from pipeline import harden
        spec = {"source": {"session_id": "s", "seed_index": 0}, "checks": []}
        with patch("pipeline.repair.design_inputs", return_value=(spec, {}, {})), \
             patch("pipeline.harden.faithfulness_budget", return_value={
                 "level": "F2", "traps_total": 0, "traps_trace_derived": 0, "fidelity": 1.0,
                 "authored_traps_left": None, "authored_bytes_left": 0}), \
             patch("pipeline.harden._breadth_summary", return_value="") as breadth, \
             patch("pipeline.author.extract.extract", return_value=object()), \
             patch("pipeline.author.agent_designer.design", return_value={}) as design:
            (self.bundle / "authoring").mkdir()
            (self.bundle / "authoring/spec.json").write_text("{}")
            measured = Path(self.tmp.name) / "measured"
            harden.propose(self.bundle, [], measured=measured)
            first = design.call_args.kwargs["feedback"][0]
            harden.propose(self.bundle, [], ["tests/checks.json c1: x"], kind="repair",
                           number=2, left=1, measured=measured)
            repair = design.call_args.kwargs["feedback"][0]
        self.assertIs(design.call_args.kwargs["revision"], True)
        self.assertIn("ATTEMPT 1 OF 3 -- THE ONE THAT MUST MAKE THIS TASK EXTREMELY HARD", first)
        self.assertIn("Hold nothing back", first)
        self.assertIn("HARDEN THIS TASK", first)
        self.assertIn("REPAIR ONLY", repair)
        self.assertNotIn("HARDEN THIS TASK", repair)
        # The per-check table comes from the version that was measured.
        self.assertEqual(breadth.call_args.args[0], measured)


class AuditIsASecondReader(unittest.TestCase):
    """The deep audit must know the same rules the gates enforce.

    It exists to re-derive what the gates assert, so a rule with no audit
    coverage has no independent check -- if the gate is quietly wrong, nothing
    disagrees with it. weight_basis, the retained spec and the category were
    all enforced upstream with no second reader at all.
    """

    def _bundle(self, tmp, *, objs, guardrails=(), spec=True, category="A"):
        bundle = Path(tmp) / "a-001-x"
        for sub in ("tests", "authoring", "verification", "provenance",
                    "environment/files", "steps/01-x"):
            (bundle / sub).mkdir(parents=True, exist_ok=True)
        (bundle / "task.toml").write_text('schema_version = "1.4"\n')
        (bundle / "tests" / "checks.json").write_text(json.dumps(
            {"checks": list(objs) + list(guardrails)}))
        (bundle / "authoring" / "traps.json").write_text(json.dumps({"traps": []}))
        (bundle / "verification" / "probes.json").write_text(json.dumps({"results": {}}))
        (bundle / "provenance" / "ledger.json").write_text(json.dumps(
            {"category": category} if category else {}))
        if spec:
            (bundle / "authoring" / "spec.json").write_text(json.dumps({"checks": []}))
        return bundle

    def _warnings(self, bundle):
        from pipeline.audit import audit
        return " ".join(audit(bundle)["warn"])

    def _failures(self, bundle):
        from pipeline.audit import audit
        return " ".join(audit(bundle)["fail"])

    def _objs(self, n=8, basis="the user corrected this judgement twice in turn 7"):
        return [{"id": f"o{i}", "kind": "objective", "weight": 20 - i,
                 "weight_basis": basis} for i in range(n)]

    def test_a_missing_spec_is_reported(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, objs=self._objs(), spec=False)
            self.assertIn("spec.json", self._warnings(bundle))

    def test_a_missing_category_is_reported(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, objs=self._objs(), category=None)
            self.assertIn("records no category", self._warnings(bundle))

    def test_unjustified_weights_are_reported(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, objs=self._objs(basis="important"))
            self.assertIn("no reasoned basis", self._warnings(bundle))

    def test_a_weighted_guardrail_is_a_failure_not_a_warning(self):
        """Double-counting the score is a defect, not a style note."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(
                tmp, objs=self._objs(),
                guardrails=[{"id": "g1", "kind": "guardrail", "weight": 10}])
            self.assertIn("double-counts", self._failures(bundle))

    def test_a_well_formed_bundle_raises_none_of_these(self):
        """Control: these checks must not fire on a good bundle."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(
                tmp, objs=self._objs(),
                guardrails=[{"id": "g1", "kind": "guardrail", "weight": 0}])
            warnings = self._warnings(bundle)
            for phrase in ("spec.json", "records no category",
                           "no reasoned basis", "two buckets"):
                self.assertNotIn(phrase, warnings)
            self.assertNotIn("double-counts", self._failures(bundle))


class TwoStepGuidanceAndAssignment(unittest.TestCase):
    """A second step must be offered to the designer and assigned correctly.

    Measured on the first bundle built under the new pipeline: the designer
    conceived a two-step task -- it named checks `obj2_*` and described one as
    "the step-two answer proper" -- and emitted no `second_step` and no `step`
    field on any check. The field existed in the schema; nothing told it when a
    task should have two steps. Both step-2 checks were then graded inside step
    one, where the agent has not yet been told the thing they turn on.
    """

    def test_the_designer_is_told_when_to_use_a_second_step(self):
        from pipeline.author.agent_designer import SYSTEM
        self.assertIn("second_step", SYSTEM)
        self.assertIn("second DECISION", SYSTEM,
                      "a second step is a second decision, not more work")

    def test_the_designer_is_warned_that_naming_is_not_assignment(self):
        """`obj2_` is a name. Only the `step` field routes a check."""
        from pipeline.author.agent_designer import SYSTEM
        self.assertIn("only the `step` field does", SYSTEM)

    def test_the_designer_is_told_step_two_starts_without_step_ones_prompt(self):
        """a-034: Codex starts every step in a fresh session."""
        from pipeline.author.agent_designer import SYSTEM
        flat = " ".join(SYSTEM.split())
        self.assertIn("Step 1's deliverable and the fixture carry over; step 1's prompt does not.", flat)

    def test_a_check_assigned_to_an_undeclared_step_is_refused(self):
        from pipeline.author.validate import _second_step
        problems = _second_step({
            "steps": [{"name": "01-x"}, {"name": "02-x"}],
            "checks": [{"id": "typo", "step": "02-typoo"}]})
        self.assertTrue(any("not declared" in p for p in problems))
        self.assertTrue(any("graded in the first step" in p for p in problems),
                        "must say what actually happens, not just that it is wrong")

    def test_correct_assignment_and_unassigned_checks_are_fine(self):
        """Control: an unassigned check legitimately belongs to step one."""
        from pipeline.author.validate import _second_step
        self.assertEqual(_second_step({
            "steps": [{"name": "01-x"}, {"name": "02-x"}],
            "checks": [{"id": "a", "step": "01-x"},
                       {"id": "b", "step": "02-x"},
                       {"id": "c"}]}), [])

    def test_the_guard_runs_even_without_a_declared_second_step(self):
        """A stray `step` on a single-step task is still a routing error."""
        from pipeline.author.validate import _second_step
        problems = _second_step({
            "steps": [{"name": "01-only"}],
            "checks": [{"id": "stray", "step": "02-imagined"}]})
        self.assertTrue(problems)


class StreamingDesignerCall(unittest.TestCase):
    """A long reply must stream, or the socket goes quiet and the build wedges.

    Measured: after the designer began reading whole fixtures, two designs sat
    for 18 minutes at 0% CPU with ESTABLISHED connections and no progress. A
    non-streaming request sends nothing until the entire reply is ready, so a
    16-32k token tool call against a large context can outlast any read
    timeout. Streaming keeps bytes moving and surfaces a stall as a timeout
    rather than an indefinite hang.
    """

    def _events(self, *events):
        events = list(events)
        if not any(e['type'] == 'error' for e in events):
            if not events or events[0]['type'] != 'message_start':
                events.insert(0, {'type':'message_start', 'message':{'content':[]}})
            if not any(e['type'] == 'message_delta' for e in events):
                reason = 'tool_use' if any(e.get('content_block', {}).get('type') == 'tool_use' for e in events) else 'end_turn'
                events.append({'type':'message_delta', 'delta':{'stop_reason':reason}})
            events.append({'type':'message_stop'})
        lines = []
        for event in events:
            lines.append(f"event: {event['type']}".encode())
            lines.append(b"data: " + json.dumps(event).encode())
            lines.append(b"")
        return lines

    def test_a_tool_call_is_reassembled_from_its_deltas(self):
        """Tool input arrives as partial_json fragments and must rejoin exactly."""
        from pipeline.author.designer import _consume_stream
        result = _consume_stream(self._events(
            {"type": "message_start", "message": {"id": "msg_1", "role": "assistant"}},
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "tool_use", "id": "t1", "name": "design"}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "input_json_delta", "partial_json": '{"checks":'}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "input_json_delta", "partial_json": ' [{"id": "a"}]}'}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use"}},
        ))
        self.assertEqual(result["id"], "msg_1")
        self.assertEqual(result["stop_reason"], "tool_use")
        block = result["content"][0]
        self.assertEqual(block["type"], "tool_use")
        self.assertEqual(block["input"], {"checks": [{"id": "a"}]})

    def test_text_deltas_concatenate(self):
        from pipeline.author.designer import _consume_stream
        result = _consume_stream(self._events(
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "text_delta", "text": "hello "}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "text_delta", "text": "world"}},
            {"type": "content_block_stop", "index": 0},
        ))
        self.assertEqual(result["content"][0]["text"], "hello world")

    def test_truncated_tool_input_raises_rather_than_returning_half(self):
        """A silently truncated spec is worse than a failure: it validates oddly."""
        from pipeline.author.designer import _consume_stream
        with self.assertRaises(RuntimeError) as caught:
            _consume_stream(self._events(
                {"type": "content_block_start", "index": 0,
                 "content_block": {"type": "tool_use", "id": "t1", "name": "design"}},
                {"type": "content_block_delta", "index": 0,
                 "delta": {"type": "input_json_delta", "partial_json": '{"checks": ['}},
                {"type": "content_block_stop", "index": 0},
            ))
        self.assertIn("did not parse as JSON", str(caught.exception))

    def test_a_stream_error_event_is_raised(self):
        from pipeline.author.designer import _consume_stream
        with self.assertRaises(ConnectionError) as caught:
            _consume_stream(self._events(
                {"type": "error", "error": {"type": "overloaded_error", "message": "private provider detail"}}))
        self.assertIn("overloaded_error", str(caught.exception))

    def test_multiple_blocks_keep_their_positions(self):
        """Index, not arrival order, decides where a block belongs."""
        from pipeline.author.designer import _consume_stream
        result = _consume_stream(self._events(
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "text_delta", "text": "thinking"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "content_block_start", "index": 1,
             "content_block": {"type": "tool_use", "id": "t1", "name": "design"}},
            {"type": "content_block_delta", "index": 1,
             "delta": {"type": "input_json_delta", "partial_json": '{"ok": true}'}},
            {"type": "content_block_stop", "index": 1},
        ))
        self.assertEqual(len(result["content"]), 2)
        self.assertEqual(result["content"][0]["text"], "thinking")
        self.assertEqual(result["content"][1]["input"], {"ok": True})

    def test_a_trickling_stream_is_abandoned_at_the_deadline(self):
        """The socket timeout is per-read, so a slow trickle resets it forever.

        Measured: a-004 sat in a single call for 70 minutes at 0% CPU with an
        ESTABLISHED connection, AFTER streaming was enabled. Streaming keeps
        bytes moving, which is exactly what defeats a per-read timeout. Only a
        wall-clock ceiling catches it.
        """
        import time
        from pipeline.author.designer import _CallTimeout, _consume_stream

        def trickle():
            for _ in range(1000):
                yield b'data: {"type": "ping"}'
                time.sleep(0.002)

        with self.assertRaises(_CallTimeout):
            _consume_stream(trickle(), deadline=time.monotonic() + 0.05)

    def test_a_prompt_stream_finishes_inside_the_deadline(self):
        """Control: the deadline must not abort a call that is working."""
        import time
        from pipeline.author.designer import _consume_stream
        result = _consume_stream(self._events(
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "tool_use", "id": "t", "name": "design"}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "input_json_delta", "partial_json": '{"ok": true}'}},
            {"type": "content_block_stop", "index": 0},
        ), deadline=time.monotonic() + 30)
        self.assertEqual(result["content"][0]["input"], {"ok": True})

    def test_no_deadline_means_no_ceiling(self):
        """Callers that pass none keep the old behaviour."""
        from pipeline.author.designer import _consume_stream
        result = _consume_stream(self._events(
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "text_delta", "text": "fine"}},
            {"type": "content_block_stop", "index": 0}))
        self.assertEqual(result["content"][0]["text"], "fine")

    def test_the_timeout_is_retryable(self):
        """It must be caught by the retry arm, not escape as a hard failure."""
        from pipeline.author.designer import _CallTimeout
        self.assertTrue(issubclass(_CallTimeout, TimeoutError),
                        "the retry arm catches TimeoutError")

    def test_the_deadline_spans_every_attempt_not_each_one(self):
        """A silent server blocks the read, so an in-loop check never runs.

        The first version of this fix put the deadline inside `for raw in
        resp`, which catches a server that TRICKLES and misses one that goes
        quiet: the iterator blocks and the check is never reached. Measured:
        three designs sat 28 minutes grinding through 300s timeouts x 5 retries
        while a 600s deadline was notionally in force.
        """
        source = Path("pipeline/author/designer.py").read_text()
        call = source[source.index("def _call("):]
        call = call[:call.index("\n\n\n")]
        self.assertIn("deadline = (time.monotonic() + CALL_DEADLINE_S", call,
                      "when a deadline is set at all it is set once, outside "
                      "the retry loop, so retries cannot extend it")
        self.assertIn("if remaining is not None and remaining <= 0:", call,
                      "each attempt must check what is left of it")
        self.assertIn("min(READ_TIMEOUT_S, remaining)", call,
                      "a single read must not be able to outlast a set deadline")

    def test_the_call_deadline_is_unbounded_by_default(self):
        """No turn or time limit on authoring (user, 2026-09-23).

        This replaces `test_the_worst_case_is_bounded`, which asserted one call
        could not exceed ~15 minutes. That bound destroyed a 26-minute build
        holding 31 completed designer responses: the draft was sound, only the
        clock had run out. A call that is slow but *progressing* is not a
        failure.

        What used to be enforced by the deadline, and still is:
          - a silent socket dies on READ_TIMEOUT_S
          - no single retry may sleep longer than MAX_RETRY_SLEEP_S
        Waiting is bounded; working is not.
        """
        from pipeline.author.designer import CALL_DEADLINE_S, READ_TIMEOUT_S
        from pipeline.provider import MAX_RETRY_SLEEP_S
        self.assertIsNone(CALL_DEADLINE_S)
        self.assertGreater(READ_TIMEOUT_S, 0,
                           "a dead socket must still be detected")
        self.assertLessEqual(MAX_RETRY_SLEEP_S, 300,
                             "a retry longer than this is a hang, not a wait")

    def test_an_explicit_deadline_still_bounds_the_worst_case(self):
        """Setting ARENA_CALL_DEADLINE_S reinstates the old behaviour."""
        import importlib, os
        from unittest.mock import patch
        from pipeline.author import designer
        try:
            with patch.dict(os.environ, {"ARENA_CALL_DEADLINE_S": "600"}):
                reloaded = importlib.reload(designer)
                self.assertEqual(reloaded.CALL_DEADLINE_S, 600.0)
                self.assertLess(reloaded.READ_TIMEOUT_S, reloaded.CALL_DEADLINE_S)
        finally:
            # Restore OUTSIDE the env patch, or the module keeps the deadline
            # and every later test in the process sees 600.0 instead of None.
            importlib.reload(designer)
        self.assertIsNone(designer.CALL_DEADLINE_S)

    def test_the_request_actually_sets_stream(self):
        source = Path("pipeline/author/designer.py").read_text()
        self.assertIn('body = {**body, "stream": True}', source)

    def test_thinking_blocks_are_reassembled(self):
        """Thinking is on by default and is replayed into the next turn.

        Dropping its deltas leaves an empty thinking block, and the API rejects
        the FOLLOWING request with "each thinking block must contain thinking"
        -- so the failure surfaces one call after the bug, on a different
        message index, which is a thoroughly misleading place to look.
        """
        from pipeline.author.designer import _consume_stream
        result = _consume_stream(self._events(
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "thinking", "thinking": ""}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "thinking_delta", "thinking": "weighing the "}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "thinking_delta", "thinking": "options"}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "signature_delta", "signature": "abc123"}},
            {"type": "content_block_stop", "index": 0},
        ))
        block = result["content"][0]
        self.assertEqual(block["type"], "thinking")
        self.assertEqual(block["thinking"], "weighing the options",
                         "an empty thinking block is rejected on the next turn")
        self.assertEqual(block["signature"], "abc123")

    def test_a_thinking_block_is_never_left_empty(self):
        """The exact shape the API refuses."""
        from pipeline.author.designer import _consume_stream
        result = _consume_stream(self._events(
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "thinking", "thinking": ""}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "thinking_delta", "thinking": "x"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "content_block_start", "index": 1,
             "content_block": {"type": "tool_use", "id": "t", "name": "design"}},
            {"type": "content_block_delta", "index": 1,
             "delta": {"type": "input_json_delta", "partial_json": "{}"}},
            {"type": "content_block_stop", "index": 1},
        ))
        for block in result["content"]:
            if block.get("type") == "thinking":
                self.assertTrue(block.get("thinking"),
                                "empty thinking block would 400 the next call")

    def test_the_calibration_agent_streams_too(self):
        """Ten campaigns run at once; one wedge there is the expensive case."""
        source = Path("pipeline/calibrate/agent.py").read_text()
        self.assertIn('body = {**body, "stream": True}', source)
        self.assertIn("_consume_stream", source)

    def test_both_callers_share_one_stream_reader(self):
        """Two copies of SSE reassembly is two places to drop a delta type."""
        from pipeline.author.designer import _consume_stream as designer_reader
        from pipeline.calibrate import agent
        import inspect
        source = inspect.getsource(agent._call)
        self.assertIn("from ..author.designer import _consume_stream", source)
        self.assertTrue(callable(designer_reader))


class LivenessProbesMustBeAbleToFail(unittest.TestCase):
    """A check that cannot succeed reports the alarming answer, silently.

    Twice this session a monitoring probe was wrong in the same way. `pgrep -c`
    is not supported on macOS and exits 2, so `$(pgrep -fc X || echo 0)` read
    as "no processes" and declared a running build finished. `find -newermt` is
    not supported by this system's find either, so with stderr suppressed it
    read as "no files written" and declared a healthy build stalled -- which
    led to two builds being killed on evidence that did not exist.

    The lesson is not about these two flags. It is that a liveness probe must
    be verified to produce a TRUE positive before its negative is believed.
    """

    def test_find_mmin_is_the_portable_form(self):
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "fresh.txt").write_text("x")
            proc = subprocess.run(["find", tmp, "-type", "f", "-mmin", "-5"],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("fresh.txt", proc.stdout,
                          "a just-written file must be found, or the probe "
                          "cannot distinguish quiet from broken")

    def test_the_probe_is_verified_in_the_shell_it_runs_in(self):
        """The sharpest version of the lesson, and the one that bit.

        `/usr/bin/find` supports `-newermt`. The shell a monitor runs in
        resolves `find` to `bfs`, which does not -- it errors, and `2>/dev/null`
        swallowed that, so the probe reported "no files written" for a build
        that was writing files. Verified one way, deployed another.

        So a liveness probe is checked THROUGH THE SHELL, with stderr visible,
        against a file known to exist. If it cannot find that, it cannot be
        trusted to report its absence.
        """
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "fresh.txt").write_text("x")
            portable = subprocess.run(
                f"find {tmp} -type f -mmin -5", shell=True,
                capture_output=True, text=True)
            self.assertEqual(portable.returncode, 0, portable.stderr)
            self.assertIn("fresh.txt", portable.stdout,
                          "the probe used by monitors must produce a true "
                          "positive in the shell it actually runs in")

    def test_stderr_is_not_suppressed_on_a_liveness_probe(self):
        """Suppressing stderr turns 'this command is broken' into 'all quiet'."""
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "fresh.txt").write_text("x")
            quiet = subprocess.run(
                f"find {tmp} -bogusflag -type f 2>/dev/null | wc -l",
                shell=True, capture_output=True, text=True)
            self.assertEqual(quiet.stdout.strip(), "0",
                             "a broken probe with stderr hidden reports zero, "
                             "which is indistinguishable from nothing happening")

    def test_pgrep_count_is_done_by_counting_lines(self):
        """`pgrep -c` is unsupported here; `pgrep -f X | wc -l` is portable."""
        import subprocess
        import shutil
        if not shutil.which("pgrep"):
            self.skipTest("pgrep is unavailable in this runtime; no liveness claim made")
        proc = subprocess.run(["pgrep", "-f", "python"],
                              capture_output=True, text=True)
        if "Cannot get process list" in proc.stderr or "Operation not permitted" in proc.stderr:
            self.skipTest("host sandbox does not permit process enumeration; no liveness claim made")
        self.assertEqual(proc.returncode, 0)
        self.assertGreater(len(proc.stdout.splitlines()), 0,
                           "this interpreter is running, so the count is >= 1")


class FixtureLedSeedsSurvive(unittest.TestCase):
    """Two corrections is dispute-led reasoning, applied to all four categories.

    A fixture-led seed builds its checks from the documents -- "reconcile these
    32 files" needs no argument to have happened -- so requiring two
    corrections of it discards the category outright. Measured on this corpus:
    five seeds are gradable, carry a non-executing truth source and a real
    deliverable, and were rejected for that clause alone, among them a
    32-document web-fiction edit and a 16-document academic thesis.
    """

    def _survives(self, *, usable, paths, gradable=True,
                  truth="structural_assertion", kind="document"):
        from pipeline.config import KNOWLEDGE_WORK_TRUTH
        from pipeline.select.classify import FIXTURE_LED_PATHS
        return (bool(gradable)
                and truth in KNOWLEDGE_WORK_TRUTH
                and kind not in ("code", "none")
                and (usable >= 2 or (usable >= 1 and paths >= FIXTURE_LED_PATHS)))

    def test_two_corrections_still_survive_on_a_thin_fixture(self):
        """The dispute-led route is unchanged."""
        self.assertTrue(self._survives(usable=2, paths=1))

    def test_one_correction_with_a_broad_fixture_now_survives(self):
        """The 32-document and 16-document seeds this was losing."""
        self.assertTrue(self._survives(usable=1, paths=32))
        self.assertTrue(self._survives(usable=1, paths=16))

    def test_one_correction_with_a_thin_fixture_still_does_not(self):
        """Control: the rule is relaxed for breadth, not abandoned."""
        self.assertFalse(self._survives(usable=1, paths=2))

    def test_no_correction_never_survives(self):
        """A seed with nothing to check is not a task at any fixture size."""
        self.assertFalse(self._survives(usable=0, paths=99))

    def test_the_coding_scope_rule_is_untouched(self):
        """Breadth must never buy a way past the non-coding constraint."""
        self.assertFalse(self._survives(usable=5, paths=99, kind="code"))
        self.assertFalse(self._survives(usable=5, paths=99,
                                        truth="requires_execution"))
        self.assertFalse(self._survives(usable=5, paths=99, gradable=False))


class CategoryFaithfulnessBands(unittest.TestCase):
    """How much of a fixture may be authored depends on the CATEGORY.

    Tier measures how rich a seed is; category decides how much authoring is
    legitimate, and they are different questions. A category D seed has no
    liftable workspace by definition -- that is what makes it D -- so holding
    it to a tier-1 floor of 95% makes the category unbuildable.

        A  Rich          90-100%
        B  Strong        90-100%
        C  Fixture-led    80-90%
        D  Thin fixture   60-80%
    """

    def test_the_bands_are_as_specified(self):
        from pipeline.select.priority import CATEGORY_FIXTURE_FLOOR
        self.assertEqual(CATEGORY_FIXTURE_FLOOR,
                         {"A": 0.90, "B": 0.90, "C": 0.80, "D": 0.60,
                          "F3": 0.90, "F2": 0.0, "F1": 0.0, "F0": 0.0})

    def test_authoring_room_widens_from_a_to_d(self):
        """The ordering is the point: D may author most, A least."""
        from pipeline.select.priority import CATEGORY_FIXTURE_FLOOR as f
        self.assertGreaterEqual(f["A"], f["C"])
        self.assertGreater(f["C"], f["D"])
        # ...and for the target levels: F3 authors least, F1/F0 most.
        self.assertGreater(f["F3"], f["F2"])
        self.assertEqual(f["F2"], f["F1"])
        self.assertEqual(f["F1"], f["F0"])

    def test_a_thin_fixture_seed_is_not_held_to_a_rich_floor(self):
        """The case that would make category D impossible to build."""
        from pipeline.select.priority import CATEGORY_FIXTURE_FLOOR, TIER_FIXTURE_FLOOR
        authored = 0.65
        self.assertLess(authored, TIER_FIXTURE_FLOOR[1],
                        "would fail on tier alone")
        self.assertGreaterEqual(authored, CATEGORY_FIXTURE_FLOOR["D"],
                                "must pass as a category D bundle")

    def test_the_gate_prefers_category_over_tier(self):
        source = Path("pipeline/gates/bundle.py").read_text()
        self.assertIn("if category in CATEGORY_FIXTURE_FLOOR:", source)
        self.assertIn('basis = f"category {category}"', source)

    def test_an_uncategorised_bundle_still_uses_the_tier_floor(self):
        """Control: everything built before categories existed must still gate."""
        source = Path("pipeline/gates/bundle.py").read_text()
        self.assertIn("TIER_FIXTURE_FLOOR.get(tier, FIXTURE_FLOOR_MIN)", source)


class CategoryAwareAdmission(unittest.TestCase):
    """Each category is admitted on what it actually needs.

    Applying the A/B bar -- corrections AND a liftable fixture -- to all four
    collapsed this corpus from 360 in-scope seeds to 110. 214 of the discarded
    have a fixture and no correction, which is category C's definition.
    """

    def _row(self, *, corrections, paths, byts, share=1.0, turns=5,
             categories=("writing",), kw=True):
        return {"corrections": corrections, "deliv_paths": paths,
                "deliv_bytes": byts, "deliv_share": share, "n_turns": turns,
                "categories": list(categories), "kw_tagged": kw}

    def _admitted(self, row):
        from pipeline.select import score
        return score.kill_filters(row).kept

    def test_dispute_led_seeds_are_still_admitted(self):
        self.assertTrue(self._admitted(self._row(corrections=3, paths=6, byts=50000)))

    def test_a_fixture_with_no_correction_is_admitted_as_c(self):
        self.assertTrue(self._admitted(self._row(corrections=0, paths=32, byts=232261)))

    def test_a_scenario_with_no_fixture_is_admitted_as_d(self):
        self.assertTrue(self._admitted(self._row(corrections=0, paths=1, byts=500)))

    def test_the_non_coding_scope_rule_still_rejects(self):
        """Breadth must never buy a way past the scope constraint."""
        self.assertFalse(self._admitted(
            self._row(corrections=5, paths=20, byts=99999, share=0.1)))
        self.assertFalse(self._admitted(
            self._row(corrections=5, paths=20, byts=99999, categories=(), kw=False)))

    def test_the_categories_can_be_switched_off(self):
        import os
        from pipeline.select import score
        previous = os.environ.get("ARENA_AUTHORED_FIXTURES")
        os.environ["ARENA_AUTHORED_FIXTURES"] = "0"
        try:
            self.assertFalse(score.kill_filters(
                self._row(corrections=0, paths=1, byts=500)).kept)
        finally:
            if previous is None:
                os.environ.pop("ARENA_AUTHORED_FIXTURES", None)
            else:
                os.environ["ARENA_AUTHORED_FIXTURES"] = previous


class BlockerNamesItsEvidence(unittest.TestCase):
    """A finding must cite the number it actually read.

    `trap.beatable` prefers a trap's OWN mutation from `per_trap` and falls
    back to the shared probe named on the trap. It reported the fallback's
    NAME with the dedicated probe's NUMBER: on a-005 it said "probe
    'plausible_wrong' scores 1.0" when plausible_wrong scored 0.98 and the 1.0
    came from the trap's own mutation. The block was correct; the message sent
    the reader to the wrong artefact, which is the same shape as a path defect
    reading as a contract defect.
    """

    def _findings(self, per_trap, shared, trap_probe="plausible_wrong"):
        import tempfile
        from pipeline.gates import difficulty
        from pipeline.gates.base import GateContext
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "verification").mkdir()
            (bundle / "authoring").mkdir()
            (bundle / "verification" / "probes.json").write_text(json.dumps({
                "results": {"golden": {"reward": 1.0},
                            "seed_zero": {"reward": 0.0, "objectives": {}, "guardrails": {}},
                            "untidy_correct": {"reward": 1.0},
                            "plausible_wrong": {"reward": shared,
                                                "mutated": ["out.json:x"]},
                            "answer_lookup": {"reward": 0.0},
                            "forged_state": {"reward": 0.0},
                            "per_trap": per_trap}}))
            (bundle / "authoring" / "traps.json").write_text(json.dumps({
                "traps": [{"id": "t1", "probe": trap_probe, "checks": ["c1"],
                           "type": "recycled_claim", "surface": "claim_audit.json",
                           "beatable_by": "reading the source rather than the summary",
                           "provenance": "trace_derived", "derived_from": "turn 3",
                           "quote": "keep the full prose"}]}))
            ctx = GateContext(task_dir=bundle, repo_root=bundle,  # gates re-run probes; logic tests hand them the report
                             extras={"probe_report": json.loads((bundle / "verification" / "probes.json").read_text())})
            findings, _ = difficulty._trap_beatable(ctx)
        return findings

    def test_a_dedicated_mutation_is_named_as_the_evidence(self):
        findings = self._findings(
            per_trap={"t1": {"reward": 1.0, "mutated": ["audit.json:field_a"]}},
            shared=0.98)
        blockers = [f for f in findings if f.code == "trap-not-discriminating"]
        self.assertTrue(blockers)
        detail = blockers[0].message
        self.assertIn("its own mutation", detail)
        self.assertIn("audit.json:field_a", detail,
                      "must name the field that was changed")
        self.assertNotIn("0.98", detail, "must not quote the unused probe")

    def test_the_shared_probe_is_named_when_it_is_what_was_used(self):
        findings = self._findings(per_trap={}, shared=1.0)
        blockers = [f for f in findings if f.code == "trap-not-discriminating"]
        self.assertTrue(blockers)
        self.assertIn("the shared probe 'plausible_wrong'", blockers[0].message)

    def test_a_discriminating_trap_raises_nothing(self):
        """Control: a trap whose mutation costs score is working."""
        findings = self._findings(
            per_trap={"t1": {"reward": 0.6, "mutated": ["audit.json:field_a"]}},
            shared=0.98)
        self.assertEqual(
            [f for f in findings if f.code == "trap-not-discriminating"], [])


class ThreeRoutesToAGradableSeed(unittest.TestCase):
    """A seed needs one of three routes, and the scope rules bind all three.

        dispute-led    two corrections a script could check
        fixture-led    documents that already support a determinate question
        scenario-led   a determinate question and a fixture we will AUTHOR

    Applying the dispute-led bar to all four categories took this corpus from
    360 admissible seeds to 14 viable. With all three routes it is 91, of which
    78 come from routes that did not exist: 50 fixture-led, 28 scenario-led.
    """

    def _verdict(self, **over):
        v = {"gradable": True, "truth_source": "structural_assertion",
             "deliverable_kind": "document", "fixture_task": None}
        v.update(over)
        return v

    def _row(self, *, paths, rr, corrections):
        return {"deliv_paths": paths, "replay_readiness": rr,
                "corrections": corrections}

    def _route(self, verdict, row, moments):
        from pipeline.select.classify import _has_a_route
        return _has_a_route(verdict, row, [None] * moments)

    def test_dispute_led_needs_no_fixture_task(self):
        self.assertTrue(self._route(self._verdict(),
                                    self._row(paths=1, rr=0.2, corrections=5), 2))

    def test_fixture_led_needs_documents_and_a_question(self):
        rich = self._row(paths=32, rr=0.8, corrections=0)
        self.assertTrue(self._route(self._verdict(fixture_task="reconcile them"), rich, 0))
        self.assertFalse(self._route(self._verdict(fixture_task=None), rich, 0),
                         "documents alone are not a task")

    def test_scenario_led_is_allowed_only_where_the_fixture_is_authored(self):
        """F1/F0 targets have almost no workspace -- that is what makes them so."""
        thin_f0 = self._row(paths=3, rr=0.3, corrections=0)     # -> target F0
        thin_f1 = self._row(paths=3, rr=0.3, corrections=1)     # -> target F1
        for thin in (thin_f0, thin_f1):
            self.assertTrue(self._route(
                self._verdict(fixture_task="which commitments were dropped"), thin, 0))

    def test_a_thin_fixture_that_is_not_category_d_is_refused(self):
        """Control: the D exemption must not become a general one.

        A seed with a middling fixture and no dispute is category C, and C is
        held to the document bar -- it claims to be led by documents it has.
        """
        thin_c = self._row(paths=3, rr=0.60, corrections=0)      # rr >= liftable -> F2
        from pipeline.select.categories import categorise
        self.assertEqual(categorise(thin_c), "F2")
        self.assertFalse(self._route(
            self._verdict(fixture_task="something"), thin_c, 0))

    def test_no_route_survives_without_a_question_or_a_dispute(self):
        self.assertFalse(self._route(self._verdict(),
                                     self._row(paths=99, rr=0.9, corrections=0), 0))
        self.assertFalse(self._route(self._verdict(),
                                     self._row(paths=1, rr=0.1, corrections=0), 1))

    def test_every_route_is_still_bound_by_the_non_coding_scope(self):
        """The routes decide WHERE a task comes from, never whether it is in scope.

        Scope is `gradable` + a non-executing truth source + a deliverable that
        is not code, checked before the route is consulted at all.
        """
        source = Path("pipeline/select/classify.py").read_text()
        rule = source[source.index('"survives": bool('):]
        rule = rule[:rule.index("_has_a_route") + 20]
        self.assertIn("truth_source", rule)
        self.assertIn("KNOWLEDGE_WORK_TRUTH", rule)
        self.assertIn('"code"', rule)


class ExploitationFloorNeedsCorrections(unittest.TestCase):
    """0 of 0 is undefined, not 0%.

    `trace.exploitation` requires a share of a trace's corrections to become
    traps. A fixture-led seed (C) or an authored one (D) has no dispute -- that
    is what makes it that category -- so the ratio has no denominator. It
    reported 0% and blocked: category C bundle
    a-002-engineering-thesis-writing was refused for having used 0% of its 0
    corrections.

    The rule still binds wherever it can. A trace WITH corrections must use
    them; a trace without one is reported as inapplicable, not as failing.
    """

    def _codes(self, usable, exploitation, floor=0.40):
        """Mirror the gate's decision without building a whole bundle."""
        if not usable:
            return {"no-corrections-to-exploit"}
        return {"trace-underused"} if exploitation < floor else set()

    def test_a_trace_with_no_corrections_is_inapplicable_not_failing(self):
        self.assertEqual(self._codes(0, 0.0), {"no-corrections-to-exploit"})

    def test_a_trace_that_wastes_its_corrections_still_blocks(self):
        """The rule must not be weakened where it can actually apply."""
        self.assertEqual(self._codes(5, 0.20), {"trace-underused"})

    def test_a_trace_that_uses_its_corrections_passes(self):
        self.assertEqual(self._codes(5, 0.60), set())

    def test_the_gate_reports_inapplicable_rather_than_passing_silently(self):
        """'Could not check' must be visible; it is not the same as 'fine'."""
        source = Path("pipeline/gates/difficulty.py").read_text()
        self.assertIn('"no-corrections-to-exploit"', source)
        self.assertIn("Severity.WARN", source.split('"no-corrections-to-exploit"')[0][-200:])
        self.assertIn("trap.faithful", source,
                      "must say which checks DO still decide the traps")


class GraderMustNotChangeMidCampaign(unittest.TestCase):
    """A calibration measures the grader it started with.

    The repair loop redesigns a blocked bundle. If that lands while a
    calibration is running, the scores describe a task no longer on disk.
    Measured: a-002-engineering-thesis-writing was calibrated at 18:57 over 13
    checks and rebuilt at 18:59 with 11 different ones. Its 0.00 was reported
    as a verified hard task -- the numbers look completely ordinary, which is
    why nothing short of a fingerprint catches it.
    """

    def _fingerprint(self, tmp, checks_text):
        from pipeline.calibrate.run import _grader_fingerprint
        bundle = Path(tmp)
        (bundle / "task.toml").write_text('schema_version = "1.4"\n')
        (bundle / "tests").mkdir(parents=True, exist_ok=True)
        (bundle / "tests" / "checks.json").write_text(checks_text)
        return _grader_fingerprint(bundle)

    def test_the_fingerprint_follows_content_not_mtime(self):
        """`arena verify` runs the grader and touches these files."""
        import os
        import tempfile
        import time
        with tempfile.TemporaryDirectory() as tmp:
            first = self._fingerprint(tmp, '{"checks": []}')
            later = time.time() + 600
            os.utime(Path(tmp) / "tests" / "checks.json", (later, later))
            from pipeline.calibrate.run import _grader_fingerprint
            self.assertEqual(_grader_fingerprint(Path(tmp)), first,
                             "touching a file must not read as a changed grader")

    def test_a_rewritten_grader_changes_the_fingerprint(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            before = self._fingerprint(tmp, '{"checks": [{"id": "a"}]}')
            after = self._fingerprint(tmp, '{"checks": [{"id": "b"}]}')
        self.assertNotEqual(before, after)

    def test_bytecode_is_ignored(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            before = self._fingerprint(tmp, '{"checks": []}')
            cache = Path(tmp) / "tests" / "__pycache__"
            cache.mkdir()
            (cache / "x.cpython-313.pyc").write_bytes(b"\x00\x01")
            from pipeline.calibrate.run import _grader_fingerprint
            self.assertEqual(_grader_fingerprint(Path(tmp)), before)

    def test_the_gate_blocks_an_unstable_campaign(self):
        source = Path("pipeline/gates/integrity.py").read_text()
        self.assertIn("grader-changed-mid-campaign", source)
        self.assertIn('report.get("grader_stable") is False', source)
        idx = source.index("grader-changed-mid-campaign")
        self.assertIn("Severity.BLOCKER", source[idx-120:idx],
                      "a stale campaign must block, not warn -- its numbers "
                      "look entirely ordinary")


class EveryRequiredProbeIsAsserted(unittest.TestCase):
    """REQUIRED_PROBES is a contract, not a comment.

    Three of its seven entries turned out to be documentation with nothing
    behind them. `plausible_wrong` and `untidy_correct` were found first;
    `destructive` was missed because the fix patched the two entries noticed
    rather than auditing the table -- and it let
    a-002-engineering-thesis-writing score 1.0 while the fixture was broken,
    meaning an agent could destroy the workspace and take full marks.

    So this walks the table and, for each entry, feeds the gate a probe set
    that VIOLATES its stated expectation and requires a blocker. A new entry
    with no enforcement fails here the day it is added.
    """

    #: How to violate each stated expectation.
    VIOLATIONS = {
        "seed_zero": {"reward": 0.0, "objectives": {"o1": 0.5}, "guardrails": {}},
        "golden": {"reward": 0.4},
        "untidy_correct": {"reward": 0.6},
        "plausible_wrong": {"reward": 1.0, "mutated": ["out.json:x"]},
        "destructive": {"reward": 1.0, "destroyed": "brief.md",
                        "destroyed_was_protected": True},
        "forged_state": {"reward": 1.0},
        "answer_lookup": {"reward": 1.0},
    }

    def _healthy(self):
        return {
            "seed_zero": {"reward": 0.0, "objectives": {}, "guardrails": {}},
            "golden": {"reward": 1.0},
            "untidy_correct": {"reward": 1.0},
            "plausible_wrong": {"reward": 0.5, "mutated": ["out.json:x"]},
            "destructive": {"reward": 0.0},
            "forged_state": {"reward": 0.0},
            "answer_lookup": {"reward": 0.0},
            # Not in REQUIRED_PROBES but the gate expects it present; a healthy
            # bundle has it, so the control needs it too.
            "empty_deliverable": {"reward": 0.0},
        }

    def _blockers(self, results):
        import tempfile
        from pipeline.gates import difficulty
        from pipeline.gates.base import GateContext, Severity
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "verification").mkdir()
            (bundle / "authoring").mkdir()
            (bundle / "verification" / "probes.json").write_text(
                json.dumps({"results": results}))
            (bundle / "authoring" / "traps.json").write_text(
                json.dumps({"traps": [], "source_tier": 1}))
            ctx = GateContext(task_dir=bundle, repo_root=bundle,  # gates re-run probes; logic tests hand them the report
                             extras={"probe_report": json.loads((bundle / "verification" / "probes.json").read_text())})
            found = set()
            for fn in (difficulty._trap_beatable, difficulty._hack_resistance):
                try:
                    findings, _ = fn(ctx)
                except Exception:
                    continue
                found |= {f.code for f in findings if f.severity is Severity.BLOCKER}
            # Only probe findings. The synthetic bundle deliberately lacks the
            # rest of a real one (an `untested_surfaces` declaration, for
            # instance), and those blockers are not what this is testing.
            unrelated = {"no-untested-declaration", "no-hack-record",
                         "no-source-tier", "bad-source-tier"}
            return found - unrelated

    def test_a_healthy_probe_set_raises_no_blocker(self):
        """Control. Without this, an always-blocking gate would pass below."""
        self.assertEqual(self._blockers(self._healthy()), set())

    def test_every_stated_expectation_is_enforced(self):
        from pipeline.gates.difficulty import REQUIRED_PROBES
        self.assertEqual(set(self.VIOLATIONS), set(REQUIRED_PROBES),
                         "a probe was added to the table without a violation "
                         "case here, so nothing proves it is enforced")
        for name, violation in self.VIOLATIONS.items():
            with self.subTest(probe=name):
                results = self._healthy()
                results[name] = violation
                self.assertTrue(
                    self._blockers(results),
                    f"{name!r} states {REQUIRED_PROBES[name]!r} and violating it "
                    "produced no blocker -- the entry is documentation, not a rule")

    def test_destructive_specifically_blocks(self):
        """The instance that shipped: fixture broken, task still scoring 1.0."""
        results = self._healthy()
        results["destructive"] = {"reward": 1.0, "destroyed": "brief.md",
                                  "destroyed_was_protected": True}
        self.assertIn("destructive-survives", self._blockers(results))

    def test_breaking_an_unwatched_file_is_no_evidence_either_way(self):
        """The probe used to destroy whatever sorted first alphabetically.

        In four bundles that file backed no projection, so `fixture_intact` had
        nothing to detect and correctly stayed silent -- and the probe reported
        a task scoring 1.0 with a broken fixture as though the guardrails were
        decorative. They were not. Absence of evidence must not read as a
        defect.
        """
        results = self._healthy()
        results["destructive"] = {"reward": 1.0, "destroyed": "notes.txt",
                                  "destroyed_was_protected": False}
        self.assertNotIn("destructive-survives", self._blockers(results))
