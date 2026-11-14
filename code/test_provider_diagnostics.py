import requests

from provider_diagnostics import detect_local_providers, probe_provider


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self._payload = payload

    def json(self):
        return self._payload


def test_probe_provider_reads_ollama_model_names():
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(200, {"models": [{"name": "local-model"}]})

    result = probe_provider("ollama", "http://127.0.0.1:11434/", get=fake_get)

    assert result == {"ok": True, "message": "Connected successfully.", "models": ["local-model"]}
    assert calls[0][0] == "http://127.0.0.1:11434/api/tags"
    assert calls[0][1]["timeout"] == 5
    assert calls[0][1]["allow_redirects"] is False


def test_probe_provider_reports_http_errors():
    result = probe_provider(
        "lmstudio",
        "http://127.0.0.1:1234/v1",
        get=lambda *_args, **_kwargs: FakeResponse(401, {}),
    )

    assert result["ok"] is False
    assert "HTTP 401" in result["message"]


def test_detect_only_returns_reachable_local_providers():
    def fake_get(url, **_kwargs):
        if "11434" in url:
            return FakeResponse(200, {"models": [{"name": "ollama-model"}]})
        raise requests.ConnectionError("not running")

    result = detect_local_providers(get=fake_get)

    assert result == [
        {
            "provider": "ollama",
            "base_url": "",
            "models": ["ollama-model"],
        }
    ]
