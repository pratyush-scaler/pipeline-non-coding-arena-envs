"""course-lecturer-name: a recovered handout's lecturer is pseudonymised on
explicit request, and nothing but the name moves (a-067, review 2026-09-27)."""
import unittest

from pipeline.ledger.redaction import KINDS, transform


class LecturerName(unittest.TestCase):
    def test_the_name_after_a_lecturer_label_becomes_a_role_placeholder(self):
        cases = {
            "محاضر المادة/د.مجدي علي غيث\nأھمية": "محاضر المادة/د.[اسم المحاضر]\nأھمية",
            "(محاضر المادة: د. مجدي علي غيث).": "(محاضر المادة: د. [اسم المحاضر]).",
            "أستاذ المادة - الدكتور سامي": "أستاذ المادة - الدكتور [اسم المحاضر]",
            "Lecturer: Dr. Jane Q Smith, room 4": "Lecturer: Dr. [lecturer name], room 4",
            "Course instructor / Prof. Ada": "Course instructor / Prof. [lecturer name]",
        }
        self.assertIn("course-lecturer-name", KINDS)
        for source, public in cases.items():
            with self.subTest(source=source):
                self.assertEqual(transform(source, ["course-lecturer-name"])[0], public)

    def test_an_unlabelled_name_is_not_touched_and_the_policy_refuses(self):
        with self.assertRaisesRegex(ValueError, "no supported private data"):
            transform("Dr. Smith wrote this chapter", ["course-lecturer-name"])

    def test_the_transform_is_a_pure_function_of_content(self):
        text = "محاضر المادة/د.مجدي علي غيث\n"
        self.assertEqual(transform(text, ["course-lecturer-name"]),
                         transform(text, ["course-lecturer-name"]))


if __name__ == "__main__":
    unittest.main()
