"""An in-stream provider error that is infra loss is retried, not reported as
a result (build 2026-09-26: one rate-limit burst voided 13 reviews)."""
import io
import json
import unittest
from unittest.mock import patch

from pipeline.calibrate import agent_openai


def stream(*events):
    lines = []
    for event in events:
        lines += [f"data: {json.dumps(event)}\n".encode(), b"\n"]
    return io.BytesIO(b"".join(lines))


class _Resp:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self.body

    def __exit__(self, *exc):
        return False


DONE = {"type": "response.completed",
        "response": {"status": "completed", "output": []}}


class TransientStreamErrors(unittest.TestCase):
    def call(self, *bodies):
        responses = iter([_Resp(b) for b in bodies])
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}), \
             patch.object(agent_openai.urllib.request, "urlopen", side_effect=lambda *a, **k: next(responses)), \
             patch.object(agent_openai.time, "sleep") as sleep:
            return agent_openai._call({"model": "m"}), sleep

    def test_a_rate_limit_in_the_stream_is_retried_with_a_long_backoff(self):
        limited = stream({"type": "error", "error": {"code": "rate_limit_exceeded"}})
        response, sleep = self.call(limited, stream(DONE))
        self.assertEqual(response["status"], "completed")
        self.assertGreaterEqual(sleep.call_args[0][0], 15)

    def test_a_quota_error_in_the_stream_is_not_retried(self):
        quota = stream({"type": "error", "error": {"code": "insufficient_quota"}})
        with self.assertRaisesRegex(RuntimeError, "insufficient_quota"):
            self.call(quota, stream(DONE))


if __name__ == "__main__":
    unittest.main()
