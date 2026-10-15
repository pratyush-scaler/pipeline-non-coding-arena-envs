"""Tests for trace_traps.py on synthetic sessions (no dump, no network).

Run from production/tools:  python3 -I -m unittest test_trace_traps
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parents[1]):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import trace_traps as tt  # noqa: E402

#: Every fixture message carries one of these tokens; none may appear in any output.
MARK = "qzmark"


def make_trace(sid, turns, categories=("document_creation",), lang="en", undone=()):
    """turns: list of (role, text). Each text gets a unique raw-text marker appended."""
    messages, user_nodes = [], []
    for i, (role, text) in enumerate(turns):
        node = f"{sid}-n{i}"
        messages.append({"role": role, "node_ids": [node], "undone": i in undone,
                         "content": [{"type": "text", "text": f"{text} {MARK}{i}x"}]})
        if role == "user":
            user_nodes.append(node)
    return {"session_id": sid, "title": f"title {MARK}t", "model_name": "fixture-model", "messages": messages,
            "metadata": {"categories": list(categories), "language_counts": {"user": {lang: len(user_nodes), "zxx": 1}}},
            "tasks": [{"task_index": 0, "task_key": f"{sid}::0", "turn_ids": user_nodes, "n_turns": len(user_nodes)}]}


def outcomes_for(sid, user_msg_indexes, signal="steerability"):
    return {"outcomes": [{"session_id": sid, "signal_name": signal, "outcome": "failure",
                          "annotating_node_id": f"{sid}-n{i}", "terminal_node_id": f"{sid}-n{i}"}
                         for i in user_msg_indexes]}


def session(turns, outcome_msgs=(), **kw):
    trace = make_trace("s-fixture", turns, **kw)
    return tt.session_from_trace(trace, outcomes_for("s-fixture", outcome_msgs))


def three_turns(prev_assistant, user, reply="Noted, revising now."):
    """A first exchange, then the user turn under test (user ordinal 2), then the reply."""
    return [("user", "Please prepare the quarterly summary from the attached files."),
            ("assistant", prev_assistant), ("user", user), ("assistant", reply)]


def signals_of(sess):
    return tt.detect(sess)


def best(sigs, category, subkind=None):
    xs = [s for s in sigs if s.category == category and (subkind is None or s.subkind == subkind)]
    return max(xs, key=lambda s: s.strength) if xs else None


class Categories(unittest.TestCase):
    """One strong case per heuristic category, plus multilingual and negative cases."""

    def strong(self, turns, category, subkind=None, outcome_msgs=()):
        sig = best(signals_of(session(turns, outcome_msgs)), category, subkind)
        self.assertIsNotNone(sig, f"no {category} signal")
        self.assertGreaterEqual(sig.strength, tt.STRONG, f"{category} too weak: {sig.strength}")
        return sig

    def test_user_correction(self):
        sig = self.strong(three_turns("The total is 520.", "That's wrong, the total should be 450."), "user_correction")
        self.assertEqual(sig.variant, "record")
        self.assertEqual(sig.turn, 2)
        self.assertEqual(sig.user_turn, 2)

    def test_requirement_change(self):
        self.strong(three_turns("Draft attached.", "Actually, the client now wants the budget changed to 40,000 in the report."),
                    "requirement_change")

    def test_document_conflict(self):
        self.strong(three_turns("Payment is due in 45 days.", "Your summary contradicts the attached contract, which says 30 days."),
                    "document_conflict")

    def test_misattribution(self):
        self.strong(three_turns("Courier charge booked to Orion.",
                                "You mixed up the two invoices: the courier charge belongs to Delta, not Orion."), "misattribution")

    def test_unit_or_basis(self):
        self.strong(three_turns("Net cost computed from list prices.",
                                "That's wrong, those prices are VAT-inclusive so the net amount is lower."), "unit_or_basis")

    def test_convention_rounding(self):
        self.strong(three_turns("Shares: 41.9 and 43.9.", "The shares are wrong; truncate to one decimal place like the guide."),
                    "convention", "rounding")

    def test_convention_aggregation(self):
        self.strong(three_turns("September revenue rose 1.2m.", "That's wrong: the export is year-to-date, not the monthly change."),
                    "convention", "aggregation")

    def test_edition(self):
        self.strong(three_turns("Priced at the current rates.", "That's wrong, you used the old rate card; the 2025 version applies."),
                    "edition_or_date", "edition")

    def test_fiscal(self):
        self.strong(three_turns("Q1 covers January to March.", "That's wrong, their fiscal year starts in April, so their Q1 is our Q2."),
                    "edition_or_date", "fiscal")

    def test_period_start(self):
        self.strong(three_turns("The deadline is 14 days after the letter date.",
                                "Wrong date: the notice period runs from the date of receipt, not the letter date."),
                    "edition_or_date", "period_start")

    def test_possession(self):
        self.strong(three_turns("Shopping list: multimeter, solder, flux.", "I already have the multimeter, so drop it."), "possession")

    def test_rule_shield(self):
        sig = self.strong(three_turns("According to the policy, section 4 requires excluding late entries, so I left them out.",
                                      "That rule doesn't apply here; section 4 is only about the gain score."), "rule_shield")
        self.assertEqual(sig.refs, [1])
        self.assertEqual(sig.variant, "cited")

    def test_assistant_error_caught(self):
        sess = session(three_turns("The total is 520.", "That's wrong, the total should be 450.",
                                   reply="You're right, I misread the table. The total is 450."))
        sig = best(signals_of(sess), "assistant_error_caught")
        self.assertIsNotNone(sig)
        self.assertEqual(sig.role, "assistant")
        self.assertEqual(sig.turn, 3)
        self.assertGreaterEqual(sig.strength, tt.STRONG)
        corr = best(signals_of(sess), "user_correction")
        self.assertIn("concede", corr.cues)

    def test_refusal_is_not_a_concession(self):
        sess = session(three_turns("Here it is.", "That's wrong, fix it.", reply="I apologize, but I can't access that file."))
        self.assertIsNone(best(signals_of(sess), "assistant_error_caught"))

    # --- multilingual
    def test_russian_correction(self):
        self.strong(three_turns("Итого 520.", "Это неправильно, сумма должна быть 450."), "user_correction")

    def test_persian_correction_with_persian_digits(self):
        sig = self.strong(three_turns("مبلغ ۵۲۰ است", "اشتباه است، مبلغ ۴۵۰ است"), "user_correction")
        self.assertIn("figure", tt.make_paraphrase(sig.category, sig.variant, sig.feats))

    def test_chinese_correction_and_self_reference(self):
        self.strong(three_turns("共九个章节。", "不对，应该是12个章节"), "user_correction")
        sig = best(signals_of(session(three_turns("好的。", "我写不对代码"))), "user_correction")
        self.assertTrue(sig is None or sig.strength < tt.STRONG)

    def test_spanish_possession(self):
        self.strong(three_turns("Lista: impresora, papel.", "Está mal, ya tengo la impresora."), "possession")

    def test_arabic_unit_basis_with_correction(self):
        self.strong(three_turns("السعر 100", "غير صحيح، السعر شامل الضريبة"), "unit_or_basis")

    # --- negatives and context penalties
    def test_first_turn_is_never_a_correction(self):
        sigs = signals_of(session([("user", "That's wrong in my old notes; build the plan."), ("assistant", "Plan attached.")]))
        self.assertIsNone(best(sigs, "user_correction"))

    def test_infra_complaint_is_not_strong(self):
        sig = best(signals_of(session(three_turns("Download the zip.", "That's wrong, I can't download the zip file."))), "user_correction")
        self.assertLess(sig.strength, tt.STRONG)

    def test_aesthetic_complaint_is_not_strong(self):
        sig = best(signals_of(session(three_turns("Poster ready.", "That's wrong, make the font bigger."))), "user_correction")
        self.assertLess(sig.strength, tt.STRONG)

    def test_cue_inside_pasted_material_is_discounted(self):
        filler = " ".join(["The committee met and reviewed the minutes of the previous meeting."] * 8)
        pasted = filler + " That's wrong, the total should be 450. " + filler
        sig = best(signals_of(session(three_turns("Summary sent.", pasted))), "user_correction")
        self.assertTrue(sig is None or sig.strength < tt.STRONG)

    def test_outcome_label_without_cue_is_weak(self):
        sig = best(signals_of(session(three_turns("Draft sent.", "Make it shorter please."), outcome_msgs=[2])), "user_correction")
        self.assertEqual(sig.cues, ["outcome_only"])
        self.assertLess(sig.strength, tt.STRONG)

    def test_outcome_label_boosts_a_lexical_cue(self):
        plain = best(signals_of(session(three_turns("x", "Are you sure? check again"))), "user_correction")
        labelled = best(signals_of(session(three_turns("x", "Are you sure? check again"), outcome_msgs=[2])), "user_correction")
        self.assertGreater(labelled.strength, plain.strength)

    def test_undone_turns_are_skipped(self):
        trace = make_trace("s-undo", three_turns("Total 520.", "That's wrong, the total should be 450."), undone=(2,))
        sess = tt.session_from_trace(trace, None)
        self.assertEqual(sess.undone_skipped, 1)
        self.assertIsNone(best(tt.detect(sess), "user_correction"))


class Scoring(unittest.TestCase):
    def test_two_independent_signals_and_mid_session_change(self):
        turns = [("user", "Build the cost register from the invoices."), ("assistant", "Register ready."),
                 ("user", "That's wrong, the total should be 450."), ("assistant", "Fixed."),
                 ("user", "Thanks. Next add the supplier column."), ("assistant", "Added."),
                 ("user", "Actually, the client now wants the budget changed to 40,000 in the report."), ("assistant", "Updated."),
                 ("user", "Good, export it.")]
        doc = tt.analyse(session(turns), tt.Library())
        tr = doc["trap_rich"]
        self.assertGreaterEqual(tr["independent_strong"], 2)
        self.assertTrue(tr["mid_session_premise_change"])
        single = tt.analyse(session(three_turns("x", "That's wrong, the total should be 450.")), tt.Library())
        self.assertGreater(tr["score"], single["trap_rich"]["score"])

    def test_same_turn_two_categories_is_one_moment(self):
        doc = tt.analyse(session(three_turns("x", "That's wrong, those prices are VAT-inclusive so the net amount is lower.")),
                         tt.Library())
        self.assertGreaterEqual(doc["trap_rich"]["events"], 2)
        self.assertEqual(doc["trap_rich"]["independent_strong"], 1)

    def test_non_knowledge_work_session_is_discounted(self):
        turns = three_turns("x", "That's wrong, the total should be 450.")
        kw = tt.analyse(session(turns), tt.Library())["trap_rich"]["score"]
        img = tt.analyse(session(turns, categories=("image_video_generation",)), tt.Library())["trap_rich"]["score"]
        self.assertAlmostEqual(img, kw / 2, places=3)


def write_library(directory: Path, internal_modes=None, extra=None):
    directory.mkdir(parents=True, exist_ok=True)
    if internal_modes is not None:
        (directory / "modes-internal.json").write_text(json.dumps(
            {"schema": "traplib/1", "source": "internal", "generated": "2026-10-15T20:00+05:30", "modes": internal_modes}))
    for name, body in (extra or {}).items():
        (directory / name).write_text(body)


LIB_MODES = [
    {"id": "T4", "status": "promising", "family": "possession_state", "name": "Already in hand",
     "trace_signals": ["the user says 'I already have that' after a list is drafted"]},
    {"id": "R7", "status": "trace-derived", "family": "quantity_basis", "name": "Currency basis",
     "trace_signals": ["the user corrects the currency or unit a figure is stated in"]},
    {"id": "D9", "status": "dead", "family": "possession_state", "name": "Dead possession variant",
     "trace_signals": ["possession: the user already has it"]},
]


class Mapping(unittest.TestCase):
    def test_fallback_without_library(self):
        lib = tt.Library()
        self.assertEqual(tt.map_signal("possession", None, lib), (["T4"], "fallback"))
        self.assertEqual(tt.map_signal("unit_or_basis", None, lib), (["T3"], "fallback"))
        self.assertEqual(tt.map_signal("rule_shield", None, lib), (["T9"], "fallback"))
        self.assertEqual(tt.map_signal("edition_or_date", "fiscal", lib), (["L4"], "fallback"))
        self.assertEqual(tt.map_signal("convention", "rounding", lib), (["T2", "T7"], "fallback"))
        self.assertEqual(tt.map_signal("user_correction", None, lib), ([], "none"))
        self.assertEqual(tt.map_signal("user_correction", "record", lib), (["T1"], "fallback"))

    def test_missing_library_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = tt.load_library(Path(tmp) / "absent")
            self.assertFalse(lib.present)
            self.assertEqual(lib.files, [])

    def test_library_trace_signals_drive_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "traps"
            write_library(d, LIB_MODES, {
                "modes-curated.json": json.dumps({"schema": "traplib-curated/1", "modes": []}),
                "modes-external.json": "{not json",
            })
            lib = tt.load_library(d)
            self.assertEqual(lib.files, ["modes-internal.json"])
            self.assertEqual(lib.skipped, ["modes-curated.json"])
            self.assertEqual([e["file"] for e in lib.errors], ["modes-external.json"])
            ids, source = tt.map_signal("possession", None, lib)
            self.assertEqual(source, "library")
            self.assertIn("T4", ids)
            self.assertNotIn("D9", ids, "dead modes are never proposed")
            self.assertEqual(tt.map_signal("unit_or_basis", None, lib), (["R7"], "library"))
            # no library mode carries rule-scope trace signals: fall back to the built-in map
            self.assertEqual(tt.map_signal("rule_shield", None, lib), (["T9"], "fallback"))

    def test_fallback_drops_ids_the_library_marks_dead(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "traps"
            write_library(d, [{"id": "T3", "status": "dead", "family": "quantity_basis", "name": "x",
                               "trace_signals": ["nothing relevant here"]}])
            self.assertEqual(tt.map_signal("unit_or_basis", None, tt.load_library(d)), ([], "none"))

    def test_real_library_files_when_present(self):
        lib = tt.load_library(tt.DEFAULT_LIBRARY)
        if not lib.present:
            self.skipTest("no modes-*.json in production/traps yet")
        self.assertEqual(lib.errors, [])
        for cat in tt.CATEGORIES:
            ids, source = tt.map_signal(cat, None, lib)
            self.assertIn(source, ("library", "fallback", "none"))
            for i in ids:
                self.assertNotEqual(lib.modes.get(i, {}).get("status"), "dead")


class NoRawText(unittest.TestCase):
    def test_raw_overlap_detects_copied_words(self):
        text = tt.norm("the courier charge belongs to delta and not to orion at all")
        words = " ".join(tt._words(text))
        self.assertTrue(tt.raw_overlap("note: the courier charge belongs to delta here", words, text))
        self.assertFalse(tt.raw_overlap("User says an item was keyed to the wrong owner.", words, text))
        rtext = tt.norm("Это неправильно сумма должна быть")
        self.assertTrue(tt.raw_overlap("quote неправильно", " ".join(tt._words(rtext)), rtext))

    def test_safe_paraphrase_falls_back_and_clips(self):
        text = tt.norm("the courier charge belongs to delta and not to orion")
        words = " ".join(tt._words(text))
        self.assertEqual(tt.safe_paraphrase("the courier charge belongs to delta", "misattribution", 4, words, text),
                         "misattribution signal at message 4.")
        long = " ".join(f"w{i}" for i in range(40))
        self.assertLessEqual(len(tt.safe_paraphrase(long, "x", 1, words, text).split()), tt.MAX_PARAPHRASE_WORDS)

    def test_every_template_is_short(self):
        for (cat, variant) in tt.TEMPLATES:
            p = tt.make_paraphrase(cat, variant, {"value": True, "concede": True, "after_correction": True})
            self.assertLessEqual(len(p.split()), tt.MAX_PARAPHRASE_WORDS, (cat, variant, p))

    def test_scan_and_report_outputs_carry_no_raw_text(self):
        turns = [("user", "Build the cost register from the courier invoices."), ("assistant", "According to the policy, section 4 applies."),
                 ("user", "That rule doesn't apply here; section 4 is only about the gain."), ("assistant", "You're right, my mistake."),
                 ("user", "That's wrong, the total should be 450 and the prices are VAT-inclusive."), ("assistant", "Fixed."),
                 ("user", "Actually, the client now wants the budget changed to 40,000 in the report."), ("assistant", "Updated."),
                 ("user", "I already have the multimeter. You mixed up the two invoices.")]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dump" / "sessions"
            sid = "01fixture-0000"
            (root / sid).mkdir(parents=True)
            (root / sid / "data.json").write_text(json.dumps({"metadata": {}, "traces": [make_trace(sid, turns)]}))
            (root / sid / "outcomes.json").write_text(json.dumps(outcomes_for(sid, [4])))
            ids = Path(tmp) / "ids.json"
            ids.write_text(json.dumps({"session_ids": [sid, "missing-session", "../escape"]}))
            used = Path(tmp) / "used.txt"
            used.write_text("already-used\n")
            out = Path(tmp) / "out"
            lib = Path(tmp) / "nolib"
            with redirect_stdout(io.StringIO()):
                tt.main(["scan", "--list", str(ids), "--exclude", str(used), "--dump", str(root.parent),
                         "--out", str(out), "--library", str(lib)])
                tt.main(["report", str(out), "-o", str(Path(tmp) / "report.md")])
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["scanned"], 1)
            self.assertEqual(summary["mode"], "deterministic", "--llm is off by default")
            self.assertEqual({e["session_id"] for e in summary["errors"]}, {"missing-session", "../escape"})
            doc = json.loads((out / "sessions" / f"{sid}.json").read_text())
            cats = {s["category"] for s in doc["signals"] if s["strong"]}
            self.assertTrue({"rule_shield", "user_correction", "requirement_change", "possession"} <= cats, cats)
            self.assertTrue(all(s["mapping_source"] in ("fallback", "none") for s in doc["signals"]))
            for s in doc["signals"]:
                self.assertLessEqual(len(s["paraphrase"].split()), tt.MAX_PARAPHRASE_WORDS)
            blobs = [p.read_text() for p in out.rglob("*.json")] + [(Path(tmp) / "report.md").read_text()]
            for blob in blobs:
                self.assertNotIn(MARK, blob, "a raw trace marker leaked into an output file")
                for phrase in ("courier invoices", "only about the gain", "budget changed to 40,000", "mixed up the two"):
                    self.assertNotIn(phrase, blob)
            self.assertIn(sid, (Path(tmp) / "report.md").read_text())


class ListsAndLLM(unittest.TestCase):
    def test_read_id_list_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.json"
            a.write_text(json.dumps(["s1", "s2"]))
            b = Path(tmp) / "b.json"
            b.write_text(json.dumps({"seeds": [{"session_id": "s3"}]}))
            c = Path(tmp) / "c.txt"
            c.write_text("s4\n\n# comment\ns5")
            self.assertEqual(tt.read_id_list(str(a)), ["s1", "s2"])
            self.assertEqual(tt.read_id_list(str(b)), ["s3"])
            self.assertEqual(tt.read_id_list(str(c)), ["s4", "s5"])

    def test_llm_refine_validates_and_guards_paraphrases(self):
        sess = session(three_turns("The total is 520.", "That's wrong, the total should be 450 for Delta."))
        heur = tt.detect(sess)
        calls = []

        def fake_call(body):
            calls.append(body)
            self.assertEqual(body["tool_choice"], {"type": "tool", "name": "record_signals"})
            self.assertNotIn("temperature", body)
            return {"content": [{"type": "tool_use", "name": "record_signals", "input": {"signals": [
                {"turn": 2, "category": "user_correction", "strength": 0.9,
                 "paraphrase": "the total should be 450 for delta"},           # raw copy -> replaced
                {"turn": 2, "category": "not_a_category", "strength": 0.5, "paraphrase": "x"},   # invalid -> rejected
                {"turn": 99, "category": "possession", "strength": 0.5, "paraphrase": "y"},      # not a candidate -> rejected
                {"turn": 2, "category": "convention", "strength": 0.7, "paraphrase": "User disputes how a total was rounded."},
            ]}}]}

        doc = tt.analyse(sess, tt.Library(), llm_call=fake_call, use_llm=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(doc["mode"], "llm")
        self.assertEqual(doc["llm"]["rejected_invalid"], 2)
        by_cat = {s["category"]: s for s in doc["signals"]}
        self.assertEqual(by_cat["user_correction"]["paraphrase"], "user correction signal at message 2.")
        self.assertEqual(by_cat["convention"]["paraphrase"], "User disputes how a total was rounded.")
        self.assertTrue(heur)

    def test_llm_refine_requires_one_tool_call(self):
        sess = session(three_turns("x", "That's wrong, the total should be 450."))
        with self.assertRaises(RuntimeError):
            tt.llm_refine(sess, tt.detect(sess), call=lambda body: {"content": [{"type": "text", "text": "no"}]}, model="m")


if __name__ == "__main__":
    unittest.main()
