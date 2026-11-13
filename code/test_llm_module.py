import unittest
from unittest.mock import patch

from llm_module import LLM


class OpenAICompatibleBackendTests(unittest.TestCase):
    def test_uses_custom_base_url_for_local_openai_compatible_server(self):
        client = object()
        with (
            patch("llm_module.OPENAI_AVAILABLE", True),
            patch("llm_module._create_openai_client", return_value=client) as create_client,
        ):
            llm = LLM(
                backend="openai_compatible",
                model="local-model",
                base_url="http://127.0.0.1:8080/v1",
            )

            self.assertTrue(llm._lazy_initialize_clients())
            self.assertIs(llm.client, client)
            create_client.assert_called_once_with(
                api_key="local-model-key",
                base_url="http://127.0.0.1:8080/v1",
            )


if __name__ == "__main__":
    unittest.main()
