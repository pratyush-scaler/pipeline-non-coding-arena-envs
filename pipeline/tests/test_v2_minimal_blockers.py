"""v2 (user, 2026-10-02): blockers and repairs only for required checks; dense
tasks; rules in the documents; no authored-file flags in the fixture."""
import json
import tempfile
import unittest
from pathlib import Path

from pipeline import advisory, policy
from pipeline.gates.base import GateResult, Status


class AdvisoryClassification(unittest.TestCase):
    def test_quotas_and_heuristics_are_advisory(self):
        for finding in (
                "Draft validation: task: require 4-24 core, 0-4 floor, 1-16 stretch objectives across all steps; got {}",
                "task: need at least four distinct core decisions, not multiple fields",
                "02-revision: each scored step needs at least 70% substantive core/stretch weight",
                "check 'c1' carries 40% of the task reward as graded, above 35%.",
                "quality.difficulty_case.misreadings has no entry for trap(s) ['t1']",
                "quality.capability_plan.bottlenecks: need four distinct core judgments",
                "misreading of trap t1: its counterexample x passes no objective when graded",
                "61% of the objective weight is a single-surface read-off (c1). A model with",
                "these objectives resolve to the SAME answer, so the second",
                "the reference answer is mostly repeats, which means the"):
            with self.subTest(finding=finding):
                self.assertIsNotNone(advisory.classify(finding))

    def test_validity_findings_stay_blocking(self):
        for finding in (
                "counterexamples do not cover ['c1']; every objective check must be failed",
                "c1: intended reasoning error did not fail ['c2']",
                "r: complete public-contract reference must score 1",
                "the reference answer contains nulls, so the task is unanswerable",
                "these checks hand-type their answer as a literal list: c1",
                "an EMPTY deliverable already scores 0.5 because",
                "check 'c1': its target applies a rule the agent must be told ({}) but carries no `rule_quote` or valid `rule_sources`.",
                "check 'c1': {} at target.where tests ['ZX9'], which is not discoverable in any agent-readable surface",
                "something nobody has classified yet"):
            with self.subTest(finding=finding):
                self.assertIsNone(advisory.classify(finding))

    def test_split_preserves_order(self):
        blocking, advice = advisory.split(["a real defect", "quality.axes needs at least two", "another defect"])
        self.assertEqual(blocking, ["a real defect", "another defect"])
        self.assertEqual(advice, ["quality.axes needs at least two"])


class SkippedCascade(unittest.TestCase):
    def test_a_gate_skipped_behind_a_failure_is_blocked_not_unverified(self):
        from pipeline.run import verdict
        failed = GateResult(gate="a", status=Status.FAIL)
        skipped = GateResult(gate="b", status=Status.SKIPPED, evidence={"blocked_by": ["a"]})
        self.assertEqual(verdict([failed, skipped])[0], "blocked")

    def test_a_gate_skipped_behind_an_error_is_unverified(self):
        from pipeline.run import verdict
        errored = GateResult(gate="a", status=Status.ERROR, error="x")
        skipped = GateResult(gate="b", status=Status.SKIPPED, evidence={"blocked_by": ["a"]})
        self.assertEqual(verdict([errored, skipped])[0], "unverified")


