"""The 2026-09-28 difficulty techniques are in the prompt production sends,
and the wording that neutralised traps is gone.

Measured before the change: 18 built instructions ran 16k-29k characters,
2.5-12.5x their schema, named 135 fixture files, said "revis" 104 times and
"governs" 38 times, and the reviewer's own advisory read "Every planted trap is
neutralised by an explicit numbered rule in the public instruction". The prompt
had told the designer to do exactly that ("say which wins", "Explicitly state
the precedence rule") while also saying "never how to compute it".
"""
import unittest


class TheInstructionStatesTheAssignmentNotTheAnalysis(unittest.TestCase):
    def test_the_leaky_contract_wording_is_gone(self):
        from pipeline.author import agent_designer as a
        from pipeline.author.quality import QUALITY_PROMPT
        self.assertNotIn("what it holds and how it is computed", a.SYSTEM)
        self.assertNotIn("say which wins when two could apply", a.SYSTEM)
        self.assertNotIn("Explicitly state\n  the precedence rule", QUALITY_PROMPT)

    def test_fields_are_defined_by_meaning_and_format(self):
        from pipeline.author import agent_designer as a
        self.assertIn("DEFINE EVERY FIELD BY MEANING AND FORMAT", a.SYSTEM)
        self.assertIn("Never how to compute it, which document to read", a.SYSTEM)
        self.assertIn("the instruction does not say which wins", a.SYSTEM)

    def test_the_instruction_is_silent_about_how(self):
        from pipeline.author import agent_designer as a
        self.assertIn("THE INSTRUCTION STATES THE ASSIGNMENT, NOT THE ANALYSIS", a.SYSTEM)
        for line in ("revised, stale, superseded, conflicting",
                     "restate a precedence rule, threshold or rate that a fixture document",
                     "list steps, joins, checks, cross-references or things to watch for",
                     "name a trap family or describe a misreading"):
            self.assertIn(line, a.SYSTEM)

    def test_rules_live_in_the_world_within_what_the_validator_allows(self):
        """The validator verifies either instruction or step-available fixture rules."""
        from pipeline.author import agent_designer as a
        from pipeline.author.quality import QUALITY_PROMPT
        self.assertIn("RULES LIVE IN THE WORLD", a.SYSTEM)
        self.assertIn("rule_sources", a.SYSTEM)
        self.assertIn("quote available", a.SYSTEM)
        self.assertIn("`bind_rows`", a.SYSTEM)
        self.assertIn("in the fixture\n  document where a professional would find it", QUALITY_PROMPT)

    def test_the_validator_message_no_longer_asks_for_a_recipe(self):
        import inspect
        from pipeline.author import validate
        src = inspect.getsource(validate)
        self.assertNotIn("what the value is and how it", src)
        self.assertIn("what the value IS and its exact", src)

    def test_the_reviewer_treats_fixture_rules_as_published(self):
        import inspect
        from pipeline import review
        src = inspect.getsource(review)
        self.assertIn("agent-visible fixture document is published", src)
        self.assertIn("belongs in difficulty_advisories", src)


