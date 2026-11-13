import unittest

from windows_gui_installer import validate_lan_host, validate_server_url


class WindowsGuiInstallerTests(unittest.TestCase):
    def test_server_url_defaults_to_application_port(self):
        self.assertEqual(
            validate_server_url("https://voicebox.local"),
            "https://voicebox.local:8000",
        )

    def test_server_url_preserves_ipv6_and_explicit_port(self):
        self.assertEqual(
            validate_server_url("https://[fd00::10]:8443/"),
            "https://[fd00::10]:8443",
        )

    def test_server_url_rejects_non_https_and_embedded_paths(self):
        for value in ("http://voicebox.local:8000", "https://user@voicebox.local:8000", "https://voicebox.local/chat"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_server_url(value)

    def test_server_host_rejects_loopback_and_wildcard(self):
        for value in ("127.0.0.1", "::1", "0.0.0.0", "bad host"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_lan_host(value)

    def test_server_host_accepts_private_ip_and_hostname(self):
        self.assertEqual(validate_lan_host("192.168.1.25"), "192.168.1.25")
        self.assertEqual(validate_lan_host("voicebox.local"), "voicebox.local")


if __name__ == "__main__":
    unittest.main()
