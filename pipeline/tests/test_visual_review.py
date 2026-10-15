"""An image cannot be text-scanned, so it ships only after a pinned visual review."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.privacy import VISUAL_REVIEW, scan, unresolved


class VisualReview(unittest.TestCase):
    def test_an_image_is_open_until_its_exact_bytes_are_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            image = bundle / "environment/files/sources/page.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
            findings = scan(bundle / "environment/files")
            self.assertTrue(any(f["kind"] == "unscannable" for f in findings))
            self.assertTrue(unresolved(bundle, findings))
            review = bundle / VISUAL_REVIEW
            review.parent.mkdir(parents=True)
            entry = {"sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                     "reviewer": "a reviewer", "verdict": "no personal data"}
            review.write_text(json.dumps({"files": {"sources/page.png": entry}}))
            self.assertEqual(unresolved(bundle, findings), [])
            image.write_bytes(image.read_bytes() + b"changed")     # new bytes: review no longer applies
            self.assertTrue(unresolved(bundle, scan(bundle / "environment/files")))
