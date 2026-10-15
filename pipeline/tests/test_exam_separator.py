"""Known attempt-status separators must not hide or erase question content."""
from pathlib import Path
import tempfile
import unittest

from pipeline.author.oracle import transcript_answers
from pipeline.ledger.redaction import transform
from pipeline.privacy import scan


class ExamStatusSeparators(unittest.TestCase):
    def test_pipe_separated_statuses_preserve_published_question_and_answer(self):
        for newline in ("\n", "\r\n"):
            for status in ("Incorrect | Flagged", "Correct | Flagged"):
                with self.subTest(newline=repr(newline), status=status):
                    source = newline.join([
                        "**Exam Result**", "Model Set 42", "Rank: 7",
                        "**Questions Answered:** 1 out of 100",
                        f"### Question 1 ({status}, 0/1)",
                        "Which symbol means logical OR: A | B?",
                        "A. A | B", "B. A & B", "**Correct Answer:** A. A | B",
                        "**Your Answer:** B. A & B", "",
                    ])
                    public, edits = transform(source, ["exam-attempt-metadata"])
                    self.assertEqual(transcript_answers(source), transcript_answers(public))
                    self.assertIn(newline.join([
                        "Which symbol means logical OR: A | B?",
                        "A. A | B", "B. A & B", "**Correct Answer:** A. A | B",
                    ]), public)
                    self.assertIn("Captured paper size: 100" + newline, public)
                    self.assertIn("### Question 1" + newline, public)
                    for private in (status, "Rank:", "Your Answer:"):
                        self.assertNotIn(private, public)
                    self.assertTrue(edits)
                    with tempfile.TemporaryDirectory() as temp:
                        fixture = Path(temp)
                        (fixture / "capture.md").write_bytes(public.encode())
                        self.assertEqual(scan(fixture), [])

    def test_pipe_does_not_authorize_removing_substantive_heading_text(self):
        for heading in (
            "Question 1 Correct | What is the budget?",
            "Question 1 Incorrect | Flagged | Explain the variance",
            "Question 1 | A or B?",
            "Question 1 | 100",
            "Question 1 Correct | 100",
            "Question 1 | Correct",
        ):
            with self.subTest(heading=heading):
                source = "Exam Result\nModel Set 42\nRank: 7\n" + heading + "\nBusiness facts\n"
                with self.assertRaisesRegex(ValueError, "unrecognized question heading"):
                    transform(source, ["exam-attempt-metadata"])


if __name__ == "__main__":
    unittest.main()