class DensityAndScenarioLimits(unittest.TestCase):
    def test_bands_allow_dense_tasks(self):
        from pipeline.author.quality import BAND_LIMITS
        self.assertGreaterEqual(BAND_LIMITS["core"][1], 20)
        self.assertGreaterEqual(sum(high for _, high in BAND_LIMITS.values()), 40)
        self.assertEqual(BAND_LIMITS["core"][0], 4)

    def test_authored_documents_use_natural_paths_and_no_fixture_notice(self):
        from pipeline.author import scenario
        self.assertTrue(scenario.NOTICE.startswith("provenance/"))
        scenario._valid_name("correspondence/2026-03-04 re rates.eml")
        scenario._valid_name("policies/expenses-handbook.md")
        for bad in ("provenance/x.md", "../x.md", "notes/run.py", ".hidden/x.md"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                scenario._valid_name(bad)
        self.assertGreaterEqual(scenario.MAX_FILE_BYTES, 256 * 1024)


class LeverDoctrine(unittest.TestCase):
    def test_doctrine_leads_the_system_prompt(self):
        from pipeline.author import agent_designer as a
        self.assertTrue(a.SYSTEM.lstrip().startswith("====="))
        self.assertLess(a.SYSTEM.index("V2.1 DIFFICULTY DOCTRINE"), a.SYSTEM.index("THE FIRST PASS IS THE ONLY PASS"))
        self.assertNotIn("FIRST-DRAFT ADVERSARIAL DESIGN", a.SYSTEM)

    def test_diagnostics_are_advisory_and_audit_the_budget(self):
        from pipeline.author.levers import diagnostics, LEVERS
        spec = {"steps": [{"name": "01", "instruction": "Please note that you should verify the totals."}],
                "checks": [{"id": "c1", "kind": "objective"}],
                "quality": {"counterexamples": [{"id": "x"}], "fragility_budget": [
                    {"id": "d1", "lever": "surface_variant_identity", "targets": "astra",
                     "files": [], "trigger": "t1", "checks": ["c1"], "counterexample": "x"},
                    {"id": "d2", "lever": "not-a-lever", "targets": "fable",
                     "files": [], "trigger": "t1", "checks": ["missing"], "counterexample": "y"}]}}
        report = diagnostics(spec)
        text = " ".join(report["advisories"])
        self.assertIn("not a catalogued lever", text)
        self.assertIn("not declared", text)
        self.assertIn("share a noticing trigger", text)
        self.assertIn("announcing or procedural words", text)
        self.assertEqual(report["per_family"], {"fable": 1, "astra": 1})
        self.assertGreaterEqual(len(LEVERS), 25)


class WitnessMode(unittest.TestCase):
    def test_policy_selects_witness_mode(self):
        self.assertEqual(policy.HIDDEN_RULE_MODE, "witness")


if __name__ == "__main__":
    unittest.main()


class WitnessModeEndToEnd(unittest.TestCase):
    """A document's rule need not repeat the column name in the instruction."""

    def setUp(self):
        from pipeline.tests.test_capability_construction import CSV, sample_spec
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        fixture = self.root / "environment/files"
        fixture.mkdir(parents=True)
        (fixture / "tickets.csv").write_text(CSV)
        # The rule as an organisation writes it: no column name, no quoting.
        self.rule = "This report covers only the tickets that are still open."
        (fixture / "handbook.md").write_text("# Handbook\n\nSection 4. " + self.rule + "\n")
        self.spec = sample_spec()
        self.spec["steps"][0]["instruction"] = "Prepare the weekly report for the operations lead."
        for check in self.spec["checks"][1:]:
            check["rule_sources"] = [{"file": "handbook.md", "quote": self.rule}]

    def test_document_rule_is_not_a_blocker(self):
        from pipeline.author import validate
        problems = validate._hidden_rules(self.spec, self.root)
        blocking, _ = advisory.split(problems)
        self.assertEqual(blocking, [], problems)

    def test_a_value_no_reader_can_find_still_blocks(self):
        from pipeline.author import validate
        self.spec["checks"][1]["target"]["of"]["where"]["eq"] = "ZQX-77"
        blocking, _ = advisory.split(validate._hidden_rules(self.spec, self.root))
        self.assertTrue(any("not discoverable" in p for p in blocking), blocking)

    def test_a_check_with_no_witness_still_blocks(self):
        from pipeline.author import validate
        for check in self.spec["checks"][1:]:
            check.pop("rule_sources", None)
        blocking, _ = advisory.split(validate._hidden_rules(self.spec, self.root))
        self.assertTrue(blocking)


class RepairShrinksPerStage(unittest.TestCase):
    """a-003, 2026-10-02: 2 gate findings fixed, then the review's first 8
    findings plus a solver-autonomy note must be admissible, not 'churn'."""

    def test_review_findings_after_cleared_gates_are_admissible(self):
        from pipeline import repair
        with tempfile.TemporaryDirectory() as d:
            bundle = Path(d)
            (bundle / "verification").mkdir()
            gate = ["contract.ambiguity: overlapping-categories: `a` and `b` share 60% [schema:x.json:y]",
                    "hacking.resistance: answer-readable-in-fixture: 4 check(s) [verification/probes.json]"]
            (bundle / "verification/repair-log.json").write_text(json.dumps({
                "schema": "arena-pipeline/repair-log/1",
                "passes": [{"index": 1, "fingerprints": [repair.fingerprint(f) for f in gate],
                            "findings": gate, "outcome": "charged", "phase": "gate"}]}))
            now = [f"Semantic review obj_{i}: issue {i} in steps/01-task/instruction.md" for i in range(8)]
            now.append("Solver autonomy: steps/01-task/instruction.md names a reading order")
            ok, why = repair.admissible(bundle, now)
            self.assertTrue(ok, why)
            self.assertEqual(repair.finding_stage(now[-1]), "semantic-review")

    def test_a_stage_that_grows_is_still_refused(self):
        from pipeline import repair
        with tempfile.TemporaryDirectory() as d:
            bundle = Path(d)
            (bundle / "verification").mkdir()
            review = [f"Semantic review c{i}: defect {i} [tests/checks.json]" for i in range(2)]
            (bundle / "verification/repair-log.json").write_text(json.dumps({
                "schema": "arena-pipeline/repair-log/1",
                "passes": [{"index": 1, "fingerprints": [repair.fingerprint(f) for f in review],
                            "findings": review, "outcome": "charged", "phase": "review"}]}))
            now = [f"Semantic review d{i}: new defect {i} [tests/checks.json]" for i in range(3)]
            ok, why = repair.admissible(bundle, now)
            self.assertFalse(ok)
            self.assertIn("did not shrink", why)


class StagedFixesAfterFirstBatchWave(unittest.TestCase):
    """2026-10-02 build: context overflow (a-018, a-015), email-only privacy
    errors (a-001, a-004, a-036, a-056), a field-definition false positive
    (a-032) and a review whose own receipt was malformed (a-051)."""

    def test_email_addresses_are_redacted_consistently(self):
        from pipeline.ledger.redaction import transform
        from pipeline.privacy import PATTERNS, _not_an_address
        out, _ = transform("Mail a.b@osm.org, then c@x.de, then a.b@osm.org.", ["email"])
        self.assertEqual(out.count("contact-1@example.com"), 2)
        self.assertIn("contact-2@example.com", out)
        self.assertTrue(all(_not_an_address(m.group(1)) for m in PATTERNS["email"].finditer(out)))

    def test_a_field_referenced_mid_definition_does_not_end_it(self):
        from pipeline.author.validate import _definition_windows
        text = ("- `uhd_elvas` — lista de `pedido` (texto) dos pedidos que deviam ter sido "
                "admitidos na UHD de Elvas.\n- `pedido` — o identificador do pedido.")
        self.assertTrue(_definition_windows(text, "uhd_elvas", {"uhd_elvas", "pedido"}))
        lend = "`workdays`. `elapsed_days` is the number of calendar days elapsed."
        self.assertFalse(_definition_windows(lend, "workdays", {"workdays", "elapsed_days"}))

    def test_request_stays_within_the_context_budget_and_keeps_pairs(self):
        from pipeline.author.agent_designer import within_context_budget
        msgs = [{"role": "user", "content": "start"}]
        for i in range(60):
            msgs.append({"role": "assistant", "content": [{"type": "tool_use", "id": f"t{i}", "name": "read_fixture", "input": {}}]})
            msgs.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "x" * 50000}]})
        small = within_context_budget(msgs, budget=1_000_000)
        self.assertLessEqual(len(json.dumps(small)), 1_000_000)
        results = [b for m in small if isinstance(m["content"], list) for b in m["content"] if b.get("type") == "tool_result"]
        self.assertEqual(len(results), 60)
        self.assertEqual(small[-1]["content"][0]["content"], "x" * 50000)   # newest kept
        self.assertEqual(msgs[1]["content"][0]["type"], "tool_use")        # input untouched

    def test_a_revision_request_with_a_malformed_reviewer_quote_is_a_rejection(self):
        from pipeline.review import semantic_rejection
        self.assertTrue(semantic_rejection([
            "invalid solver autonomy citation fixture/x.txt (quote absent, too short or not the complete tiny file)",
            "semantic reviewer requested revision", "unresolved review findings: substantive_gaps"]))
        self.assertFalse(semantic_rejection(["invalid review citation fixture/x.txt"]))


