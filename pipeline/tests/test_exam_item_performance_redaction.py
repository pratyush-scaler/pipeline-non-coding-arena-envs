"""exam-item-performance: per-item marks a capture prints on lines of their own
are removed on explicit request, and nothing else moves (a-001/a-005 semantic
review 2026-09-29: "**Incorrect** 0/1 -0.2" under a heading, "0/1" / "-0.2"
after the response survived exam-attempt-metadata). A file that already carries
a verified redaction takes the new kind only through explicit composition."""
import unittest

from pipeline.ledger.redaction import KINDS, compose_row, sha, transform

HEADER = ("# Exam Result\nModel Set 507\n**Questions Answered:** 100 out of 100\n"
          "**Score:** 77\n\n")

HEADING_MARKS = HEADER + (
    "**Question 98** \n**Incorrect** 0/1 -0.2\nWhich country received the prize?\nOptions:\n"
    "A. China\nB. South Korea\n**Correct Answer:**\nB. South Korea\n**Your Answer:**\nA. China\n\n"
    "**Question 99** \n**Correct** 1/1\nWhich ISP is building a data center?\nOptions:\n"
    "A. Classic Tech\nB. Vianet\n**Correct Answer:**\nB. Vianet\n**Your Answer:**\nB. Vianet\n")

RESPONSE_MARKS = HEADER + (
    "**Question 96**\nWhat is the validity period of sealed quotation?\nOptions:\nA. 15 days\nB. 30 days\n"
    "**Correct Answer:**\nB. 30 days\n**Your Answer:**\nB. 30 days\n1/1\n\n"
    "**Question 97**\nThe range of carbon content in mild steel is\nOptions:\nA. less than .1%\nB. .2% to .5%\n"
    "**Correct Answer:**\nB. .2% to .5%\n**Your Answer:**\nA. less than .1%\n0/1\n-0.2\n\n"
    "**Question 98**\nHalf a tank:\n1/2 of the tank fills by 9\nOptions:\nA. 1/2\nB. 3/4\nCorrect\nB. 3/4\n"
    "**Your Answer:**\nB. 3/4\n1/1")

BOTH = ["exam-attempt-metadata", "exam-item-performance"]


class ExamItemPerformance(unittest.TestCase):
    def test_the_kind_is_registered(self):
        self.assertIn("exam-item-performance", KINDS)

    def test_a_status_and_marks_line_under_the_heading_is_removed(self):
        public, _ = transform(HEADING_MARKS, BOTH)
        self.assertNotIn("0/1", public)
        self.assertNotIn("1/1", public)
        self.assertNotIn("-0.2", public)
        self.assertNotIn("**Incorrect**", public)
        for kept in ("Which country received the prize?", "B. South Korea", "**Correct Answer:**",
                     "Which ISP is building a data center?", "**Question 98**", "**Question 99**"):
            self.assertIn(kept, public)

    def test_bare_marks_and_penalties_after_the_response_are_removed(self):
        public, _ = transform(RESPONSE_MARKS, BOTH)
        lines = public.splitlines()
        for gone in ("1/1", "0/1", "-0.2"):
            self.assertNotIn(gone, lines)
        # Question content that merely looks numeric stays: an option, a stem line,
        # and the bare "Correct" answer label a capture prints before the answer.
        for kept in ("A. 1/2", "1/2 of the tank fills by 9", "Correct", "B. .2% to .5%"):
            self.assertIn(kept, lines)

    def test_only_those_lines_differ_from_the_existing_policy(self):
        old, _ = transform(RESPONSE_MARKS, ["exam-attempt-metadata"])
        new, changes = transform(RESPONSE_MARKS, BOTH)
        self.assertEqual([line for line in old.splitlines() if line not in new.splitlines()],
                         ["1/1", "0/1", "-0.2", "1/1"])
        self.assertTrue(all(c["replacement"] == "" for c in changes if c["kind"] == "exam-item-performance"))

    def test_the_existing_kind_alone_is_unchanged(self):
        # Receipts recorded before this kind existed must replay byte-for-byte.
        public, _ = transform(RESPONSE_MARKS, ["exam-attempt-metadata"])
        self.assertIn("0/1", public.splitlines())

    def test_the_new_kind_alone_needs_question_blocks(self):
        with self.assertRaisesRegex(ValueError, "question blocks"):
            transform("no questions here\n1/1\n", ["exam-item-performance"])

    def test_composition_replays_from_the_recorded_source(self):
        old, _ = transform(RESPONSE_MARKS, ["exam-attempt-metadata"])
        row = {"path": "uploads/w07.md", "citation": "s::msg1::uploads/w07.md",
               "source_sha256": sha(RESPONSE_MARKS.encode()), "public_sha256": sha(old.encode()),
               "kinds": ["exam-attempt-metadata"]}
        public, updated = compose_row(row, RESPONSE_MARKS, ["exam-item-performance"])
        self.assertEqual(updated["kinds"], BOTH)
        self.assertEqual(updated["public_sha256"], sha(public.encode()))
        self.assertEqual(public, transform(RESPONSE_MARKS, BOTH)[0])
        self.assertEqual(row["kinds"], ["exam-attempt-metadata"])     # the old row is not mutated

    def test_composition_refuses_a_wrong_source_or_a_no_op(self):
        row = {"path": "x.md", "citation": "c", "source_sha256": sha(b"other"),
               "public_sha256": "", "kinds": ["exam-attempt-metadata"]}
        with self.assertRaisesRegex(ValueError, "differs from the recorded source"):
            compose_row(row, RESPONSE_MARKS, ["exam-item-performance"])
        row["source_sha256"] = sha(RESPONSE_MARKS.encode())
        with self.assertRaisesRegex(ValueError, "adds no redaction kind"):
            compose_row(row, RESPONSE_MARKS, ["exam-attempt-metadata"])


if __name__ == "__main__":
    unittest.main()
