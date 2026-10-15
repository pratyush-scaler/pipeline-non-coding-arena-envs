"""Arena 261011 output-contract defects, kept closed (2026-10-12).

R24/R30/R31/R19: a uniqueness rule compared raw JSON text, so 91 and 91.0, or
two spellings differing only in letter case, passed as two entries and then
collapsed into one answer when the set was scored. R25: a FIFO escaped the
extra-deliverable guard (and a FIFO at a declared path blocked the reader).
R23: deeply nested JSON raised RecursionError past the invalid-output handler.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from pipeline.author.contracts import (MAX_JSON_DEPTH, ContractError, schema_errors, strict_json,
                                       submission_errors)

SCHEMA = {"type": "object", "required": ["ids", "names"], "additionalProperties": False,
          "properties": {"ids": {"type": "array", "uniqueItems": True, "items": {"type": "integer"}},
                         "names": {"type": "array", "uniqueItems": True, "items": {"type": "string"}}}}
OUTPUTS = [{"file": "answer.json", "step": "01-task", "schema": SCHEMA}]


class Uniqueness(unittest.TestCase):
    def test_integer_and_decimal_spelling_are_one_entry(self):
        errors = schema_errors({"ids": [91, 91.0], "names": []}, SCHEMA)
        self.assertTrue(any("repeated" in e for e in errors), errors)

    def test_case_variants_are_one_entry(self):
        errors = schema_errors({"ids": [], "names": ["Mira Holt", "mira  holt"]}, SCHEMA)
        self.assertTrue(any("repeated" in e for e in errors), errors)

    def test_distinct_entries_pass(self):
        self.assertEqual(schema_errors({"ids": [91, 92], "names": ["a", "b"]}, SCHEMA), [])

    def test_boolean_is_not_one(self):
        schema = {"type": "array", "uniqueItems": True, "items": {"type": ["boolean", "null"]}}
        self.assertEqual(schema_errors([True, None], schema), [])


class Depth(unittest.TestCase):
    def test_parser_recursion_is_a_contract_error(self):
        with self.assertRaises(ContractError):
            strict_json("[" * 5000 + "]" * 5000)

    def test_depth_bound(self):
        with self.assertRaises(ContractError):
            strict_json("[" * (MAX_JSON_DEPTH + 1) + "]" * (MAX_JSON_DEPTH + 1))
        self.assertEqual(strict_json("[" * MAX_JSON_DEPTH + "]" * MAX_JSON_DEPTH)[0:0], [])


class Inventory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "answer.json").write_text(json.dumps({"ids": [1], "names": ["a"]}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_submission(self):
        self.assertEqual(submission_errors(self.root, OUTPUTS, "01-task"), [])

    def test_extra_fifo_is_refused(self):
        os.mkfifo(self.root / "extra.pipe")
        errors = submission_errors(self.root, OUTPUTS, "01-task")
        self.assertTrue(any(e.startswith("extra.pipe:") for e in errors), errors)

    def test_declared_fifo_is_refused_without_blocking(self):
        (self.root / "answer.json").unlink()
        os.mkfifo(self.root / "answer.json")
        result = {}
        worker = threading.Thread(target=lambda: result.update(e=submission_errors(self.root, OUTPUTS, "01-task")),
                                  daemon=True)
        worker.start()
        worker.join(10)
        self.assertFalse(worker.is_alive(), "submission_errors blocked on a FIFO")
        self.assertTrue(any("regular file" in e for e in result["e"]), result["e"])

    def test_deep_json_deliverable_is_a_contract_error(self):
        (self.root / "answer.json").write_text("[" * 5000 + "]" * 5000)
        errors = submission_errors(self.root, OUTPUTS, "01-task")
        self.assertTrue(any("nested deeper" in e for e in errors), errors)


class PatternEndAnchor(unittest.TestCase):
    """JSON Schema patterns follow ECMA-262: `$` is the end of the text, never 'before a final newline'."""
    SCHEMA = {"type": "string", "pattern": "^C-[0-9]{3}$"}

    def test_trailing_newline_fails(self):
        self.assertTrue(schema_errors("C-103\n", self.SCHEMA))

    def test_exact_value_passes(self):
        self.assertEqual(schema_errors("C-103", self.SCHEMA), [])

    def test_escaped_dollar_and_class_untouched(self):
        self.assertEqual(schema_errors("$5", {"type": "string", "pattern": "^\\$[0-9]$"}), [])
        self.assertEqual(schema_errors("a$", {"type": "string", "pattern": "^a[$]$"}), [])


class ReadGuard(unittest.TestCase):
    def test_oversized_submission_is_a_failed_read(self):
        from pipeline.author import checks
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            big = root / "answer.json"
            with open(big, "wb") as handle:
                handle.truncate(checks.MAX_DELIVERABLE_BYTES + 1)
            ws = checks.Workspace(source=root, submitted=root)
            with self.assertRaises(checks.SubmissionInvalid):
                ws.read("answer.json", "submitted")


class LongInputs(unittest.TestCase):
    """Stage 3: no crash past the int-digit limit, no quadratic normalisation regex."""

    def test_huge_numeric_string_in_unique_list_does_not_crash(self):
        schema = {"type": "array", "uniqueItems": True, "items": {"type": "string"}}
        self.assertEqual(schema_errors(["1" * 5000, "a"], schema), [])

    def test_normalise_is_linear_on_long_runs(self):
        import time
        from pipeline.author.checks import normalise
        start = time.time()
        normalise(" " * 2_000_000 + "x")
        normalise("1 " * 1_000_000 + "x")
        self.assertLess(time.time() - start, 5.0)

    def test_trailing_hashes_still_stripped(self):
        from pipeline.author.checks import normalise
        self.assertEqual(normalise("Results ##"), "results")
        self.assertEqual(normalise("C# basics"), "c# basics")


class PublishedContractText(unittest.TestCase):
    """The published contract text must carry no example value that could coincide with a graded one."""

    def test_uniqueness_sentence_names_no_number(self):
        import re
        from pipeline.author.contracts import public_contract
        text = public_contract(OUTPUTS, "01-task")
        sentence = text[text.index("A list that must not repeat"):].split("\n", 1)[0]
        self.assertIsNone(re.search(r"\d", sentence), sentence)


if __name__ == "__main__":
    unittest.main()
