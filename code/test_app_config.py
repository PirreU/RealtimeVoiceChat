import pytest

from app_config import AppSettings, validate_settings


def test_default_settings_are_valid():
    settings = validate_settings(AppSettings())
    assert settings.llm_provider == "ollama"
    assert settings.llm_model
    assert settings.tts_engine == "coqui"


def test_custom_openai_compatible_requires_base_url():
    with pytest.raises(ValueError, match="base URL"):
        validate_settings(AppSettings(llm_provider="openai_compatible", llm_base_url=""))


def test_rejects_unsafe_url_values():
    with pytest.raises(ValueError, match="valid HTTP or HTTPS URL"):
        validate_settings(AppSettings(llm_provider="openai_compatible", llm_base_url="file:///tmp/test"))


def test_allows_valid_local_openai_compatible_url():
    settings = validate_settings(
        AppSettings(
            llm_provider="openai_compatible",
            llm_base_url="http://127.0.0.1:8080/v1",
        )
    )
    assert settings.llm_base_url == "http://127.0.0.1:8080/v1"
