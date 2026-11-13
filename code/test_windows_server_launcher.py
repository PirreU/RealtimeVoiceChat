import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest import mock

from windows_server_launcher import main


class WindowsServerLauncherTests(unittest.TestCase):
    def test_sets_certifi_bundle_before_server_startup(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with (
                mock.patch("windows_server_launcher.certifi.where", return_value="test-ca-bundle.pem"),
                mock.patch("windows_server_launcher.runpy.run_path") as run_server,
                mock.patch("builtins.input", return_value=""),
            ):
                with self.assertRaises(SystemExit) as exit_info:
                    main()
                self.assertEqual(os.environ["SSL_CERT_FILE"], "test-ca-bundle.pem")
                self.assertEqual(exit_info.exception.code, 0)
                run_server.assert_called_once()

    def test_server_startup_error_is_shown_before_console_waits(self):
        original_directory = os.getcwd()
        original_path = sys.path[:]
        output = StringIO()
        errors = StringIO()

        try:
            with (
                mock.patch(
                    "windows_server_launcher.runpy.run_path",
                    side_effect=RuntimeError("visible startup error"),
                ),
                mock.patch("builtins.input", return_value="") as wait_for_close,
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                with self.assertRaises(SystemExit) as exit_info:
                    main()
        finally:
            os.chdir(original_directory)
            sys.path[:] = original_path

        self.assertEqual(exit_info.exception.code, 1)
        self.assertIn("visible startup error", errors.getvalue())
        wait_for_close.assert_called_once_with("\nPress Enter to close this window...")


if __name__ == "__main__":
    unittest.main()