class DoctrineV21Audit(unittest.TestCase):
    """research/R6: noticing traps measured q ~ 0; only default-wrong,
    unlabelled entries on routes b-e count."""

    def test_admission_fields_baseline_and_echo_are_audited(self):
        from pipeline.author.levers import diagnostics
        rule = "Every listing on any Facebook property counts as social proof for the lead."
        spec = {"steps": [{"name": "01", "instruction": "List each lead; every listing on any facebook property counts."}],
                "checks": [{"id": "c1", "kind": "objective", "rule_sources": [{"file": "p.md", "quote": rule}]},
                           {"id": "c2", "kind": "objective", "rule_sources": [{"file": "p.md", "quote": "Lines marked MEMO are not postings."}]}],
                "quality": {"counterexamples": [{"id": "x"}], "fragility_budget": [
                    {"id": "d1", "lever": "surface_variant_identity", "targets": "astra", "files": ["a.csv"],
                     "trigger": "t", "checks": ["c1"], "counterexample": "x"}]}}
        text = " ".join(diagnostics(spec)["advisories"])
        for needle in ("no route", "idiomatic baseline gets wrong", "no label", "baseline_",
                       "no executed idiomatic baseline", "negates something", "echoes its rule witness"):
            self.assertIn(needle, text)

    def test_prompt_states_the_wave1_measurement_and_routes(self):
        from pipeline.author.levers import PROMPT
        for needle in ("0 lever\nfailures in 1,220", "THE ADMISSION TEST", "(b) MIS-SCOPED", "(c) A DEFAULT NUMERIC",
                       "(d) A TRIGGER FACT", "(e) TWO RULES FROM TWO DOCUMENTS", "STEP 2 IS REBUILT FROM SCRATCH"):
            self.assertIn(needle, PROMPT)


