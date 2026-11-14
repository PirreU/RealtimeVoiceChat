from typing import Any, Callable, Dict, List, Optional

import requests


LOCAL_PROVIDERS = {
    "ollama": "http://127.0.0.1:11434",
    "lmstudio": "http://127.0.0.1:1234/v1",
}


def _models_from_response(response: requests.Response) -> List[str]:
    try:
        payload = response.json()
    except ValueError:
        return []

    if not isinstance(payload, dict):
        return []
    raw_models = payload.get("models")
    if not isinstance(raw_models, list):
        raw_models = payload.get("data")
    if not isinstance(raw_models, list):
        return []

    models = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("id")
        if isinstance(name, str) and name:
            models.append(name)
    return models


def _models_url(provider: str, base_url: str) -> str:
    if provider == "ollama":
        return f"{base_url.rstrip('/')}/api/tags"
    return f"{base_url.rstrip('/')}/models"


def probe_provider(
    provider: str,
    base_url: str,
    api_key: Optional[str] = None,
    get: Callable[..., requests.Response] = requests.get,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        response = get(
            _models_url(provider, base_url),
            headers=headers,
            timeout=5,
            allow_redirects=False,
        )
    except requests.RequestException as error:
        return {"ok": False, "message": f"Could not reach the provider: {error}", "models": []}

    if not 200 <= response.status_code < 300:
        return {
            "ok": False,
            "message": f"The provider returned HTTP {response.status_code}.",
            "models": [],
        }

    models = _models_from_response(response)
    return {"ok": True, "message": "Connected successfully.", "models": models}


def detect_local_providers(
    get: Callable[..., requests.Response] = requests.get,
) -> List[Dict[str, Any]]:
    detected = []
    for provider, base_url in LOCAL_PROVIDERS.items():
        result = probe_provider(provider, base_url, get=get)
        if result["ok"]:
            detected.append(
                {
                    "provider": provider,
                    "base_url": "",
                    "models": result["models"],
                }
            )
    return detected
