import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class AppTests(unittest.TestCase):
    def test_granted_at_is_used_for_issued_time(self):
        payload = {"credits": [{"granted_at": "2026-08-12T16:00:00Z", "expires_at": "2026-08-13T17:56:41Z"}]}
        with patch.object(app, "read_token", return_value="x"), patch.object(app, "open_request", return_value=FakeResponse(payload)):
            status, cards = app.query()
        self.assertEqual(status, 200)
        self.assertEqual(cards, [("2026-08-13 00:00:00", "2026-08-14 01:56:41")])

    def test_missing_credits_is_reported(self):
        with patch.object(app, "read_token", return_value="x"), patch.object(app, "open_request", return_value=FakeResponse({"available_count": 0})):
            with self.assertRaisesRegex(app.AppError, "credits"):
                app.query()

    def test_gnome_proxy_is_used_without_environment_proxy(self):
        proxy = {"http": "http://proxy.test:8080", "https": "http://proxy.test:8080"}
        with patch.object(app.urllib.request, "getproxies", return_value={}), patch.object(
            app, "gnome_proxy_config", return_value=proxy
        ):
            self.assertEqual(app.configured_proxies(), proxy)

    def test_auth_file_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "auth.json"
            path.write_text("[]", encoding="utf-8")
            with patch.dict(app.os.environ, {"CODEX_HOME": directory}):
                with self.assertRaisesRegex(app.AppError, "顶层必须是 JSON 对象"):
                    app.read_token()

    def test_linux_uses_codex_default_path(self):
        with patch.dict(app.os.environ, {}, clear=True), patch.object(app.sys, "platform", "linux"), patch.object(app.Path, "home", return_value=Path("/portable-home")):
            self.assertEqual(app.auth_path(), Path("/portable-home/.codex/auth.json"))

    def test_non_linux_requires_codex_home(self):
        with patch.dict(app.os.environ, {}, clear=True), patch.object(app.sys, "platform", "win32"):
            with self.assertRaisesRegex(app.AppError, "CODEX_HOME"):
                app.auth_path()

    def test_invalid_time_is_safe(self):
        self.assertEqual(app.beijing_time("not-a-time"), "未知")


if __name__ == "__main__":
    unittest.main()
