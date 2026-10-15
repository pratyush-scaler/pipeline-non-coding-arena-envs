"""The design loop caches its prefix without changing what the model reads.

Measured 2026-09-27 over 78 environments: a median of 172 designer requests per
environment re-sent a median of 26M tokens of unchanged prefix at the full
input rate, about 85% of authoring spend. Cache markers cut that by roughly
an order of magnitude, and they must do so WITHOUT touching the prompt: the
rendered tools, system and messages have to stay byte-identical, the stored
request config has to keep deciding whether a stalled session may resume, and
`conversation.json` must never accumulate a marker per turn (the API allows
four per request; a fifth is a 400 that would end the design).
"""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pipeline.author.agent_designer import (
    CACHE_MARK, CACHEABLE_BLOCKS, design, with_cache_breakpoints)
from pipeline.author.outcomes import SeedRejected


def markers(node) -> int:
    """Count `cache_control` keys anywhere in a request body."""
    if isinstance(node, dict):
        return int("cache_control" in node) + sum(markers(v) for v in node.values())
    if isinstance(node, list):
        return sum(markers(v) for v in node)
    return 0


def rendered(body: dict) -> dict:
    """What the API renders: markers removed, shorthand strings expanded."""
    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k != "cache_control"}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node
    out = strip(body)
    system = out.get("system")
    if isinstance(system, str):
        out["system"] = [{"type": "text", "text": system}]
    return out


