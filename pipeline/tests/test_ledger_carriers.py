"""Arena 261011 (R20/R26/R32): several fixture files carrying one session file get declared roles."""
from __future__ import annotations

import unittest

from pipeline.ledger.faithfulness import CARRIER_POLICY, Entry, carriers, measured_fields

S = "01a0-trace"


def entry(path, sha, msg, src="/home/user/plan.md", origin="lifted", similarity=1.0):
    return Entry(path, origin, sha, 10, citation=f"{S}::msg{msg}::{src}", similarity=similarity)


class Carriers(unittest.TestCase):
    def test_flat_and_home_copies(self):
        rows = carriers([entry("plan.md", "a", 4), entry("home/user/plan.md", "a", 4)])
        self.assertEqual(rows, [{"source_identity": "/home/user/plan.md", "original": "home/user/plan.md",
                                 "original_carries": f"{S}::msg4", "copies": ["plan.md"], "revisions": []}])

    def test_earliest_version_is_original_and_later_is_revision(self):
        rows = carriers([entry("plan.md", "b", 9), entry("home/user/plan.md", "a", 4)])
        self.assertEqual(rows[0]["original"], "home/user/plan.md")
        self.assertEqual(rows[0]["revisions"], [{"path": "plan.md", "carries": f"{S}::msg9", "similarity": 1.0}])

    def test_pre_edit_flat_copy_is_original(self):
        rows = carriers([entry("plan.md", "a", 4), entry("home/user/plan.md", "b", 9)])
        self.assertEqual(rows[0]["original"], "plan.md")
        self.assertEqual([r["path"] for r in rows[0]["revisions"]], ["home/user/plan.md"])

    def test_single_carrier_is_not_listed(self):
        self.assertEqual(carriers([entry("plan.md", "a", 4), Entry("x.md", "authored", "c", 1)]), [])

    def test_carrier_table_is_reverified_only_when_present(self):
        old = {"schema": "arena-pipeline/ledger/3"}
        self.assertNotIn("carriers", measured_fields(old))
        self.assertIn("carriers", measured_fields({**old, "carriers": [], "carrier_policy": CARRIER_POLICY}))


if __name__ == "__main__":
    unittest.main()
