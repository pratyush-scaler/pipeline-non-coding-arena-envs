"""person-name-example: a recovered design document's worked examples keep a
real person's name that the dump's redaction replaced in prose; on explicit
request that name, and only it, becomes the file's placeholder (a-001, semantic
review 2026-09-28)."""
import unittest

from pipeline.ledger.redaction import KINDS, transform

KIND = "person-name-example"


class PersonNameExample(unittest.TestCase):
    def test_example_values_and_their_mentions_become_the_files_placeholder(self):
        source = ('جملة "توفيت [PERSON_NAME_1] سنة 2019"\n'
                  '   → FamilyGraph: يُخزَّن (عمة → عائشة) بدون أي تاريخ وفاة\n'
                  '    person_name    TEXT    NOT NULL,        -- "عائشة"\n'
                  '{person: "عائشة", event_type: "death"}\n'
                  "WHERE person_name='عائشة' AND event_type='death'\n"
                  '"معلومة مؤكدة: تُوفيت عائشة (عمة المستخدم) في 2019."\n')
        public = ('جملة "توفيت [PERSON_NAME_1] سنة 2019"\n'
                  '   → FamilyGraph: يُخزَّن (عمة → [PERSON_NAME_1]) بدون أي تاريخ وفاة\n'
                  '    person_name    TEXT    NOT NULL,        -- "[PERSON_NAME_1]"\n'
                  '{person: "[PERSON_NAME_1]", event_type: "death"}\n'
                  "WHERE person_name='[PERSON_NAME_1]' AND event_type='death'\n"
                  '"معلومة مؤكدة: تُوفيت [PERSON_NAME_1] (عمة المستخدم) في 2019."\n')
        self.assertIn(KIND, KINDS)
        self.assertEqual(transform(source, [KIND])[0], public)

    def test_a_file_without_a_placeholder_gets_the_generic_one(self):
        self.assertEqual(transform('"person_name": "Jane Roe" or None, Jane Roe', [KIND])[0],
                         '"person_name": "[PERSON_NAME]" or None, [PERSON_NAME]')

    def test_only_whole_words_move(self):
        text = '"person_name": "Ann"\nAnna and Ann and Annex\n'
        self.assertEqual(transform(text, [KIND])[0],
                         '"person_name": "[PERSON_NAME]"\nAnna and [PERSON_NAME] and Annex\n')

    def test_placeholders_nulls_and_non_names_are_not_examples(self):
        for text in ('"person_name": "[PERSON_NAME_1]"', '"person_name": "None"',
                     '"person_name": "..."', '"person_name": "x_1"', 'the person said "hello"'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "no supported private data"):
                transform(text, [KIND])

    def test_the_transform_is_a_pure_function_of_content(self):
        text = '"person": "عائشة"\nتوفيت عائشة\n'
        self.assertEqual(transform(text, [KIND]), transform(text, [KIND]))


if __name__ == "__main__":
    unittest.main()
