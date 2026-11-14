import json
import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field


_CODE_DIR = Path(__file__).resolve().parent
_SETTINGS_PATH = _CODE_DIR / "data" / "settings.json"
_SETTINGS_LOCK = threading.Lock()


def _default_system_prompt() -> str:
    prompt_path = _CODE_DIR / "system_prompt.txt"
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "You are a helpful assistant."


class AppSettings(BaseModel):
    llm_provider: Literal["ollama", "openai", "lmstudio", "openai_compatible"] = "ollama"
    llm_model: str = Field(
        "hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M",
        min_length=1,
        max_length=200,
    )
    llm_base_url: str = Field("", max_length=400)
    tts_engine: Literal["coqui", "kokoro", "orpheus"] = "coqui"
    tts_model: str = Field(
        "orpheus-3b-0.1-ft-Q8_0-GGUF/orpheus-3b-0.1-ft-q8_0.gguf",
        min_length=1,
        max_length=200,
    )
    tts_voice: str = Field("reference_audio.wav", min_length=1, max_length=200)
    tts_speed: float = Field(1.1, ge=0.5, le=2.0)
    turn_speed: int = Field(0, ge=0, le=100)
    stt_language: str = Field("en", min_length=2, max_length=15)
    stt_model: str = Field("base.en", min_length=1, max_length=100)
    system_prompt: str = Field(default_factory=_default_system_prompt, max_length=10000)


class ProviderProbeRequest(BaseModel):
    llm_provider: Literal["ollama", "openai", "lmstudio", "openai_compatible"]
    llm_model: str = Field(..., min_length=1, max_length=200)
    llm_base_url: str = Field("", max_length=400)


def settings_to_dict(settings: AppSettings) -> dict:
    if hasattr(settings, "model_dump"):
        return settings.model_dump()
    return settings.dict()


def validate_settings(settings: AppSettings) -> AppSettings:
    settings.llm_model = settings.llm_model.strip()
    settings.llm_base_url = settings.llm_base_url.strip()
    settings.stt_model = settings.stt_model.strip()
    settings.stt_language = settings.stt_language.strip()
    settings.tts_model = settings.tts_model.strip()
    settings.tts_voice = settings.tts_voice.strip()

    if not settings.llm_model:
        raise ValueError("Choose a model name.")
    if not settings.stt_model:
        raise ValueError("Choose a transcription model.")
    if not settings.tts_model:
        raise ValueError("Choose a text-to-speech model.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,14}", settings.stt_language):
        raise ValueError("Language must be a language code, such as 'en' or 'en-US'.")
    if not settings.tts_voice:
        raise ValueError("Choose a voice or reference audio file.")

    if settings.llm_base_url:
        parsed_url = urlsplit(settings.llm_base_url)
        try:
            has_valid_port = parsed_url.port is None or 1 <= parsed_url.port <= 65535
        except ValueError:
            has_valid_port = False
        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
            or not parsed_url.hostname
            or any(character.isspace() for character in settings.llm_base_url)
            or not has_valid_port
            or parsed_url.username is not None
            or parsed_url.password is not None
        ):
            raise ValueError("The provider URL must be a valid HTTP or HTTPS URL without credentials.")
    elif settings.llm_provider == "openai_compatible":
        raise ValueError("Enter the base URL for your OpenAI-compatible local model server.")

    if settings.tts_engine == "coqui":
        voice_path = settings.tts_voice.replace("\\", "/")
        if (
            voice_path.startswith("/")
            or re.match(r"^[A-Za-z]:", voice_path)
            or ".." in voice_path.split("/")
        ):
            raise ValueError("Coqui reference audio must be a relative path inside the code folder.")

    return settings


def load_settings() -> AppSettings:
    with _SETTINGS_LOCK:
        try:
            saved = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return AppSettings()
        except json.JSONDecodeError as error:
            raise ValueError(f"Settings file is not valid JSON: {_SETTINGS_PATH}") from error

        if not isinstance(saved, dict):
            raise ValueError(f"Settings file must contain a JSON object: {_SETTINGS_PATH}")

        try:
            return validate_settings(AppSettings(**saved))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Settings file contains invalid values: {_SETTINGS_PATH}: {error}") from error


def save_settings(settings: AppSettings) -> AppSettings:
    validated = validate_settings(settings)
    serialized = json.dumps(settings_to_dict(validated), ensure_ascii=False, indent=2)

    with _SETTINGS_LOCK:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=_SETTINGS_PATH.parent,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(serialized)
                temporary_file.write("\n")
            os.replace(temporary_path, _SETTINGS_PATH)
        except OSError:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    return validated
