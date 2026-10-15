"""Offline credential reloads and same-request transport recovery."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from pipeline import cli, credentials
from pipeline.calibrate import agent_openai as agent
from pipeline.provider import ProviderBudgetExhausted, RequestBudget
from pipeline.tests.test_openai_transport import stream, terminal


def http_error(status=429, code="rate_limit_exceeded", error_type=None, headers=None):
    error = {"code": code, "message": "private provider prose offline-one offline-two"}
    if error_type:
        error["type"] = error_type
    return HTTPError(agent.API_URL, status, "private raw HTTP reason", headers or {},
                     io.BytesIO(json.dumps({"error": error}).encode()))


class CredentialFixtures(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.keys_file = Path(temporary.name) / "keys.env"
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.enterContext(patch.object(credentials, "_managed_environment", {}))
        self.enterContext(patch.object(credentials, "_enabled_keys_file", None))
        self.enterContext(patch.object(credentials, "KEYS_FILE", self.keys_file))
        self.pool = credentials.OpenAICredentialPool(self.keys_file)

    def stage_keys(self, values=None):
        values = values or {"OPEN_AI_API_KEY1": "offline-one", "OPEN_AI_API_KEY2": "offline-two",
                            "OPEN_AI_API_KEY3": "offline-three"}
        self.keys_file.write_text("\n".join(f"{name}={value}" for name, value in values.items()) + "\n")


class OpenAICredentials(CredentialFixtures):
    def test_aliases_normalize_without_modifying_input(self):
        values = {"OPEN_AI_API_KEY3": "three", "OPEN_AI_API_KEY1": " one ",
                  "OPEN_AI_API_KEY2": "two"}
        normalized = credentials.normalize_openai_aliases(values)
        self.assertEqual(normalized["OPENAI_API_KEY"], "one")
        self.assertNotIn("OPENAI_API_KEY", values)

    def test_canonical_priority_numeric_order_and_deduplication(self):
        values = {"OPENAI_API_KEY": "canonical", "OPEN_AI_API_KEY1": "canonical",
                  "OPENAI_API_KEY_2": "two", "OPEN_AI_API_KEY10": "ten",
                  "OPEN_AI_API_KEY3": "three", "OPENAI_API_KEY4": "two",
                  "ANTHROPIC_API_KEY": "not-openai", "OPENAI_API_KEY0": "invalid"}
        self.assertEqual(credentials.openai_keys(values), ("canonical", "two", "three", "ten"))

    def test_cli_normalizes_in_memory_without_rewriting_the_file(self):
        self.stage_keys({"ANTHROPIC_API_KEY": "offline-anthropic", "OPEN_AI_API_KEY1": "offline-one"})
        before = self.keys_file.read_bytes()
        with patch.object(cli, "KEYS", self.keys_file):
            values = cli.load_keys(prompt_if_missing=False)
        self.assertEqual(values["OPENAI_API_KEY"], "offline-one")
        self.assertEqual(os.environ["OPENAI_API_KEY"], "offline-one")
        self.assertEqual(self.keys_file.read_bytes(), before)

    def test_cli_keeps_an_explicit_canonical_environment_key(self):
        self.stage_keys()
        os.environ["OPENAI_API_KEY"] = "explicit"
        with patch.object(cli, "KEYS", self.keys_file):
            cli.load_keys(prompt_if_missing=False)
        self.assertEqual(os.environ["OPENAI_API_KEY"], "explicit")
        self.assertEqual(self.pool.select(), "explicit")

    def test_cold_cli_selected_file_is_used_by_the_default_pool(self):
        self.stage_keys({"OPEN_AI_API_KEY1": "selected-file"})
        with patch.object(credentials, "KEYS_FILE", self.keys_file.parent / "wrong-file"), \
                patch.object(cli, "KEYS", self.keys_file):
            cli.load_keys(prompt_if_missing=False)
            self.assertEqual(credentials.OpenAICredentialPool().select(), "selected-file")

    def test_default_pool_does_not_read_workspace_keys_without_cli_opt_in(self):
        self.stage_keys()
        os.environ["OPENAI_API_KEY"] = "fake-explicit-canonical"
        pool = credentials.OpenAICredentialPool()
        with patch.object(credentials, "_file_keys", side_effect=AssertionError("Unexpected file read")):
            self.assertEqual(pool.select(), "fake-explicit-canonical")
            self.assertEqual(pool.select(rotate_after="fake-explicit-canonical"), "fake-explicit-canonical")

    def test_explicit_override_after_cli_load_does_not_use_file_or_managed_aliases(self):
        self.stage_keys()
        with patch.object(cli, "KEYS", self.keys_file):
            cli.load_keys(prompt_if_missing=False)
        os.environ["OPENAI_API_KEY"] = "fake-test-override"
        pool = credentials.OpenAICredentialPool()
        with patch.object(credentials, "_file_keys", side_effect=AssertionError("Unexpected file read")):
            self.assertEqual(pool.select(), "fake-test-override")
            self.assertEqual(pool.select(rotate_after="fake-test-override"), "fake-test-override")

    def test_default_environment_alias_pool_does_not_read_workspace_keys(self):
        self.stage_keys()
        os.environ.update({"OPEN_AI_API_KEY1": "environment-one", "OPEN_AI_API_KEY2": "environment-two"})
        pool = credentials.OpenAICredentialPool()
        with patch.object(credentials, "_file_keys", side_effect=AssertionError("Unexpected file read")):
            self.assertEqual(pool.select(), "environment-one")
            self.assertEqual(pool.select(rotate_after="environment-one"), "environment-two")

    def test_updated_file_replaces_cli_managed_canonical_and_aliases(self):
        self.stage_keys({"OPEN_AI_API_KEY1": "old"})
        with patch.object(cli, "KEYS", self.keys_file):
            cli.load_keys(prompt_if_missing=False)
        self.assertEqual(self.pool.select(), "old")
        self.stage_keys({"OPEN_AI_API_KEY2": "updated"})
        self.assertEqual(self.pool.select(), "updated")
        self.assertEqual(self.pool.select(rotate_after="old"), "updated")

    def test_removed_file_does_not_resurrect_cli_managed_secrets(self):
        self.stage_keys()
        with patch.object(cli, "KEYS", self.keys_file):
            cli.load_keys(prompt_if_missing=False)
        self.keys_file.unlink()
        with self.assertRaisesRegex(RuntimeError, "No OpenAI credential configured"):
            self.pool.select()

    def test_environment_only_aliases_and_single_key_rotation(self):
        os.environ["OPEN_AI_API_KEY2"] = "environment-only"
        self.assertEqual(self.pool.select(), "environment-only")
        self.assertEqual(self.pool.select(rotate_after="environment-only"), "environment-only")

    def test_rotation_deduplicates_and_wraps(self):
        self.stage_keys({"OPENAI_API_KEY": "one", "OPEN_AI_API_KEY1": "one",
                         "OPEN_AI_API_KEY2": "two"})
        self.assertEqual(self.pool.select(), "one")
        self.assertEqual(self.pool.select(rotate_after="one"), "two")
        self.assertEqual(self.pool.select(rotate_after="two"), "one")

    def test_quoted_export_aliases_are_data_not_shell_commands(self):
        self.keys_file.write_text("# ignored\nexport OPEN_AI_API_KEY1='literal$(not-executed)'\n")
        self.assertEqual(self.pool.select(), "literal$(not-executed)")

    def test_unreadable_file_has_a_payload_free_error(self):
        self.keys_file.mkdir()
        with self.assertRaisesRegex(RuntimeError, "credential file could not be read") as caught:
            self.pool.select()
        self.assertNotIn(str(self.keys_file), str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)


class OpenAIRotationTransport(CredentialFixtures):
    def setUp(self):
        super().setUp()
        self.stage_keys()
        self.enterContext(patch.object(agent, "OPENAI_POOL", self.pool))
        self.enterContext(patch.object(agent, "request_slot", contextlib.nullcontext))
        self.enterContext(patch.object(agent.random, "random", return_value=0))
        self.sleep = self.enterContext(patch.object(agent.time, "sleep"))

    def test_http_throttles_rotate_without_changing_body_or_attempt_budget(self):
        for status, code in [(429, None), (429, "rate_limit_exceeded"), (429, "slow_down"),
                             (503, "slow_down")]:
            self.sleep.reset_mock()
            with self.subTest(status=status, code=code), \
                    patch.object(agent, "OPENAI_POOL", credentials.OpenAICredentialPool(self.keys_file)), \
                    patch.object(agent.urllib.request, "urlopen", side_effect=[
                        http_error(status, code), stream(terminal())]) as request:
                body = {"model": "gpt-6-astra", "input": [{"role": "user", "content": "unchanged"}],
                        "tools": agent.TOOLS, "reasoning": {"effort": "high"}}
                before = json.dumps(body)
                agent._call(body, retries=2)
                sent = [call.args[0] for call in request.call_args_list]
                self.assertEqual([item.get_header("Authorization") for item in sent],
                                 ["Bearer offline-one", "Bearer offline-two"])
                self.assertEqual(sent[0].data, sent[1].data)
                self.assertEqual(json.dumps(body), before)
                self.assertEqual(request.call_count, 2)
                self.sleep.assert_called_once_with(15)

    def test_quota_billing_auth_and_action_types_do_not_retry_or_rotate(self):
        for status, code, error_type in [(401, "rate_limit_exceeded", None),
                                        (403, None, None), (429, "insufficient_quota", None),
                                        (429, "billing_hard_limit_reached", None),
                                        (429, "rate_limit_exceeded", "billing_error"),
                                        (429, "invalid_api_key", None),
                                        (429, None, "project_spend_limit_exceeded")]:
            with self.subTest(status=status, code=code, error_type=error_type), \
                    patch.object(agent.urllib.request, "urlopen",
                                 side_effect=http_error(status, code, error_type)) as request:
                with self.assertRaises(RuntimeError) as caught:
                    agent._call({"model": "gpt-6-astra"}, retries=5)
                self.assertEqual(request.call_count, 1)
                self.assertEqual(self.pool.select(), "offline-one")
                self.sleep.assert_not_called()
                self.assertNotIn("private", str(caught.exception))
                self.assertNotIn("offline-", str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_non_rate_transient_errors_keep_the_same_credential(self):
        for failure in [http_error(503, "server_is_overloaded"), URLError("private connection text")]:
            with self.subTest(kind=type(failure).__name__), \
                    patch.object(agent.urllib.request, "urlopen",
                                 side_effect=[failure, stream(terminal())]) as request:
                agent._call({"model": "gpt-6-astra"}, retries=2)
                self.assertEqual([call.args[0].get_header("Authorization") for call in request.call_args_list],
                                 ["Bearer offline-one", "Bearer offline-one"])

    def test_retry_after_is_honored_before_using_another_key(self):
        with patch.object(agent.urllib.request, "urlopen", side_effect=[
                http_error(headers={"Retry-After": "45"}), stream(terminal())]):
            agent._call({"model": "gpt-6-astra"}, retries=2)
        self.sleep.assert_called_once_with(45)

    def test_long_retry_after_defers_without_rotating_or_retrying(self):
        with patch.object(agent.urllib.request, "urlopen", side_effect=
                http_error(headers={"Retry-After": "121"})) as request:
            with self.assertRaisesRegex(RuntimeError, "continuation deferred"):
                agent._call({"model": "gpt-6-astra"}, retries=5)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(self.pool.select(), "offline-one")
        self.sleep.assert_not_called()

    def test_file_is_reloaded_before_a_retry(self):
        requests = []
        def respond(request, **kwargs):
            requests.append(request)
            if len(requests) == 1:
                self.stage_keys({"OPEN_AI_API_KEY2": "replacement"})
                raise http_error()
            return stream(terminal())
        with patch.object(agent.urllib.request, "urlopen", side_effect=respond):
            agent._call({"model": "gpt-6-astra"}, retries=2)
        self.assertEqual([request.get_header("Authorization") for request in requests],
                         ["Bearer offline-one", "Bearer replacement"])
        self.assertEqual(requests[0].data, requests[1].data)

    def test_sse_rate_codes_and_failed_rate_terminals_rotate(self):
        events = [{"type": "error", "error": {"code": code}} for code in
                  ["rate_limit_exceeded", "slow_down", "rate_limit_error"]]
        failed = terminal("failed")
        failed["response"]["error"] = {"code": "rate_limit_exceeded"}
        for event in [*events, failed]:
            with self.subTest(kind=event["type"]), \
                    patch.object(agent, "OPENAI_POOL", credentials.OpenAICredentialPool(self.keys_file)), \
                    patch.object(agent.urllib.request, "urlopen", side_effect=[
                        stream(event), stream(terminal())]) as request:
                agent._call({"model": "gpt-6-astra"}, retries=2)
                self.assertEqual([call.args[0].get_header("Authorization") for call in request.call_args_list],
                                 ["Bearer offline-one", "Bearer offline-two"])

    def test_sse_retry_after_is_honored_and_oversized_hints_defer(self):
        for hint in ["45", "121"]:
            self.sleep.reset_mock()
            response = stream({"type": "error", "error": {"code": "slow_down"}})
            response.headers = {"Retry-After": hint}
            with self.subTest(hint=hint), patch.object(agent.urllib.request, "urlopen",
                    side_effect=[response, stream(terminal())]) as request:
                if hint == "45":
                    agent._call({"model": "gpt-6-astra"}, retries=2)
                    self.sleep.assert_called_once_with(45)
                else:
                    with self.assertRaisesRegex(RuntimeError, "continuation deferred"):
                        agent._call({"model": "gpt-6-astra"}, retries=2)
                    self.assertEqual(request.call_count, 1)
                    self.sleep.assert_not_called()

    def test_sse_quota_and_auth_even_in_a_conflicting_type_never_rotate(self):
        for code, error_type in [("insufficient_quota", None), ("invalid_api_key", None),
                                 ("rate_limit_exceeded", "billing_error")]:
            event = {"type": "error", "error": {"code": code, "type": error_type}}
            with self.subTest(code=code), patch.object(agent.urllib.request, "urlopen",
                    side_effect=[stream(event), stream(terminal())]) as request:
                with self.assertRaises(RuntimeError):
                    agent._call({"model": "gpt-6-astra"}, retries=5)
                self.assertEqual(request.call_count, 1)
                self.assertEqual(self.pool.select(), "offline-one")

    def test_partial_tools_before_sse_rotation_are_never_executed(self):
        partial = {"type": "response.output_item.done", "item": {"type": "function_call",
                   "call_id": "partial", "name": "write_file", "arguments": "{}"}}
        output = [{"type": "function_call", "call_id": "committed", "name": "write_file",
                   "arguments": json.dumps({"path": "answer.json", "content": "{}"})}]
        fixture = self.keys_file.parent / "fixture"
        fixture.mkdir()
        attempt = self.keys_file.parent / "attempt"
        with patch.object(agent.urllib.request, "urlopen", side_effect=[
                stream(partial, {"type": "error", "error": {"code": "slow_down"}}),
                stream(terminal(output=output)), stream(terminal())]) as request:
            record, submitted = agent.rollout("offline", fixture, attempt, "gpt-6-astra", "test", max_steps=3)
        self.assertEqual(record.tool_calls, 1)
        self.assertEqual(sorted(filename.name for filename in submitted.iterdir()), ["answer.json"])
        self.assertEqual(request.call_args_list[0].args[0].data, request.call_args_list[1].args[0].data)
        conversation = json.loads((attempt / "conversation.json").read_text())
        self.assertFalse(any(item.get("call_id") == "partial" for item in conversation))

    def test_exhaustion_keeps_five_requests_and_four_waits(self):
        with patch.object(agent.urllib.request, "urlopen", side_effect=lambda *args, **kwargs: http_raise()) as request:
            with self.assertRaisesRegex(RuntimeError, "failed after 5 attempts"):
                agent._call({"model": "gpt-6-astra"})
        self.assertEqual(request.call_count, 5)
        self.assertEqual(self.sleep.call_count, 4)
        self.assertEqual([call.args[0].get_header("Authorization") for call in request.call_args_list],
                         ["Bearer offline-one", "Bearer offline-two", "Bearer offline-three",
                          "Bearer offline-one", "Bearer offline-two"])

    def test_provider_request_cap_is_not_reset_by_rotation(self):
        budget = RequestBudget(concurrency=1, max_requests=2)
        with patch.object(agent, "request_slot", budget.slot), \
                patch.object(agent.urllib.request, "urlopen", side_effect=lambda *args, **kwargs: http_raise()) as request:
            with self.assertRaisesRegex(RuntimeError, "failed after 2 attempts"):
                agent._call({"model": "gpt-6-astra"}, retries=2)
            with self.assertRaises(ProviderBudgetExhausted):
                agent._call({"model": "gpt-6-astra"}, retries=2)
        self.assertEqual(budget.requests, 2)
        self.assertEqual(request.call_count, 2)

    def test_observations_and_errors_contain_no_keys_or_provider_prose(self):
        observation = self.keys_file.parent / "transport.jsonl"
        with patch.dict(os.environ, {"ARENA_TRANSPORT_OBSERVATIONS": str(observation)}), \
                patch.object(agent.urllib.request, "urlopen", side_effect=[http_error(), http_error()]):
            with self.assertRaises(RuntimeError) as caught:
                agent._call({"model": "gpt-6-astra", "input": "private prompt"}, retries=2)
        retained = observation.read_text() + str(caught.exception)
        self.assertNotIn("offline-", retained)
        self.assertNotIn("private", retained)
        self.assertNotIn("Authorization", retained)

    def test_a_secret_shaped_stream_error_code_is_not_retained(self):
        secret = "sk-project-private-key"
        with self.assertRaises(RuntimeError) as caught:
            agent._consume_stream(stream({"type": "error", "error": {"code": secret}}))
        self.assertNotIn(secret, str(caught.exception))

    def test_any_configured_pool_secret_is_withheld_from_error_codes_and_fields(self):
        secret = "private_provider_secret"
        self.stage_keys({"OPEN_AI_API_KEY1": secret})
        self.pool.select()
        for error in [{"code": secret}, {secret: "private provider prose"},
                      {"code": "provider_" + secret + "_error"}]:
            with self.subTest(shape=list(error)), self.assertRaises(RuntimeError) as caught:
                agent._consume_stream(stream({"type": "error", "error": error}))
            self.assertNotIn(secret, str(caught.exception))
            self.assertNotIn("private provider prose", str(caught.exception))
        self.assertNotIn(secret, repr(self.pool))


def http_raise():
    raise http_error()


if __name__ == "__main__":
    unittest.main()