class StepNumberReferences(unittest.TestCase):
    """a-011's first hardening attempt was spent on 510 findings because the
    designer wrote steps as 1 and 2 (2026-10-02)."""

    def test_bare_step_numbers_map_to_declared_steps(self):
        from pipeline.author.validate import canonical_step_refs
        spec = {"steps": [{"name": "01-task"}, {"name": "02-revision"}],
                "checks": [{"id": "a", "step": 1}, {"id": "b", "step": "2"}, {"id": "c", "step": "02-revision"},
                           {"id": "d", "step": 3}, {"id": "e", "step": "later"}, {"id": "f", "step": True}]}
        self.assertEqual(canonical_step_refs(spec), 2)
        self.assertEqual([c["step"] for c in spec["checks"]],
                         ["01-task", "02-revision", "02-revision", 3, "later", True])

    def test_an_out_of_range_step_is_still_reported(self):
        from pipeline.author.validate import _second_step, canonical_step_refs
        spec = {"steps": [{"name": "01-task"}], "checks": [{"id": "a", "step": 2}]}
        canonical_step_refs(spec)
        self.assertTrue(any("not declared" in p for p in _second_step(spec)))


class DoctrineV22Interlocks(unittest.TestCase):
    """Lever lab: every single mechanism was solved 10/10; the doctrine asks for
    interlocks of two or more levers on one decision."""

    def test_single_mechanism_entries_are_flagged_and_interlocks_need_partials(self):
        from pipeline.author.levers import diagnostics
        spec = {"steps": [{"name": "01", "instruction": "Settle the quarter."}], "checks": [{"id": "c1", "kind": "objective"}],
                "quality": {"counterexamples": [{"id": "baseline_partial_a"}], "fragility_budget": [
                    {"id": "d1", "lever": "rounding_stage", "levers": ["rounding_stage"], "checks": ["c1"]},
                    {"id": "d2", "lever": "masking_pair", "levers": ["masking_pair", "surface_variant_identity"],
                     "partial_counterexamples": ["baseline_partial_a", "baseline_partial_missing"], "checks": ["c1"]}]}}
        result = diagnostics(spec)
        text = " ".join(result["advisories"])
        self.assertIn("single-mechanism decision", text)
        self.assertIn("baseline_partial_missing", text)
        self.assertEqual(result["interlocks"], 1)
        self.assertEqual(result["doctrine"], "v2.2-2026-10-02")

    def test_combination_recipes_are_catalogued_and_the_prompt_leads_with_them(self):
        from pipeline.author.levers import LEVERS, PROMPT
        for name in ("masking_pair", "cascade_premise", "control_total_blind", "cross_step_premise",
                     "opposite_skew_population", "multi_lever_item"):
            self.assertIn(name, LEVERS)
            self.assertIn(f" - {name} [", PROMPT)
        self.assertIn("V2.2 -- INTERLOCKS, NEVER SINGLE TRAPS", PROMPT)
        self.assertLess(PROMPT.index("V2.2 -- INTERLOCKS"), PROMPT.index("WHAT WAVE 1 MEASURED"))

    def test_measured_evidence_renders_from_the_registry(self):
        from pipeline.author import levers
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lever_evidence.json"
            path.write_text(json.dumps({"labs": {"L99": {"shape": "combined", "mechanism": "m",
                "per_model": {"anthropic/claude-fable-5-1": {"valid": 5, "passes": 1}}}}}))
            original = levers.EVIDENCE_PATH
            try:
                levers.EVIDENCE_PATH = path
                self.assertIn("L99 [combined] m: claude-fable-5-1 1/5 solved", levers._evidence_table())
                levers.EVIDENCE_PATH = Path(tmp) / "absent.json"
                self.assertIn("no lever-lab measurements", levers._evidence_table())
            finally:
                levers.EVIDENCE_PATH = original

    def test_the_hardening_brief_asks_for_interlocks(self):
        from pipeline.harden import HARDENING_BRIEF
        self.assertTrue(HARDENING_BRIEF.startswith("V2.2 INTERLOCKS"))
        self.assertIn("baseline_partial_", HARDENING_BRIEF)

    def test_undefined_category_repair_never_asks_for_a_restated_rule(self):
        import inspect
        from pipeline.gates import findings
        source = inspect.getsource(findings)
        self.assertIn("never restate its threshold", source)


