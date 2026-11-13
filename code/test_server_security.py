import hashlib
import tempfile
import unittest
from ipaddress import ip_address
from pathlib import Path
from unittest.mock import patch

from cryptography import x509

import server_security


class ServerSecurityTests(unittest.TestCase):
    def test_unconfigured_server_binds_to_loopback_only(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = Path(temporary_directory) / "missing.json"
            with patch.object(server_security, "SERVER_CONFIG_PATH", config_path):
                config = server_security.load_server_config()

        self.assertEqual(config["mode"], "local")
        self.assertEqual(config["bind_host"], "127.0.0.1")

    def test_access_token_verification_rejects_missing_or_wrong_tokens(self):
        self.assertTrue(server_security.verify_access_token("secret", hashlib.sha256(b"secret").hexdigest()))
        self.assertFalse(server_security.verify_access_token("", "hash"))
        self.assertFalse(server_security.verify_access_token("wrong", "hash"))
        self.assertFalse(server_security.verify_access_token(None, "hash"))

    def test_lan_configuration_creates_tls_files_and_stores_only_token_hash(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            config_path = data_dir / "server.json"
            with (
                patch.object(server_security, "_DATA_DIR", data_dir),
                patch.object(server_security, "SERVER_CONFIG_PATH", config_path),
            ):
                token = server_security.configure_lan_server("192.168.1.25")
                config = server_security.load_server_config()

            self.assertEqual(config["mode"], "server")
            self.assertTrue(server_security.verify_access_token(token, config["access_token_hash"]))
            self.assertNotIn(token, config_path.read_text(encoding="utf-8"))
            self.assertTrue(Path(config["certificate"]).is_file())
            self.assertTrue(Path(config["private_key"]).is_file())
            self.assertTrue(Path(config["ca_certificate"]).is_file())
            certificate = x509.load_pem_x509_certificate(Path(config["certificate"]).read_bytes())
            subject_alt_names = certificate.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value
            self.assertIn(x509.IPAddress(ip_address("192.168.1.25")), subject_alt_names)


if __name__ == "__main__":
    unittest.main()
