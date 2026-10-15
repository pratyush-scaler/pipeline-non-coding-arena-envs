"""Exam sources retain question semantics, never private grading shortcuts."""
import unittest
from pathlib import Path
import tempfile

from pipeline.author.oracle import mcq_paper, transcript_answers
from pipeline.ledger.redaction import transform


class ExamSources(unittest.TestCase):
    def test_all_question_formats_and_duplicates_remain_observable(self):
        text = ("Exam Result\nQuestion 1 Correct\nPlain stem\nCorrect Answer:\nB. value\n"
                "**Question 1**\n**Repeated stem**\n**Correct Answer:** A. other\n"
                "### Question 8\nUnique stem\n**Correct Answer: Bhajan Shiromani**\n")
        rows = transcript_answers(text)
        self.assertEqual([r['item'] for r in rows], [1, 1, 8])
        self.assertEqual([r['stem'] for r in rows], ['Plain stem', 'Repeated stem', 'Unique stem'])
        self.assertEqual([r['stated_answer'] for r in rows], ['b', 'a', None])
        self.assertEqual(rows[2]['stated_answer_text'], 'Bhajan Shiromani')

    def test_visual_words_are_observations_not_hidden_semantic_gold(self):
        rows = mcq_paper('1. Sales agents have all values given here.\na) 1\nb) 2\nc) 3\nd) 4\n'
                         '2. The following chart gives the data.\na) 1\nb) 2\nc) 3\nd) 4\n')
        self.assertEqual(rows[0]['visual_cues'], [])
        self.assertEqual(rows[1]['visual_cues'], ['chart'])
        for row in rows:
            self.assertNotIn('figure_dependent', row)
            self.assertNotIn('verifiable', row)
            self.assertTrue(row['complete_options'])

    def test_attempt_minimization_preserves_questions_and_published_answers(self):
        source = ('**Exam Result**\r\nModel Set 42\r\nRank: 7\r\n'
                  '**Questions Answered:** 2 out of 100\r\nSubmitted: private date\r\n'
                  '**Question 1** (Incorrect, 0/1)\r\nBudget is 650.\r\n'
                  'A. 650\r\nB. 900\r\n**Correct Answer:** A. 650\r\n'
                  '**Your Answer:** B. 900\r\n'
                  'Question 2 Not answered\r\nWhat is next?\r\nCorrect Answer:\r\nD. 12\r\n'
                  'Your Answer:\r\nA. 3\r\n')
        public, edits = transform(source, ['exam-attempt-metadata'])
        self.assertEqual(transcript_answers(source), transcript_answers(public))
        self.assertIn('Captured paper size: 100\r\n', public)
        self.assertIn('Budget is 650.\r\nA. 650\r\nB. 900\r\n', public)
        for private in ('Rank:', 'private date', 'Incorrect', 'Not answered', 'Your Answer', 'A. 3'):
            self.assertNotIn(private, public)
        self.assertTrue(all(edit['kind'] == 'exam-attempt-metadata' for edit in edits))
        from pipeline.privacy import scan
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.md'
            path.write_text(source)
            self.assertEqual(scan(Path(directory))[0]['kind'], 'exam-attempt-metadata')
            path.write_text(public)
            self.assertEqual(scan(Path(directory)), [])

    def test_unknown_source_shape_cannot_erase_business_prose(self):
        for source in ('Budget 5\nQuestion 1\nMeaning',
                       'Exam Result\nModel Set 3\nQuestion 1 describes a budget\n650',
                       'Exam Result\nModel Set 3\nQuestion 1\nYour Answer:\nQuestion 2\nBusiness'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                transform(source, ['exam-attempt-metadata'])

    def test_privacy_scan_distinguishes_attempt_labels_from_question_text(self):
        from pipeline.privacy import scan
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.md'
            questions = ('Exam Result\nModel Set 42\nQuestion 1\n'
                'Find the time taken by the train.\nQuestion 2\n'
                'Time taken to cross a bridge is 11 seconds.\n')
            path.write_text(questions)
            self.assertEqual(scan(Path(directory)), [])
            for label in ('Time Taken\n11 minutes', '**Time Taken:** 11 minutes',
                          'Rank\n7', '**Your Answer:** B. 900', 'Marks Obtained: 4'):
                with self.subTest(label=label):
                    path.write_text(questions + label + '\n')
                    self.assertEqual(scan(Path(directory))[0]['kind'], 'exam-attempt-metadata')


if __name__ == '__main__':
    unittest.main()