class HardeningAppliesTheAdvisorySplit(unittest.TestCase):
    """a-049's first hardening attempt was spent on 323 lexical co-occurrence
    findings the designer's check_draft had shown as advisories (2026-10-02)."""

    def test_harden_validates_through_the_split(self):
        import inspect
        from pipeline import harden
        source = inspect.getsource(harden.attempt)
        self.assertIn("advisory.split(validate(revised, target)", source)
        self.assertIn("advisory.split(budget_problems(", source)

    def test_witness_cooccurrence_and_routing_quota_are_advisory_but_step_errors_block(self):
        blocking, advised = advisory.split([
            "check 'c': {\"field\": \"x\", \"eq\": \"y\"} at target.where is not stated by any rule_quote "
            "(no quoted sentence names ['x'])",
            "new trap t1 drives 1 graded objective(s); route at least 2 through it so one wrong premise costs several checks",
            "check 's1' is assigned to step '7', which is not declared (steps: ['01-task']). It would be graded "
            "in the first step instead."])
        self.assertEqual(len(advised), 2)
        self.assertEqual(len(blocking), 1)
        self.assertIn("not declared", blocking[0])


class VoidedHardeningAttempts(unittest.TestCase):
    """An invalid, unscreened attempt lost to a fixed pipeline defect measured
    nothing; it is recorded, never deleted, and does not spend the budget."""

    def _lineage(self, tmp, outcome="invalid", screened=False):
        from pipeline import harden
        root = Path(tmp) / "a-001"
        (root / "hardened").mkdir(parents=True)
        ledger = {"schema": "arena-pipeline/hardening/1", "status": "open", "max_attempts": 3,
                  "attempts": [{"attempt": 1, "kind": "harden", "revision": "hardened/v2", "outcome": outcome,
                                "findings": ["x"]}],
                  "screens": [{"revision": "hardened/v2"}] if screened else [], "interruptions": []}
        (root / harden.LEDGER).write_text(json.dumps(ledger))
        return root

    def test_void_restores_the_attempt_and_keeps_the_row(self):
        from pipeline import harden
        with tempfile.TemporaryDirectory() as tmp:
            root = self._lineage(tmp)
            self.assertEqual(harden.attempts_left(harden.read_ledger(root)), 2)
            harden.void_attempt(root, 1, "advisories re-raised as blockers by the hardening path", "e9156c1")
            ledger = harden.read_ledger(root)
            self.assertEqual(harden.attempts_left(ledger), 3)
            self.assertEqual(len(ledger["attempts"]), 1)
            self.assertEqual(ledger["attempts"][0]["voided_by_pipeline_defect"]["fixed_by"], "e9156c1")

    def test_a_screened_or_valid_attempt_cannot_be_voided(self):
        from pipeline import harden
        for outcome, screened in (("valid", False), ("invalid", True)):
            with tempfile.TemporaryDirectory() as tmp:
                root = self._lineage(tmp, outcome, screened)
                with self.assertRaises(ValueError):
                    harden.void_attempt(root, 1, "advisories re-raised as blockers by the hardening path", "e9156c1")

    def test_a_void_needs_a_reason_and_a_fix(self):
        from pipeline import harden
        with tempfile.TemporaryDirectory() as tmp:
            root = self._lineage(tmp)
            with self.assertRaises(ValueError):
                harden.void_attempt(root, 1, "bug", "")


