import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from windows_gui_installer import (
    _is_vc_redist_x64_installed,
    _initial_window_geometry,
    create_server_desktop_shortcut,
    validate_lan_host,
    validate_server_url,
)


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
        for value in (
            "http://voicebox.local:8000",
            "https://user@voicebox.local:8000",
            "https://voicebox.local/chat",
            "https://voicebox.local:0",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_server_url(value)

    def test_server_host_rejects_loopback_and_wildcard(self):
        for value in ("127.0.0.1", "::1", "0.0.0.0", "localhost", "bad host"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_lan_host(value)

    def test_server_host_accepts_private_ip_and_hostname(self):
        self.assertEqual(validate_lan_host("192.168.1.25"), "192.168.1.25")
        self.assertEqual(validate_lan_host("voicebox.local"), "voicebox.local")

    def test_initial_window_geometry_fits_short_screen(self):
        width, height, x, y = _initial_window_geometry(800, 600)
        self.assertEqual((width, height), (680, 520))
        self.assertLessEqual(x + width, 800)
        self.assertLessEqual(y + height, 600)

        width, height, x, y = _initial_window_geometry(640, 480)
        self.assertLessEqual(width, 640)
        self.assertLessEqual(height, 480)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    @unittest.skipUnless(sys.platform == "win32", "Windows registry is required")
    def test_vc_redist_detection_handles_missing_or_installed_runtime(self):
        import winreg

        with mock.patch("winreg.OpenKey", side_effect=FileNotFoundError):
            self.assertFalse(_is_vc_redist_x64_installed())

        with (
            mock.patch("winreg.OpenKey") as open_key,
            mock.patch("winreg.QueryValueEx", return_value=(1, "v14.0")),
        ):
            self.assertTrue(_is_vc_redist_x64_installed())
            open_key.assert_called_once_with(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
            )

    def test_server_shortcut_launches_managed_python_directly(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            python_executable = destination / "venv" / "Scripts" / "python.exe"
            python_executable.parent.mkdir(parents=True)
            python_executable.touch()
            code_directory = destination / "code"
            code_directory.mkdir()
            launcher_script = code_directory / "windows_server_launcher.py"
            launcher_script.touch()
            shortcut_path = destination / "Desktop" / "Real-Time Voice Chat Server.lnk"

            def create_shortcut(command, env, **kwargs):
                script = command[-1]
                self.assertEqual(env["RVCHAT_SERVER_PYTHON"], str(python_executable))
                self.assertEqual(env["RVCHAT_SERVER_LAUNCHER"], str(launcher_script))
                self.assertEqual(env["RVCHAT_SERVER_WORKDIR"], str(code_directory))
                self.assertIn("$shortcut.TargetPath = $env:RVCHAT_SERVER_PYTHON", script)
                self.assertIn("$shortcut.Arguments = 'windows_server_launcher.py'", script)
                self.assertNotIn(".bat", script)
                shortcut_path.parent.mkdir()
                shortcut_path.touch()
                return subprocess.CompletedProcess(command, 0, f"{shortcut_path}\n", "")

            with (
                mock.patch("windows_gui_installer.shutil.which", return_value="powershell.exe"),
                mock.patch("windows_gui_installer.subprocess.run", side_effect=create_shortcut),
            ):
                created_path = create_server_desktop_shortcut(destination)

            self.assertEqual(created_path, shortcut_path)


if __name__ == "__main__":
    unittest.main()