class TheTrapsAreConfusingNeverUnfair(unittest.TestCase):
    def test_the_new_families_are_in_the_hunt(self):
        from pipeline.author import agent_designer as a
        for family in ("14. NEAR-MISS DECOY", "15. IMPLICIT INVALIDATION", "16. VOCABULARY VARIANCE"):
            self.assertIn(family, a.SYSTEM)
        self.assertIn("sixteen pitfall families", a.AUTHORING_MANDATE)
        self.assertIn("retention versus payable, accrual versus cash", a.SYSTEM)

    def test_every_technique_is_named(self):
        from pipeline.author import agent_designer as a
        block = a.SYSTEM[a.SYSTEM.index("MAKE THE TRAPS CONFUSING"):a.SYSTEM.index("EVERY TRAP GENUINE")]
        for heading in ("NEAR-MISS DECOYS", "THE DECISIVE QUALIFIER SITS WHERE A PROFESSIONAL LOOKS",
                        "VOCABULARY VARIANCE", "EXPERT-ONLY ERRORS", "INDEPENDENCE AND MIX",
                        "SMALL POPULATIONS", "INVALIDATE IMPLICITLY",
                        "LONG MEANS DEEP, NOT BIG", "FULL-SUCCESS ARITHMETIC",
                        "EVERY FAILURE MUST TRACE TO A NAMED TRAP", "AVOID SAFEGUARD TERRITORY"):
            self.assertIn(heading, block)

    def test_decoys_are_near_misses_and_fidelity_bound(self):
        from pipeline.author import agent_designer as a
        self.assertIn("Unrelated filler is\n    never a decoy", a.SYSTEM)
        self.assertIn("90% fixture fidelity", a.SYSTEM)
        self.assertIn("grounded in a verbatim quote from a\n    recovered file", a.SYSTEM)
        self.assertNotIn("more output fields or more \\\ndecoys", a.SYSTEM)

    def test_model_hypotheses_are_labelled_unverified(self):
        from pipeline.author import agent_designer as a
        self.assertIn("STARTING HYPOTHESES ON THE TWO CALIBRATION MODELS -- UNVERIFIED", a.SYSTEM)
        self.assertIn("measured calibration data overrides them", a.SYSTEM)

    def test_the_negative_first_test_is_stated(self):
        from pipeline.author import agent_designer as a
        self.assertIn("ADDING ONE TRAP TO AN EASY TASK DOES NOT", a.SYSTEM)
        self.assertIn("pass@1 0.88 and moved it to 0.80", a.SYSTEM)

    def test_families_map_onto_the_schema_trap_types(self):
        from pipeline.author import agent_designer as a
        from pipeline.author.traps import TAXONOMY
        block = a.SYSTEM[a.SYSTEM.index("Record each candidate's family"):a.SYSTEM.index("MAKE THE TRAPS CONFUSING")]
        for key in TAXONOMY:
            if key != "unreadable_source":
                self.assertIn(key, block, f"{key} has no family mapped to it")

    def test_the_hardening_brief_no_longer_publishes_the_governing_document(self):
        from pipeline import harden
        self.assertNotIn("the instruction must publish which", harden.HARDENING_BRIEF)
        self.assertIn("Do not announce the solved source-selection answer", harden.HARDENING_BRIEF)
        self.assertIn("explicit normative authority and revision conventions", harden.HARDENING_BRIEF)
        self.assertIn("Naming a governing document is NOT automatically a leak", harden.HARDENING_BRIEF)
        # v2 (2026-10-02): rules are witnessed in the documents, never moved into the instruction.
        self.assertIn("do NOT move a document's rule into the instruction", harden.HARDENING_BRIEF)

    def test_the_operator_evidence_is_current(self):
        from pipeline.author import agent_designer as a
        self.assertIn("ZERO", a.SYSTEM)
        self.assertIn("`derive_rows` 431", a.SYSTEM)
        self.assertIn("derivation is necessary and not sufficient", a.SYSTEM)


if __name__ == "__main__":
    unittest.main()


