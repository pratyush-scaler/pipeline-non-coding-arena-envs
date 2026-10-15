"""Privacy credit requires replayable source evidence and independent semantics."""
import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.artifacts import atomic_json
from pipeline.author.build import build as export
from pipeline.ledger.anonymization import MANIFEST, SCHEMA, sha, transform
from pipeline.ledger.faithfulness import build
from pipeline.tests.test_production import synthetic_bundle


class CalendarProvenance(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = synthetic_bundle(self.root)
        self.fixture = self.bundle / "environment/files"
        self.source = "約定 2026-08-14; price 1.1; height 3.3m\r\nDelivery 8/20; month 8月\r\n"
        self.edits = []
        for token, day, fmt in (("2026-08-14", "2026-08-14", "iso-date"),
                                ("8/20", "2026-08-20", "slash-date"),
                                ("8月", "2026-08-01", "zh-month")):
            start = self.source.index(token)
            self.edits.append({"start": start, "end": start + len(token), "date": day, "format": fmt})
        self.window = ["2026-08-01", "2027-01-31"]
        self.public, _ = transform(self.source, self.edits, -153, self.window)
        (self.fixture / "schedule.md").write_bytes(self.public.encode())
        originals = {p.name: p.read_text() for p in self.fixture.iterdir()}
        originals["schedule.md"] = self.source
        trace = {"session_id": "session", "messages": [{"role": "assistant", "content": [
            {"type": "tool-write_file", "input": {"path": name, "content": content}}
            for name, content in originals.items()]}]}
        atomic_json(self.root / "dump/sessions/session/data.json", {"traces": [trace]})
        self.enterContext(patch.dict(os.environ, ARENA_DUMP=str(self.root / "dump")))
        spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        spec["source"] = {"session_id": "session", "seed_index": 0}
        spec["_producer"] = {"model": "author"}
        spec["traps"] = []
        export(spec, self.bundle)
        self.manifest = {"schema": SCHEMA, "kind": "fixed-day-shift", "days": -153,
            "source_window": self.window, "files": [{"path": "schedule.md",
                "citation": "session::msg0::schedule.md", "source_sha256": sha(self.source.encode()),
                "public_sha256": sha(self.public.encode()), "edits": self.edits}]}
        self.save()

    def save(self):
        atomic_json(self.bundle / MANIFEST, self.manifest)

    def ledger(self):
        result = build(self.bundle, "session", 0)
        result["category"] = "B"
        atomic_json(self.bundle / "provenance/ledger.json", result)
        return result

    def test_verified_calendar_retains_source_credit_but_not_exact_copy_credit(self):
        ledger = self.ledger()
        self.assertEqual(ledger["faithfulness_by_bytes"], 1)
        self.assertLess(ledger["exact_copy_by_bytes"], 1)
        self.assertEqual(ledger["counts"]["anonymized"], 1)
        self.assertIn("price 1.1; height 3.3m\r\n", self.public)
        self.assertIn("2026-03-14", self.public)
        self.assertEqual(ledger["privacy_transformation"]["manifest_sha256"], sha((self.bundle / MANIFEST).read_bytes()))

    def test_missing_manifest_gives_no_privacy_credit(self):
        (self.bundle / MANIFEST).unlink()
        ledger = self.ledger()
        self.assertEqual(ledger["counts"]["anonymized"], 0)
        self.assertLess(ledger["faithfulness_by_bytes"], 1)

    def test_price_edit_cannot_be_laundered_by_updating_public_hash(self):
        forged = self.public.replace("price 1.1", "price 9.9")
        (self.fixture / "schedule.md").write_bytes(forged.encode())
        self.manifest["files"][0]["public_sha256"] = sha(forged.encode())
        self.save()
        with self.assertRaisesRegex(ValueError, "differs from the verified"):
            self.ledger()

    def test_manifest_tampering_and_untrusted_sources_fail_closed(self):
        original = copy.deepcopy(self.manifest)
        mutations = [
            lambda m: m.update(days=True),
            lambda m: m.update(days=0),
            lambda m: m.update(days=-154),
            lambda m: m.update(kind="replace-text"),
            lambda m: m.update(source_window=["2026-01-01", "2027-12-31"]),
            lambda m: m["files"][0].update(citation="other::msg0::schedule.md"),
            lambda m: m["files"][0].update(source_sha256="a" * 64),
            lambda m: m["files"][0].update(public_sha256="a" * 64),
            lambda m: m["files"][0].update(path="../schedule.md"),
            lambda m: m["files"].append(copy.deepcopy(m["files"][0])),
            lambda m: m["files"][0]["edits"][0].update(replacement="approved"),
            lambda m: m["files"][0]["edits"][0].update(format="plain-text"),
            lambda m: m["files"][0]["edits"].reverse(),
            lambda m: m["files"][0]["edits"][0].update(start=0),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutations.index(mutate)):
                self.manifest = copy.deepcopy(original)
                mutate(self.manifest)
                self.save()
                with self.assertRaises((ValueError, OSError)):
                    self.ledger()

    def test_month_intervals_leap_days_and_numeric_boundaries(self):
        text = "2024-02-29"
        edits = [{"start": 0, "end": len(text), "date": text, "format": "iso-date"}]
        self.assertEqual(transform(text, edits, 1, [text, text])[0], "2024-03-01")
        self.assertEqual(transform(text + ".", edits, 1, [text, text])[0], "2024-03-01.")
        text = "2026-12-31"
        edits[0].update(date=text)
        self.assertEqual(transform(text, edits, 1, [text, text])[0], "2027-01-01")
        with self.assertRaisesRegex(ValueError, "entire month"):
            transform("1月", [{"start": 0, "end": 2, "date": "2026-01-01", "format": "zh-month"}],
                      31, ["2026-01-01", "2026-01-31"])
        with self.assertRaisesRegex(ValueError, "numeric token"):
            transform("18/20", [{"start": 1, "end": 5, "date": "2026-08-20", "format": "slash-date"}],
                      -153, self.window)

    def test_gate_recomputes_privacy_credit_and_keeps_category_floor(self):
        from pipeline.gates.bundle import _ledger_shape
        from pipeline.gates.base import GateContext
        ledger = self.ledger()
        atomic_json(self.bundle / "authoring/traps.json", {"source_tier": 2})
        ctx = GateContext(self.bundle, self.root)
        self.assertEqual(_ledger_shape(ctx)[0], [])
        (self.fixture / "schedule.md").write_text(self.public + "An unrelated invented decision.")
        findings, _ = _ledger_shape(ctx)
        self.assertIn("unverified-anonymization", {f.code for f in findings})
        (self.fixture / "schedule.md").write_bytes(self.public.encode())
        ledger["schema"] = "arena-pipeline/ledger/2"
        atomic_json(self.bundle / "provenance/ledger.json", ledger)
        self.assertIn("unverified-anonymization", {f.code for f in _ledger_shape(ctx)[0]})
        # A valid transformation does not grant credit to unrelated authored data.
        (self.fixture / "invented.md").write_text("Unsupported new business material.\n" * 100)
        self.ledger()
        self.assertIn("below-fixture-floor", {f.code for f in _ledger_shape(ctx)[0]})

    def test_release_recomputes_both_metrics_and_legacy_ledgers_remain_usable(self):
        from pipeline.release import _provenance_problems
        ledger = self.ledger()
        self.assertEqual(_provenance_problems(self.bundle), [])
        ledger["exact_copy_by_bytes"] = 1
        atomic_json(self.bundle / "provenance/ledger.json", ledger)
        self.assertTrue(_provenance_problems(self.bundle))
        (self.bundle / MANIFEST).unlink()
        ledger = self.ledger()
        ledger["schema"] = "arena-pipeline/ledger/2"
        for key in ("exact_copy_by_bytes", "exact_copy_by_file", "privacy_transformation"):
            del ledger[key]
        atomic_json(self.bundle / "provenance/ledger.json", ledger)
        self.assertEqual(_provenance_problems(self.bundle), [])

    def test_missing_trace_symlinks_and_duplicate_json_are_rejected(self):
        target = self.fixture / "schedule.md"
        original = target.read_bytes()
        target.unlink()
        elsewhere = self.root / "external.md"
        elsewhere.write_bytes(original)
        target.symlink_to(elsewhere)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.ledger()
        target.unlink()
        target.write_bytes(original)
        outside = self.root / "external-fixture"
        self.fixture.rename(outside)
        self.fixture.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.ledger()
        self.fixture.unlink()
        outside.rename(self.fixture)
        (self.bundle / MANIFEST).write_text('{"schema":"a","schema":"b"}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.ledger()
        self.save()
        (self.root / "dump/sessions/session/data.json").unlink()
        with self.assertRaises(OSError):
            self.ledger()

    def test_independent_review_requires_calendar_assessment_and_binds_originals(self):
        from pipeline.review import review, review_problems
        self.ledger()
        spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        include_assessment = False
        def critic(_prompt, public, work, model, _tag, max_steps):
            audit = json.loads((public / "calendar-audit.json").read_text())
            self.assertEqual(audit["files"]["schedule.md"]["source_content"], self.source)
            self.assertFalse((self.fixture / "calendar-audit.json").exists())
            shutil.copytree(public, work / "workspace")
            atomic_json(work / "conversation.json", [])
            atomic_json(work / "request-config.json", {"model": model, "max_steps": max_steps})
            doc = {"verdict": "pass", "checks": [{"id": c["id"], "verdict": "pass",
                "reason": "The published source supports the specific criterion and its output semantics.",
                "citations": [{"file": "fixture/tickets.csv", "quote": "ticket,status,effort\nR-21,open,3"}]}
                for c in spec["checks"]], "ambiguities": [], "substantive_gaps": [], "shortcut_risks": [],
                "privacy_findings": [], "difficulty_assessment": "Synthetic fixture tests review evidence rather than empirical difficulty assurance.",
                "novelty_assessment": "Synthetic fixture tests the supplied comparison context and exact review bindings.",
                "untested_surfaces": ["No empirical calibration."]}
            if include_assessment:
                doc["calendar_assessment"] = {"verdict": "pass",
                    "reason": "The shifted tokens are calendar dates; prices and durations remain unchanged. This synthetic task has no weekday, holiday or seasonal assumptions.",
                    "citations": [{"file": "calendar-audit.json", "quote": '"kind": "fixed-day-shift"'},
                                  {"file": "fixture/schedule.md", "quote": "2026-03-14; price 1.1; height 3.3m"},
                                  {"file": "package-layout/Dockerfile", "quote": "COPY files/ /app/environment/files/"}]}
            from pipeline.tests.test_solver_brief import synthetic_autonomy_assessment
            doc["solver_autonomy"] = synthetic_autonomy_assessment(public)
            atomic_json(work / "deliverables/review.json", doc)
            return SimpleNamespace(error=None, stop_reason="completed", tool_calls=1), None
        with patch("pipeline.calibrate.run._rollout_for", return_value=critic), \
             patch("pipeline.corpus.review_context", return_value={"peers": []}):
            report = review(self.bundle, "critic")
            self.assertIn("calendar anonymization lacks an independent semantic assessment", report["errors"])
            include_assessment = True
            report = review(self.bundle, "critic")
            self.assertEqual(report["errors"], [])
            rel = "workspace/calendar-audit.json"
            path = self.bundle / report["work_dir"] / rel
            atomic_json(path, {"fabricated": "trusted source"})
            report["artifacts"][rel] = sha(path.read_bytes())
            self.assertIn("calendar reviewer evidence differs from the trusted source transformation",
                          review_problems(self.bundle, report))


if __name__ == "__main__":
    unittest.main()