class TrajectoryDigest(unittest.TestCase):
    """The hardener sees HOW the agents beat a version: files, greps, notes."""

    def test_digest_counts_files_greps_and_cue_sentences(self):
        from pipeline import trajectory_digest as t
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "files"
            (fixture / "policies").mkdir(parents=True)
            (fixture / "policies/expense_policy.md").write_text("x")
            (fixture / "ledger.csv").write_text("x")
            (fixture / "unused_notes.md").write_text("x")
            for i in range(2):
                trial = Path(tmp) / "camp" / "jobs" / "run" / f"t{i}"
                agent = trial / "steps" / "01-task" / "agent"
                agent.mkdir(parents=True)
                (trial / "result.json").write_text("{}")
                (agent / "trajectory.json").write_text(json.dumps({"steps": [
                    {"source": "agent", "message": "I excluded the two refunded lines after checking the memo.",
                     "tool_calls": [
                         {"function_name": "Bash", "arguments": {"command": "cat /app/environment/files/ledger.csv | grep -i 'refund'"}},
                         {"function_name": "Read", "arguments": {"file_path": "/app/environment/files/policies/expense_policy.md"}}]}]}))
            data = t.digest([Path(tmp) / "camp"], fixture)
            row = data["steps"]["01-task"]
            self.assertEqual(row["episodes"], 2)
            self.assertEqual(row["opened_by_every_episode"], ["ledger.csv", "policies/expense_policy.md"])
            self.assertEqual(row["never_opened"], ["unused_notes.md"])
            self.assertEqual(row["top_greps"][0], ("refund", 2))
            text = t.render(data)
            self.assertIn("files NO episode opened (1): unused_notes.md", text)
            self.assertIn("agent said: I excluded the two refunded lines", text)
            self.assertEqual(t.render({"steps": {}}), "")

    def test_the_hardening_brief_carries_the_digest(self):
        import inspect
        from pipeline import harden
        self.assertIn("for_bundle(measured or bundle)", inspect.getsource(harden.propose))