class TheHardeningBriefCarriesTheSameTechniques(unittest.TestCase):
    """The hardening session reads the authoring system prompt; its brief must
    not pull the designer back toward leaky instructions, and it must feed the
    diagnosis the loop can give without solver answers."""

    def test_the_brief_de_leaks_first_and_names_the_killer_set(self):
        from pipeline import harden
        b = harden.HARDENING_BRIEF
        self.assertIn("1. DE-LEAK THE INSTRUCTION FIRST", b)
        self.assertLess(b.index("DE-LEAK THE INSTRUCTION FIRST"), b.index("UNDERSTAND FIRST"))
        for family in ("REVISED PREMISE", "GOVERNING CONFLICT", "RESIDUE", "MERGED CONCEPTS",
                       "NEAR-MISS DECOY", "IMPLICIT INVALIDATION"):
            self.assertIn(family, b)
        self.assertIn("The criterion is\n     published; which document meets it is never stated.", b)

    def test_the_contradictions_are_gone(self):
        from pipeline import harden
        b = harden.HARDENING_BRIEF
        self.assertNotIn("the instruction says which governs", b)
        self.assertNotIn("derivation depth, length", b)
        self.assertIn("depth with no premise inside it has measured 1.00", b)
        self.assertNotIn("tune against solver\n   answers", b)
        self.assertIn("never solver answers", b)
        for phrase in ("as confusing as", "Confusing is not unfair"):
            self.assertNotIn(phrase, b + harden.FIRST_ATTEMPT + harden.TIGHTEN_ATTEMPT)

    def test_every_free_check_and_every_dead_trap_must_be_re_aimed(self):
        from pipeline import harden
        self.assertIn("re-aim\n   EVERY free check beyond it into a NEW premise", harden.HARDENING_BRIEF)
        # V4 (2026-10-13): one premise per family per task replaces "no per-family count quota".
        self.assertIn("One premise per family per task", harden.HARDENING_BRIEF)
        self.assertNotIn("no per-family count quota", harden.HARDENING_BRIEF)
        self.assertNotIn("at most two from one family", harden.HARDENING_BRIEF)
        self.assertIn("BINDING\n   MODEL", harden.HARDENING_BRIEF)
        self.assertIn("never-bit list", harden.TIGHTEN_ATTEMPT)
        self.assertIn("de-leak the instruction first", harden.FIRST_ATTEMPT)
        self.assertIn("a failure no declared trap explains is\na defect to repair, not difficulty", harden.HARDENING_BRIEF)

    def test_the_brief_still_formats_with_the_same_placeholders(self):
        from pipeline import harden
        text = harden.HARDENING_BRIEF.format(targets="T", breadth="B", requested="", budget="$")
        self.assertNotIn("{", text.replace("{{", "").replace("}}", ""))
        self.assertIn("\n6. KEEP FAITHFULNESS", text)

    def test_the_calibration_summary_names_the_binding_model_and_dead_traps(self):
        from unittest.mock import patch
        from pathlib import Path
        from pipeline import harden
        report = {"checks": {
            "01/o_free": {"id": "o_free", "step": "01", "weight": 20,
                          "by_model": {"m1": {"rate": 1.0}, "m2": {"rate": 0.95}}},
            "01/o_bit": {"id": "o_bit", "step": "01", "weight": 20,
                         "by_model": {"m1": {"rate": 0.4}, "m2": {"rate": 1.0}}}},
            "by_model": {"m1": {"pass_at_1": 0.8}, "m2": {"pass_at_1": 0.6}}}
        traps = [{"id": "t_dead", "checks": ["o_free"]},
                 {"id": "t_live", "checks": ["o_free", "o_bit"]},
                 {"id": "t_none", "checks": ["o_missing"]}]
        with patch("pipeline.harden.hardenable", return_value=report):
            text = harden._breadth_summary(Path("x"), [], traps=traps)
        self.assertIn("BINDING MODEL: m1 (pass@1 0.80; m2 0.60)", text)
        self.assertIn("TRAPS THAT NEVER BIT", text)
        self.assertIn("t_dead (drives o_free)", text)
        self.assertNotIn("t_live (", text)
        self.assertIn("traps driving no measured check: t_none", text)
        with patch("pipeline.harden.hardenable", return_value={"checks": {}, "by_model": {}}):
            self.assertEqual(harden._breadth_summary(Path("x"), [], traps=traps),
                             "  no per-check calibration on record")

    def test_no_dead_trap_line_without_traps(self):
        """Callers that pass no traps (older tests, report mode) see the old shape."""
        from unittest.mock import patch
        from pathlib import Path
        from pipeline import harden
        report = {"checks": {"01/o": {"id": "o", "step": "01", "weight": 1,
                                      "by_model": {"m1": {"rate": 1.0}}}},
                  "by_model": {"m1": {"pass_at_1": 1.0}}}
        with patch("pipeline.harden.hardenable", return_value=report):
            text = harden._breadth_summary(Path("x"), [])
        self.assertNotIn("TRAPS THAT NEVER BIT", text)
        self.assertIn("pass@1 on record for one model only: m1 1.00", text)

    def test_a_tie_between_models_is_reported_as_a_tie(self):
        from unittest.mock import patch
        from pathlib import Path
        from pipeline import harden
        report = {"checks": {"01/o": {"id": "o", "step": "01", "weight": 1,
                                      "by_model": {"m1": {"rate": 1.0}, "m2": {"rate": 1.0}}}},
                  "by_model": {"m1": {"pass_at_1": 1.0}, "m2": {"pass_at_1": 1.0}}}
        with patch("pipeline.harden.hardenable", return_value=report):
            text = harden._breadth_summary(Path("x"), [], traps=[])
        self.assertIn("BINDING MODEL: tie at pass@1 1.00 (m1, m2); harden against both", text)
        self.assertIn("none -- every trap cost some attempt a point", text)