def a_body() -> dict:
    return {"model": "claude-opus-5", "max_tokens": 48000, "system": "You design tasks.",
            "output_config": {"effort": "xhigh"},
            "tools": [{"name": "read_fixture", "description": "Read.", "input_schema": {"type": "object"}}],
            "messages": [
                {"role": "user", "content": "Design from the source."},
                {"role": "assistant", "content": [
                    {"type": "thinking", "thinking": "", "signature": "sig"},
                    {"type": "text", "text": "Reading."},
                    {"type": "tool_use", "id": "t1", "name": "read_fixture", "input": {"path": "a.md"}}]},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": "# a\n"}]}]}


class CacheBreakpoints(unittest.TestCase):
    def test_two_markers_on_system_and_the_last_block_only(self):
        body = a_body()
        cached = with_cache_breakpoints(body)
        self.assertEqual(markers(cached), 2)
        self.assertEqual(cached["system"], [{"type": "text", "text": body["system"], "cache_control": CACHE_MARK}])
        self.assertIs(cached["tools"], body["tools"], "tools are shared, not copied or marked")
        self.assertEqual(markers(cached["tools"]), 0)
        self.assertIs(cached["messages"][0], body["messages"][0])
        self.assertIs(cached["messages"][1], body["messages"][1])
        tail = cached["messages"][-1]["content"]
        self.assertEqual(tail[-1]["cache_control"], CACHE_MARK)
        self.assertEqual(tail[-1]["type"], "tool_result")

    def test_the_rendered_prompt_is_byte_identical(self):
        body = a_body()
        self.assertEqual(rendered(with_cache_breakpoints(body)), rendered(body))
        self.assertEqual(json.dumps(rendered(with_cache_breakpoints(body)), sort_keys=True),
                         json.dumps(rendered(body), sort_keys=True))

    def test_the_caller_s_body_is_never_mutated(self):
        body = a_body()
        before = copy.deepcopy(body)
        with_cache_breakpoints(body)
        self.assertEqual(body, before)
        self.assertEqual(markers(body), 0)

    def test_a_lone_string_opening_is_sent_exactly_as_written(self):
        # The first request carries only the opening; a string message is never
        # rewritten into blocks, so the request has the system marker alone.
        body = {**a_body(), "messages": [{"role": "user", "content": "Design from the source."}]}
        cached = with_cache_breakpoints(body)
        self.assertIs(cached["messages"], body["messages"])
        self.assertEqual(markers(cached), 1)

    def test_a_string_tail_puts_the_marker_on_the_turn_before_it(self):
        body = {**a_body(), "messages": [*a_body()["messages"],
                                         {"role": "user", "content": "Continue."}]}
        cached = with_cache_breakpoints(body)
        self.assertEqual(markers(cached), 2)
        self.assertIs(cached["messages"][-1], body["messages"][-1], "the string is untouched")
        self.assertEqual(cached["messages"][-2]["content"][-1]["cache_control"], CACHE_MARK)
        self.assertEqual(cached["messages"][-2]["content"][-1]["type"], "tool_result")
        self.assertEqual(rendered(cached), rendered(body))

    def test_the_tail_marker_walks_back_past_a_thinking_block(self):
        body = {**a_body(), "messages": [{"role": "assistant", "content": [
            {"type": "text", "text": "done"}, {"type": "thinking", "thinking": "", "signature": "s"}]}]}
        cached = with_cache_breakpoints(body)
        blocks = cached["messages"][-1]["content"]
        self.assertEqual(blocks[0]["cache_control"], CACHE_MARK)
        self.assertNotIn("cache_control", blocks[1])
        self.assertEqual(markers(cached), 2)

    def test_no_cacheable_block_means_no_tail_marker(self):
        body = {**a_body(), "messages": [{"role": "assistant", "content": [
            {"type": "thinking", "thinking": "", "signature": "s"}]}]}
        cached = with_cache_breakpoints(body)
        self.assertEqual(markers(cached), 1)
        self.assertEqual(cached["messages"], body["messages"])
        self.assertNotIn("thinking", CACHEABLE_BLOCKS)

    def test_a_system_block_list_keeps_its_blocks_and_marks_the_last(self):
        body = {**a_body(), "system": [{"type": "text", "text": "A"}, {"type": "text", "text": "B"}]}
        cached = with_cache_breakpoints(body)
        self.assertEqual(cached["system"], [{"type": "text", "text": "A"},
                                            {"type": "text", "text": "B", "cache_control": CACHE_MARK}])
        self.assertEqual(rendered(cached), rendered(body))

    def test_an_unrecognised_system_shape_is_refused_not_guessed(self):
        for system in (None, "", [], [{"type": "image"}], 42):
            with self.subTest(system=system), self.assertRaises(ValueError):
                with_cache_breakpoints({**a_body(), "system": system})


class DesignLoopRequests(unittest.TestCase):
    """Every request the loop sends is marked; nothing it stores is."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = self.root / "candidate"
        fixture = self.bundle / "environment/files"
        fixture.mkdir(parents=True)
        (fixture / "brief.md").write_text("Only the final total is available; component records are absent.\n")
        self.reason = {"reason": ("The source supplies a copied total but no component records, so no "
                                  "independent decision can be graded: every candidate check would restate "
                                  "the printed total, and a fair two-step task needs component-level evidence "
                                  "that the brief says is absent."),
                       "source_evidence": [{"file": "brief.md", "quote": "component records are absent."}]}

    def test_every_request_is_cached_and_the_record_carries_no_marker(self):
        extraction = SimpleNamespace(session_id="source", seed_index=0, source_root=self.root)
        responses = [
            {"stop_reason": "end_turn", "content": [{"type": "text", "text": "Let me look."}]},
            {"stop_reason": "tool_use", "content": [
                {"type": "tool_use", "id": "reject", "name": "reject_seed", "input": self.reason}]}]
        sent = []
        with patch("pipeline.dump.recover.load_trace", return_value={"messages": []}), \
             patch("pipeline.author.agent_designer._handlers", return_value={}), \
             patch("pipeline.author.agent_designer._opening", return_value="Read the source."), \
             patch("pipeline.author.agent_designer._call",
                   side_effect=lambda body: sent.append(copy.deepcopy(body)) or responses[len(sent) - 1]):
            with self.assertRaises(SeedRejected):
                design({}, extraction, self.bundle, max_steps=10)
        self.assertEqual(len(sent), 2)
        for body in sent:
            self.assertEqual(body["system"][-1]["cache_control"], CACHE_MARK)
            self.assertLessEqual(markers(body), 4)
        # Request 1 carries the opening alone, a string: system marker only,
        # and the opening goes out exactly as `_opening` composed it.
        self.assertEqual(markers(sent[0]), 1)
        self.assertEqual(len(sent[0]["messages"]), 1)
        self.assertIsInstance(sent[0]["messages"][0]["content"], str)
        self.assertIn("Read the source.", sent[0]["messages"][0]["content"])
        # Request 2 ends in the string "Continue." nudge, so the tail marker
        # sits on the assistant turn before it; the opening is re-sent as is.
        self.assertEqual(len(sent[1]["messages"]), 3)
        self.assertEqual(markers(sent[1]), 2)
        self.assertEqual(sent[1]["messages"][0], sent[0]["messages"][0])
        self.assertEqual(sent[1]["messages"][1]["content"][-1]["cache_control"], CACHE_MARK)
        self.assertIsInstance(sent[1]["messages"][2]["content"], str)
        session = next((self.bundle / "verification/design-sessions").glob("*/request-config.json")).parent
        config = json.loads((session / "request-config.json").read_text())
        self.assertIsInstance(config["system"], str, "the resume contract keeps its shape")
        self.assertEqual(markers(config), 0)
        self.assertEqual(markers(json.loads((session / "conversation.json").read_text())), 0)
        for response in session.glob("response-*.json"):
            self.assertEqual(markers(json.loads(response.read_text())), 0)


if __name__ == "__main__":
    unittest.main()