class PrintedAnswers(unittest.TestCase):
    """2026-10-02 audit: a-009 printed all thirteen computed gaps in an audit
    report ('+31,1 +27,3 ... -14,2') and the token probe saw none."""

    def test_locale_spellings_are_read(self):
        from pipeline.author.probes import _number_readings, _PRINTED_NUMBER, _EASTERN_DIGITS
        def numbers(text):
            out = set()
            for m in _PRINTED_NUMBER.finditer(text.translate(_EASTERN_DIGITS)):
                out |= _number_readings(m.group(1), m.group(2))
            return out
        self.assertIn("31.1", numbers("gap +31,1 pp"))
        self.assertIn("-14.2", numbers("gap −14,2"))
        self.assertIn("1207.83", numbers("AED 1,207.83 due"))
        self.assertIn("1207.83", numbers("AED 1 207,83"))
        self.assertIn("1250.5", numbers("١٢٥٠.٥"))

    def test_an_arithmetic_answer_printed_outside_the_inputs_is_reported(self):
        import types
        from pipeline.author import probes
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            (fixture / "data.csv").write_text("x\n10.10\n20.25\n30.40\n")
            (fixture / "report.md").write_text("Gaps: +12,35 / 45,65 / -3,15 as computed last quarter.")
            (fixture / "notes.md").write_text("Threshold 10.10 applies.")
            check = types.SimpleNamespace(id="gaps", kind="objective", target={"op": "subtract", "a": 1, "b": 2})
            original = probes.evaluate
            try:
                probes.evaluate = lambda target, ws, side: [{"g": 12.35}, {"g": 45.65}, {"g": -3.15}, {"base": 10.10}]
                out = probes._printed_answers([check], None, fixture, [{"as": "d.jsonl", "file": "data.csv"}])
            finally:
                probes.evaluate = original
            self.assertEqual(out["printed_derived"]["gaps"]["in"], "report.md")
            self.assertEqual(out["printed_derived"]["gaps"]["of"], 3)

    def test_a_selection_is_never_a_printed_answer(self):
        import types
        from pipeline.author import probes
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            (fixture / "report.md").write_text("12.35 45.65 3.15")
            check = types.SimpleNamespace(id="sel", kind="objective", target={"op": "latest", "of": {"op": "rows", "file": "x"}})
            original = probes.evaluate
            try:
                probes.evaluate = lambda target, ws, side: [12.35, 45.65, 3.15]
                out = probes._printed_answers([check], None, fixture, [])
            finally:
                probes.evaluate = original
            self.assertEqual(out, {"printed_derived": {}, "printed_partial": {}})

    def test_the_gate_blocks_and_the_review_routes_printed_answers_to_shortcut_risks(self):
        import inspect
        from pipeline.gates import integrity
        from pipeline import review
        self.assertIn("answer-printed-in-fixture", inspect.getsource(integrity))
        self.assertIn("PRINTED ANSWERS", inspect.getsource(review))


class ProvisioningRetriesTransientSsh(unittest.TestCase):
    def test_transient_classification(self):
        from pipeline.benchmark.coder import transient_ssh_error
        self.assertTrue(transient_ssh_error('RuntimeError: coder ssh failed (1): Encountered an error running "coder ssh" error: run command: EOF'))
        self.assertFalse(transient_ssh_error("RuntimeError: workspace x is below the required specs: vCPU 8 < 32"))


class DeclaredExclusiveValuesAreNotAnOverlap(unittest.TestCase):
    def test_a_contract_declaring_mutually_exclusive_values_is_a_warn(self):
        import inspect
        from pipeline.gates import findings
        self.assertIn("declared_exclusive", inspect.getsource(findings))


