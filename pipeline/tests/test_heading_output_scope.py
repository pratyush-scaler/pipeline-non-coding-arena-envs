from __future__ import annotations

import unittest

from pipeline.author.designer import _target_reads_headings


class HeadingOutputScopeTests(unittest.TestCase):
    def setUp(self):
        self.heading = {"op": "field", "path": "heading"}
        self.sections = {"op": "rows", "file": "sections.jsonl"}

    def test_direct_heading_set_still_requires_scope(self):
        self.assertTrue(_target_reads_headings({"op": "pluck", "field": "heading", "of": self.sections}))

    def test_heading_set_difference_still_requires_scope(self):
        headings = {"op": "pluck", "field": "heading", "of": self.sections}
        self.assertTrue(_target_reads_headings({"op": "difference", "a": headings, "b": headings}))

    def test_direct_heading_count_still_requires_scope(self):
        headings = {"op": "pluck", "field": "heading", "of": self.sections}
        self.assertTrue(_target_reads_headings({"op": "count", "of": headings}))

    def test_renamed_heading_column_still_requires_scope(self):
        rows = {"op": "derive_rows", "of": self.sections, "fields": {"label": self.heading}}
        self.assertTrue(_target_reads_headings({"op": "pluck", "field": "label", "of": rows}))

    def test_selected_heading_column_still_requires_scope(self):
        rows = {"op": "select", "of": self.sections, "fields": {"label": "heading"}}
        self.assertTrue(_target_reads_headings({"op": "pluck", "field": "label", "of": rows}))

    def test_nested_record_returning_headings_still_requires_scope(self):
        self.assertTrue(_target_reads_headings({"op": "record", "fields": {"report": self.heading}}))

    def test_batch_identifier_extraction_is_not_a_heading_report(self):
        code = {"op": "extract", "pattern": "(T[0-9]+)", "group": 1, "of": self.heading}
        rows = {"op": "derive_rows", "of": self.sections, "fields": {"code": code, "heading": self.heading}}
        self.assertFalse(_target_reads_headings({"op": "pluck", "field": "code", "of": rows}))

    def test_full_heading_extraction_still_requires_scope(self):
        for pattern in ("(.+)", "(.*?)", r"([^\n]+)"):
            with self.subTest(pattern=pattern):
                self.assertTrue(_target_reads_headings({"op": "extract", "pattern": pattern,
                                                       "group": 1, "of": self.heading}))

    def test_condition_reading_a_heading_does_not_turn_a_number_into_a_heading_report(self):
        expression = {"op": "if", "where": {"op": "compare", "a": self.heading},
                      "then": {"op": "literal", "value": 1}, "else": {"op": "literal", "value": 0}}
        self.assertFalse(_target_reads_headings(expression))

    def test_unused_heading_binding_does_not_affect_a_selected_quantity(self):
        rows = {"op": "bind_rows", "of": self.sections,
                "fields": {"heading": self.heading, "quantity": {"op": "field", "path": "quantity"}}}
        self.assertFalse(_target_reads_headings({"op": "pluck", "field": "quantity", "of": rows}))

    def test_heading_words_in_a_literal_are_not_source_heading_reads(self):
        self.assertFalse(_target_reads_headings({"op": "literal", "value": "heading"}))


if __name__ == '__main__':
    unittest.main()