class DeLeakRemovesTheAnalysisNeverTheMeaning(unittest.TestCase):
    """Measured 2026-09-28: the de-leak step deleted scope sentences (a-055,
    a-047) and produced ambiguity that read as a single-model pass@1 drop."""

    def test_both_prompts_say_scope_sentences_stay(self):
        from pipeline import harden
        from pipeline.author import agent_designer as a
        self.assertIn("REMOVE THE ANALYSIS, NEVER THE MEANING", harden.HARDENING_BRIEF)
        self.assertIn("is the field's MEANING and MUST STAY", harden.HARDENING_BRIEF)
        self.assertIn("(a-055, a-047)", harden.HARDENING_BRIEF)
        self.assertIn("It MUST keep every sentence that decides a field's SCOPE", a.SYSTEM)
        self.assertNotIn("threshold, rate, exception or definition that a", a.SYSTEM)

    def test_removed_scope_sentences_are_listed_and_neutral_ones_are_not(self):
        from pipeline.harden import removed_scope_sentences
        before = {"instruction": ("Report each design's restore date as `restore_date`. A design exported "
                                  "before that moment puts no date on the restore, even when it is to be "
                                  "re-exported for some other reason. Please write the report in English "
                                  "and keep it short for the team."),
                  "second_step": {"instruction": "A published chapter is ours to edit only when the "
                                                 "imprint still lists it. Thank you very much indeed."}}
        after = {"instruction": "Report each design's restore date as `restore_date`.",
                 "second_step": {"instruction": "Thank you very much indeed."}}
        flagged = removed_scope_sentences(before, after)
        self.assertEqual(len(flagged), 2, flagged)
        self.assertTrue(flagged[0].startswith("step 1: A design exported before that moment"))
        self.assertTrue(flagged[1].startswith("step 2: A published chapter is ours to edit only"))
        self.assertEqual(removed_scope_sentences(before, before), [])

    def test_reworded_but_present_sentences_are_not_flagged(self):
        from pipeline.harden import removed_scope_sentences
        before = {"instruction": "Count only invoices the finance lead approved before the cut-off."}
        after = {"instruction": "Some prose.  Count only invoices the finance   lead approved before the cut-off.\nMore."}
        self.assertEqual(removed_scope_sentences(before, after), [])


class RewordedScopeSentencesAreCountedNotListed(unittest.TestCase):
    """a-061 hardened/v2: a verbatim diff listed 66 sentences on a heavy rewrite."""

    def test_a_rephrased_scope_sentence_is_counted_as_reworded(self):
        from pipeline.harden import scope_sentence_diff, removed_scope_sentences
        before = {"instruction": ("Count only invoices the finance lead approved before the cut-off date. "
                                  "A design exported before that moment puts no date on the restore.")}
        after = {"instruction": ("Only invoices approved by the finance lead before the cut-off date are "
                                 "counted. Everything else stays as it was.")}
        diff = scope_sentence_diff(before, after)
        self.assertEqual(diff["reworded"], 1)
        self.assertEqual(len(diff["removed"]), 1)
        self.assertTrue(diff["removed"][0].startswith("step 1: A design exported before"))
        self.assertEqual(removed_scope_sentences(before, after), diff["removed"])
