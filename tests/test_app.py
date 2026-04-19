"""
Unit tests for my_assistant.

These tests mock all external dependencies (LLM APIs, screen capture) so they
can run in any CI environment without real API keys or a display.
"""

import base64
import io
import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers to inject lightweight fake modules for optional heavy dependencies
# ---------------------------------------------------------------------------

def _fake_image_module():
    """Return a minimal stub for PIL.Image used by llm_client._query_gemini."""
    fake_pil = types.ModuleType("PIL")
    fake_image = types.ModuleType("PIL.Image")

    class _FakeImg:
        pass

    def _open(_buf):
        return _FakeImg()

    fake_image.open = _open
    fake_pil.Image = fake_image
    return fake_pil, fake_image


# ---------------------------------------------------------------------------
# Tests for config.py
# ---------------------------------------------------------------------------

class TestConfig(unittest.TestCase):
    def test_screenshot_region_has_required_keys(self):
        import config
        for key in ("top", "left", "width", "height"):
            self.assertIn(key, config.SCREENSHOT_REGION)

    def test_port_is_integer(self):
        import config
        self.assertIsInstance(config.PORT, int)

    def test_use_ngrok_is_bool(self):
        import config
        self.assertIsInstance(config.USE_NGROK, bool)


# ---------------------------------------------------------------------------
# Tests for llm_client.py
# ---------------------------------------------------------------------------

class TestQueryLlmDispatch(unittest.TestCase):
    """query_llm() should route to the correct provider."""

    FAKE_B64 = base64.b64encode(b"fake-png-data").decode()

    def setUp(self):
        # Ensure llm_client is imported so we can patch its module-level names
        import llm_client  # noqa: F401

    def test_unknown_provider_raises(self):
        import llm_client
        with patch.object(llm_client, "LLM_PROVIDER", "unknown"):
            with self.assertRaises(ValueError):
                llm_client.query_llm("hello", self.FAKE_B64)

    def test_routes_to_openai(self):
        import llm_client
        with patch.object(llm_client, "LLM_PROVIDER", "openai"):
            with patch.object(llm_client, "_query_openai", return_value="ok") as mock:
                result = llm_client.query_llm("q", self.FAKE_B64)
            mock.assert_called_once_with("q", self.FAKE_B64)
            self.assertEqual(result, "ok")

    def test_routes_to_claude(self):
        import llm_client
        with patch.object(llm_client, "LLM_PROVIDER", "claude"):
            with patch.object(llm_client, "_query_claude", return_value="ok") as mock:
                result = llm_client.query_llm("q", self.FAKE_B64)
            mock.assert_called_once_with("q", self.FAKE_B64)
            self.assertEqual(result, "ok")

    def test_routes_to_gemini(self):
        import llm_client
        with patch.object(llm_client, "LLM_PROVIDER", "gemini"):
            with patch.object(llm_client, "_query_gemini", return_value="ok") as mock:
                result = llm_client.query_llm("q", self.FAKE_B64)
            mock.assert_called_once_with("q", self.FAKE_B64)
            self.assertEqual(result, "ok")

    def test_provider_matching_is_case_insensitive(self):
        import llm_client
        with patch.object(llm_client, "LLM_PROVIDER", "OpenAI"):
            with patch.object(llm_client, "_query_openai", return_value="ok"):
                result = llm_client.query_llm("q", self.FAKE_B64)
            self.assertEqual(result, "ok")


class TestOpenAiCompatibility(unittest.TestCase):
    FAKE_B64 = base64.b64encode(b"fake-png-data").decode()

    def _install_fake_openai(self, create_side_effect):
        fake_openai = types.ModuleType("openai")

        create_mock = MagicMock(side_effect=create_side_effect)
        fake_client = types.SimpleNamespace(
            chat=types.SimpleNamespace(
                completions=types.SimpleNamespace(create=create_mock)
            )
        )

        class FakeOpenAI:
            def __init__(self, api_key):
                self.api_key = api_key
                self.chat = fake_client.chat

        fake_openai.OpenAI = FakeOpenAI
        return fake_openai, create_mock

    def test_openai_does_not_send_output_token_limit(self):
        import llm_client

        response = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))]
        )
        fake_openai, create_mock = self._install_fake_openai(lambda **kwargs: response)

        with patch.dict(sys.modules, {"openai": fake_openai}):
            result = llm_client._query_openai("hello", self.FAKE_B64)

        self.assertEqual(result, "ok")
        self.assertEqual(create_mock.call_count, 1)
        self.assertNotIn("max_completion_tokens", create_mock.call_args.kwargs)
        self.assertNotIn("max_tokens", create_mock.call_args.kwargs)


# ---------------------------------------------------------------------------
# Tests for the Flask app endpoints
# ---------------------------------------------------------------------------

class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        # Patch take_screenshot and query_llm before importing app so the
        # real mss / LLM libraries are never touched.
        self._ss_patcher = patch("screenshot.take_screenshot",
                                 return_value=(b"png", "ZmFrZQ=="))
        self._llm_patcher = patch("llm_client.query_llm",
                                  return_value="The answer is 42.")
        self._ss_patcher.start()
        self._llm_patcher.start()

        import app as flask_app
        flask_app.app.config["TESTING"] = True
        self.client = flask_app.app.test_client()

    def tearDown(self):
        self._ss_patcher.stop()
        self._llm_patcher.stop()

    def test_index_returns_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"My Assistant", resp.data)

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "ok")

    def test_capture_config_endpoint(self):
        resp = self.client.get("/capture-config")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("screen_region", data)
        self.assertIn("browser", data)
        self.assertIn("scroll", data["browser"])
        self.assertEqual(data["browser"]["scroll"]["unchanged_frame_limit"], 3)

    def test_ask_returns_llm_response(self):
        resp = self.client.post(
            "/ask",
            data=json.dumps({"prompt": "What is this?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("response", data)
        self.assertEqual(data["response"], "The answer is 42.")

    def test_ask_missing_prompt_field(self):
        resp = self.client.post(
            "/ask",
            data=json.dumps({"question": "oops"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("error", data)

    def test_ask_empty_prompt(self):
        resp = self.client.post(
            "/ask",
            data=json.dumps({"prompt": "   "}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("error", data)

    def test_ask_non_json_body(self):
        resp = self.client.post(
            "/ask",
            data="not json",
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, 400)

    def test_ask_propagates_llm_error(self):
        with patch("app.query_llm", side_effect=RuntimeError("API error")):
            resp = self.client.post(
                "/ask",
                data=json.dumps({"prompt": "test"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("error", data)

    def test_ask_propagates_screenshot_error(self):
        with patch("app.take_screenshot", side_effect=RuntimeError("no display")):
            resp = self.client.post(
                "/ask",
                data=json.dumps({"prompt": "test"}),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