class StringifiedExpressions(unittest.TestCase):
    """a-049's hardening attempt was spent on 29 expressions sent as JSON text."""

    def test_nested_expression_strings_become_objects(self):
        from pipeline.author.validate import parse_stringified_expressions
        spec = {"checks": [{"id": "c", "target": {"op": "derive_rows", "fields": {
            "SO-01": '{"op": "round", "mode": "half_up", "places": 2, "of": {"op": "field", "file": "x", "path": "a"}}',
            "note": "{not json", "plain": "literal text"}}}]}
        self.assertEqual(parse_stringified_expressions(spec), 1)
        fields = spec["checks"][0]["target"]["fields"]
        self.assertEqual(fields["SO-01"]["op"], "round")
        self.assertEqual(fields["note"], "{not json")
        self.assertEqual(fields["plain"], "literal text")


class PrintedAnswerGateFormats(unittest.TestCase):
    """The printed-answer finding crashed the gate with map(...)[:6] (a-006, 2026-10-02)."""

    def test_the_gate_message_formats_without_raising(self):
        import inspect
        from pipeline.gates import integrity
        source = inspect.getsource(integrity)
        self.assertNotIn("map(str, where.get('values') or [])[:6]", source)
        values = [1207.83, 309, "44.1"]
        self.assertEqual(", ".join(str(v) for v in values[:6]), "1207.83, 309, 44.1")


class RaisedAttemptCap(unittest.TestCase):
    """User 2026-10-02: spent lineages may get more attempts, recorded in the ledger."""

    def test_raise_reopens_and_extends_the_budget(self):
        from pipeline import harden
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "a-001"
            (root / "hardened").mkdir(parents=True)
            ledger = {"schema": "arena-pipeline/hardening/1", "status": "no-progress", "max_attempts": 3,
                      "attempts": [{"attempt": i, "outcome": "invalid", "revision": "hardened/v2"} for i in (1, 2, 3)],
                      "screens": [], "interruptions": []}
            (root / harden.LEDGER).write_text(json.dumps(ledger))
            self.assertEqual(harden.attempts_left(harden.read_ledger(root)), 0)
            harden.raise_attempt_cap(root, 6, "user 2026-10-02: raise the cap for spent lineages")
            after = harden.read_ledger(root)
            self.assertEqual(harden.attempts_left(after), 3)
            self.assertEqual(after["status"], "open")
            self.assertEqual(after["overrides"][0]["status_before"], "no-progress")
            with self.assertRaises(ValueError):
                harden.raise_attempt_cap(root, 3, "user 2026-10-02: raise the cap for spent lineages")


class RepairGrant(unittest.TestCase):
    """User 2026-10-02: 'Also fix the blocked tasks' -- extra repair passes, recorded."""

    def test_grant_extends_budget_and_resets_the_monotone_anchor(self):
        from pipeline import repair, checkpoint
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "a-001"
            (bundle / "verification").mkdir(parents=True)
            log = {"schema": "arena-pipeline/repair-log/1", "passes": [
                {"fingerprints": [repair.fingerprint("f1 in tests/checks.json")]},
                {"fingerprints": [repair.fingerprint("f1 in tests/checks.json")]}]}
            (bundle / repair.LOG).write_text(json.dumps(log))
            self.assertEqual(checkpoint.repairs_left(bundle), 0)
            ok, _ = repair.admissible(bundle, ["f1 in tests/checks.json"])
            self.assertFalse(ok)
            repair.grant_repairs(bundle, 2, "user 2026-10-02: Also fix the blocked tasks")
            self.assertEqual(checkpoint.repairs_left(bundle), 2)
            ok, why = repair.admissible(bundle, ["f1 in tests/checks.json"])
            self.assertTrue(ok, why)
            self.assertEqual(repair.history(bundle)["operator_grant"]["since_pass"], 2)
