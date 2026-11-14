import sys
import unittest
from types import ModuleType
from unittest.mock import Mock, patch


def _dependency_stub(name, **exports):
    module = ModuleType(name)
    for export_name, export in exports.items():
        setattr(module, export_name, export)
    return module


with patch.dict(
    sys.modules,
    {
        "audio_module": _dependency_stub("audio_module", AudioProcessor=Mock),
        "text_similarity": _dependency_stub("text_similarity", TextSimilarity=Mock),
        "text_context": _dependency_stub("text_context", TextContext=Mock),
        "llm_module": _dependency_stub("llm_module", LLM=Mock),
        "colors": _dependency_stub("colors", Colors=Mock),
    },
):
    import speech_pipeline_manager as pipeline_module


class SpeechPipelineManagerTests(unittest.TestCase):
    def setUp(self):
        self.audio = Mock()
        self.audio.tts_inference_time = 1.0
        self.llm = Mock()

    def test_unavailable_llm_backend_raises_actionable_startup_error(self):
        self.llm.prewarm.return_value = False

        with (
            patch.object(pipeline_module, "AudioProcessor", return_value=self.audio),
            patch.object(pipeline_module, "TextSimilarity", return_value=Mock()),
            patch.object(pipeline_module, "TextContext", return_value=Mock()),
            patch.object(pipeline_module, "LLM", return_value=self.llm),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "LLM backend 'ollama' failed startup prewarm for model 'test-model'",
            ):
                pipeline_module.SpeechPipelineManager(
                    llm_provider="ollama",
                    llm_model="test-model",
                )

        self.llm.measure_inference_time.assert_not_called()

    def test_missing_inference_measurement_raises_startup_error(self):
        self.llm.prewarm.return_value = True
        self.llm.measure_inference_time.return_value = None

        with (
            patch.object(pipeline_module, "AudioProcessor", return_value=self.audio),
            patch.object(pipeline_module, "TextSimilarity", return_value=Mock()),
            patch.object(pipeline_module, "TextContext", return_value=Mock()),
            patch.object(pipeline_module, "LLM", return_value=self.llm),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "LLM backend 'ollama' did not produce a measurable response",
            ):
                pipeline_module.SpeechPipelineManager(
                    llm_provider="ollama",
                    llm_model="test-model",
                )
