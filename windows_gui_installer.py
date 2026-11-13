import ipaddress
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk
from urllib.parse import urlsplit


APP_NAME = "Real-Time Voice Chat"
APP_DIR_NAME = "RealtimeVoiceChat"
PYTHON_VERSION = "3.11"
VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
TORCH_PACKAGES = (
    "torch==2.5.1+cu121",
    "torchaudio==2.5.1+cu121",
    "torchvision==0.20.1",
)


def _is_vc_redist_x64_installed() -> bool:
    try:
        import winreg
    except ImportError as error:
        raise RuntimeError("Windows registry access is required to check the Visual C++ runtime.") from error

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
        ) as key:
            installed, _ = winreg.QueryValueEx(key, "Installed")
    except FileNotFoundError:
        return False
    return installed == 1


def _resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def default_lan_host() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 80))
            address = probe.getsockname()[0]
            if not ipaddress.ip_address(address).is_loopback:
                return address
    except OSError:
        pass
    return socket.gethostname()


def validate_lan_host(value: str) -> str:
    host = value.strip()
    if not host or host.casefold() == "localhost" or any(character.isspace() for character in host):
        raise ValueError("Enter the server's LAN IP address or hostname.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        labels = host.rstrip(".").split(".")
        if len(host) > 253 or not all(
            len(label) <= 63
            and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
            for label in labels
        ):
            raise ValueError("Enter a valid server IP address or hostname.")
    else:
        if address.is_loopback or address.is_unspecified:
            raise ValueError("Enter the server's LAN IP address, not localhost or a wildcard address.")
    return host


def validate_server_url(value: str) -> str:
    raw_url = value.strip()
    try:
        parsed = urlsplit(raw_url)
        port = parsed.port
    except ValueError as error:
        raise ValueError("Enter a valid HTTPS server URL and port.") from error
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("The server URL port must be between 1 and 65535.")
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or any(character.isspace() for character in parsed.hostname)
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter an HTTPS server URL without credentials, path, query, or fragment.")
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    return f"https://{host}:{8000 if port is None else port}"


def create_server_desktop_shortcut(destination: Path) -> Path:
    python_executable = destination / "venv" / "Scripts" / "python.exe"
    code_directory = destination / "code"
    icon_path = code_directory / "static" / "favicon.ico"
    if not python_executable.is_file():
        raise FileNotFoundError(f"Managed Python executable is missing: {python_executable}")
    launcher_script = code_directory / "windows_server_launcher.py"
    if not launcher_script.is_file():
        raise FileNotFoundError(f"Server launcher is missing: {launcher_script}")

    powershell = shutil.which("powershell.exe")
    if not powershell:
        raise RuntimeError("Windows PowerShell is required to create the server desktop shortcut.")

    environment = os.environ.copy()
    environment.update({
        "RVCHAT_SERVER_PYTHON": str(python_executable),
        "RVCHAT_SERVER_LAUNCHER": str(launcher_script),
        "RVCHAT_SERVER_WORKDIR": str(code_directory),
        "RVCHAT_SERVER_ICON": str(icon_path),
    })
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$shell = New-Object -ComObject WScript.Shell; "
        "$desktop = [Environment]::GetFolderPath('Desktop'); "
        "if ([string]::IsNullOrWhiteSpace($desktop)) { throw 'Could not locate the Desktop folder.' }; "
        "$shortcutPath = Join-Path $desktop 'Real-Time Voice Chat Server.lnk'; "
        "$shortcut = $shell.CreateShortcut($shortcutPath); "
        "$shortcut.TargetPath = $env:RVCHAT_SERVER_PYTHON; "
        "$shortcut.Arguments = 'windows_server_launcher.py'; "
        "$shortcut.WorkingDirectory = $env:RVCHAT_SERVER_WORKDIR; "
        "$shortcut.Description = 'Start the Real-Time Voice Chat server and keep startup errors visible.'; "
        "$shortcut.IconLocation = $env:RVCHAT_SERVER_ICON + ',0'; "
        "$shortcut.WindowStyle = 1; "
        "$shortcut.Save(); "
        "Write-Output $shortcutPath"
    )
    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        details = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Could not create the server desktop shortcut: {details}")

    output_lines = result.stdout.strip().splitlines()
    if not output_lines:
        raise RuntimeError("PowerShell did not return the server desktop shortcut path.")
    shortcut_path = Path(output_lines[-1])
    if not shortcut_path.is_file():
        raise RuntimeError(f"Server desktop shortcut was not created: {shortcut_path}")
    return shortcut_path


class InstallerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[tuple] = queue.Queue()
        self.role = tk.StringVar(value="server")
        self.host = tk.StringVar(value=default_lan_host())
        self.install_dir = tk.StringVar(
            value=str(Path(os.environ["LOCALAPPDATA"]) / "Programs" / APP_DIR_NAME)
        )
        self.server_url = tk.StringVar()
        self.trusted_ca = tk.BooleanVar(value=False)
        self.last_token = ""

        root.title(f"{APP_NAME} Setup")
        root.geometry("760x650")
        root.minsize(700, 580)

        ttk.Label(root, text="Real-Time Voice Chat", font=("Segoe UI", 18, "bold")).pack(
            anchor="w", padx=20, pady=(18, 2)
        )
        ttk.Label(
            root,
            text="Choose how this computer will be used. The client does not install the AI stack.",
            wraplength=700,
        ).pack(anchor="w", padx=20, pady=(0, 14))

        role_frame = ttk.LabelFrame(root, text="This computer is a")
        role_frame.pack(fill="x", padx=20, pady=(0, 10))
        ttk.Radiobutton(
            role_frame, text="Server — install speech and AI components", variable=self.role,
            value="server", command=self._role_changed,
        ).pack(anchor="w", padx=12, pady=(8, 2))
        ttk.Radiobutton(
            role_frame, text="Client — connect to an existing server", variable=self.role,
            value="client", command=self._role_changed,
        ).pack(anchor="w", padx=12, pady=(2, 8))

        self.server_frame = ttk.LabelFrame(root, text="Server setup")
        ttk.Label(self.server_frame, text="Server LAN IP address or hostname:").grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4)
        )
        ttk.Entry(self.server_frame, textvariable=self.host).grid(
            row=1, column=0, sticky="ew", padx=10, pady=(0, 8)
        )
        ttk.Label(self.server_frame, text="Install folder:").grid(
            row=2, column=0, sticky="w", padx=10, pady=(0, 4)
        )
        path_row = ttk.Frame(self.server_frame)
        path_row.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 8))
        ttk.Entry(path_row, textvariable=self.install_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="Browse...", command=self._browse_folder).pack(side="left", padx=(8, 0))
        ttk.Label(
            self.server_frame,
            text=(
                "The installer downloads a private Python 3.11 runtime and the AI packages. "
                "This requires an internet connection and several GB of free disk space."
            ),
            wraplength=680,
        ).grid(row=4, column=0, sticky="w", padx=10, pady=(0, 10))
        self.server_frame.columnconfigure(0, weight=1)

        self.client_frame = ttk.LabelFrame(root, text="Client setup")
        ttk.Label(self.client_frame, text="Server HTTPS URL (for example https://192.168.1.25:8000):").pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        ttk.Entry(self.client_frame, textvariable=self.server_url).pack(
            fill="x", padx=10, pady=(0, 8)
        )
        ttk.Label(
            self.client_frame,
            text=(
                "Ask the server administrator for the CA certificate and access token. "
                "Trust the certificate on this device before connecting."
            ),
            wraplength=680,
        ).pack(anchor="w", padx=10, pady=(0, 6))
        ttk.Checkbutton(
            self.client_frame,
            text="I have trusted the server's CA certificate on this device",
            variable=self.trusted_ca,
        ).pack(anchor="w", padx=10, pady=(0, 10))

        self.server_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.client_frame.pack_forget()

        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill="x", padx=20, pady=(2, 6))
        self.status = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status).pack(anchor="w", padx=20, pady=(0, 4))

        self.log = scrolledtext.ScrolledText(root, height=12, wrap=tk.WORD, state=tk.DISABLED)
        self.log.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        button_row = ttk.Frame(root)
        button_row.pack(fill="x", padx=20, pady=(0, 16))
        self.copy_token_button = ttk.Button(
            button_row, text="Copy access token", command=self._copy_token, state=tk.DISABLED
        )
        self.copy_token_button.pack(side="left")
        self.action_button = ttk.Button(button_row, text="Install Server", command=self._start_action)
        self.action_button.pack(side="right")
        self.close_button = ttk.Button(button_row, text="Close Setup", command=self.root.destroy)
        self.close_button.pack(side="right", padx=(0, 8))

        self._poll_events()

    def _role_changed(self) -> None:
        if self.role.get() == "server":
            self.client_frame.pack_forget()
            self.server_frame.pack(fill="x", padx=20, pady=(0, 10))
            self.action_button.config(text="Install Server")
        else:
            self.server_frame.pack_forget()
            self.client_frame.pack(fill="x", padx=20, pady=(0, 10))
            self.action_button.config(text="Connect")

    def _browse_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.install_dir.get())
        if selected:
            self.install_dir.set(selected)

    def _start_action(self) -> None:
        if self.role.get() == "client":
            self._connect_client()
            return
        try:
            host = validate_lan_host(self.host.get())
            destination = Path(self.install_dir.get()).expanduser()
            if not destination.is_absolute():
                raise ValueError("Choose an absolute installation folder path.")
            if destination.exists() and any(destination.iterdir()):
                marker = destination / ".rvchat-installer.json"
                if not marker.is_file():
                    raise ValueError(
                        "The selected folder is not empty. Choose an empty folder to avoid overwriting files."
                    )
        except (OSError, ValueError) as error:
            messagebox.showerror("Check server setup", str(error), parent=self.root)
            return

        self.action_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.DISABLED)
        self.copy_token_button.config(state=tk.DISABLED)
        self.progress.start(12)
        self.status.set("Preparing server installation...")
        self._append_log("Starting server installation. Keep this window open.")
        threading.Thread(
            target=self._install_server,
            args=(host, destination),
            daemon=True,
        ).start()

    def _connect_client(self) -> None:
        try:
            server_url = validate_server_url(self.server_url.get())
        except ValueError as error:
            messagebox.showerror("Check server URL", str(error), parent=self.root)
            return
        if not self.trusted_ca.get():
            messagebox.showwarning(
                "Trust the server certificate",
                "Import the CA certificate provided by the server administrator, then select the checkbox.",
                parent=self.root,
            )
            return
        if not webbrowser.open(server_url):
            messagebox.showerror("Could not open browser", f"Open this URL manually:\n{server_url}")
            return
        self.status.set(f"Opened {server_url}. Enter the server access token when prompted.")

    def _install_server(self, host: str, destination: Path) -> None:
        try:
            destination.mkdir(parents=True, exist_ok=True)
            marker = destination / ".rvchat-installer.json"
            if not marker.exists():
                marker.write_text(
                    json.dumps({"installer": 1, "python": PYTHON_VERSION}) + "\n",
                    encoding="utf-8",
                )

            resources = _resource_root()
            source_code = resources / "code"
            if not source_code.is_dir():
                raise FileNotFoundError(f"Bundled application source is missing: {source_code}")
            shutil.copytree(
                source_code,
                destination / "code",
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "test_*.py", "data"),
            )
            for filename in ("setup.py", "requirements.txt"):
                shutil.copy2(resources / filename, destination / filename)

            self._ensure_vc_redist_x64()

            uv_source = resources / "uv.exe"
            if not uv_source.is_file():
                uv_source = Path(shutil.which("uv") or "")
            if not uv_source.is_file():
                raise FileNotFoundError("The bundled Python runtime manager (uv.exe) is missing.")
            tools_dir = destination / "tools"
            tools_dir.mkdir(exist_ok=True)
            uv_executable = tools_dir / "uv.exe"
            shutil.copy2(uv_source, uv_executable)

            python_dir = destination / "runtime"
            cache_dir = destination / ".uv-cache"
            environment = os.environ.copy()
            environment["UV_PYTHON_INSTALL_DIR"] = str(python_dir)
            environment["UV_PYTHON_BIN_DIR"] = str(destination / "runtime-bin")
            environment["UV_CACHE_DIR"] = str(cache_dir)
            environment["UV_NO_PROGRESS"] = "1"

            self._set_status("Installing managed Python 3.11...")
            self._run_command(
                [str(uv_executable), "--managed-python", "python", "install", PYTHON_VERSION],
                destination,
                environment,
            )

            virtual_env = destination / "venv"
            python_executable = virtual_env / "Scripts" / "python.exe"
            if not python_executable.is_file():
                self._set_status("Creating the application environment...")
                self._run_command(
                    [
                        str(uv_executable), "--managed-python", "venv", "--python",
                        PYTHON_VERSION, str(virtual_env),
                    ],
                    destination,
                    environment,
                )

            self._set_status("Installing CUDA-enabled PyTorch...")
            self._run_command(
                [
                    str(uv_executable), "pip", "install", "--python", str(python_executable),
                    "--index-url", "https://download.pytorch.org/whl/cu121", *TORCH_PACKAGES,
                ],
                destination,
                environment,
            )
            self._set_status("Installing speech and web application dependencies...")
            self._run_command(
                [
                    str(uv_executable), "pip", "install", "--python", str(python_executable),
                    "-r", str(destination / "requirements.txt"),
                ],
                destination,
                environment,
            )

            config_path = destination / "code" / "data" / "server.json"
            if not config_path.is_file():
                self._set_status("Configuring private-LAN HTTPS and access token...")
                setup_output = self._run_command(
                    [
                        str(python_executable), str(destination / "setup.py"),
                        "--configure-server", "--host", host,
                    ],
                    destination,
                    environment,
                )
                self._set_result(host, setup_output, destination)
            else:
                self._set_result(host, [], destination)
            shortcut_path = create_server_desktop_shortcut(destination)
            self._append_log(f"Desktop shortcut created: {shortcut_path}")
            try:
                shutil.rmtree(cache_dir)
            except FileNotFoundError:
                pass
            except OSError as error:
                self._append_log(f"Could not remove temporary package cache: {error}")
            self.events.put(("done", True, str(destination), ""))
        except Exception as error:
            self.events.put(("done", False, str(destination), str(error)))

    def _ensure_vc_redist_x64(self) -> None:
        if _is_vc_redist_x64_installed():
            self._append_log("Microsoft Visual C++ Redistributable (x64) is already installed.")
            return

        powershell = shutil.which("powershell.exe")
        if not powershell:
            raise RuntimeError("Windows PowerShell is required to install the Visual C++ runtime.")

        self._set_status("Installing Microsoft Visual C++ Redistributable (x64)...")
        with tempfile.TemporaryDirectory(prefix="rvchat-vc-redist-") as temporary_directory:
            installer_path = Path(temporary_directory) / "vc_redist.x64.exe"
            urllib.request.urlretrieve(VC_REDIST_URL, installer_path)
            environment = os.environ.copy()
            environment["RVCHAT_VC_REDIST_PATH"] = str(installer_path)
            script = (
                "$ErrorActionPreference = 'Stop'; "
                "$signature = Get-AuthenticodeSignature -FilePath $env:RVCHAT_VC_REDIST_PATH; "
                "if ($signature.Status -ne 'Valid' -or "
                "$signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { "
                "throw 'The downloaded Visual C++ runtime does not have a valid Microsoft signature.' }; "
                "$process = Start-Process -FilePath $env:RVCHAT_VC_REDIST_PATH "
                "-ArgumentList '/install /quiet /norestart' -Verb RunAs -Wait -PassThru; "
                "exit $process.ExitCode"
            )
            result = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        if result.returncode not in (0, 3010):
            details = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
            raise RuntimeError(f"Could not install the Visual C++ runtime: {details}")
        if result.returncode == 3010:
            self._append_log("Windows requested a restart to finish installing the Visual C++ runtime.")
        else:
            self._append_log("Microsoft Visual C++ Redistributable (x64) installed.")

    def _run_command(self, command: list[str], cwd: Path, environment: dict[str, str]) -> list[str]:
        self._append_log("> " + subprocess.list2cmdline(command))
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = []
        assert process.stdout is not None
        for line in process.stdout:
            output.append(line.rstrip())
            self._append_log(line.rstrip())
        return_code = process.wait()
        if return_code:
            raise RuntimeError(f"Command failed with exit code {return_code}. See the log for details.")
        return output

    def _set_status(self, message: str) -> None:
        self.events.put(("status", message))
        self._append_log(message)

    def _append_log(self, message: str) -> None:
        self.events.put(("log", message))

    def _set_result(self, host: str, output: list[str], destination: Path) -> None:
        marker = "Share this access token with trusted users; it is shown only once:"
        token = ""
        if marker in output:
            token_index = output.index(marker) + 1
            if token_index < len(output):
                token = output[token_index].strip()
        if token:
            self.last_token = token
            self.events.put(("token", token))
        else:
            config_path = destination / "code" / "data" / "server.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            host = config.get("lan_host", host)
            self._append_log(
                "Existing server credentials were preserved. The saved token cannot be recovered; "
                "run setup.py --configure-server to generate new credentials if it was lost."
            )
        formatted_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        url = f"https://{formatted_host}:8000"
        ca_path = destination / "code" / "data" / "server-ca.crt"
        self._append_log(f"Server URL: {url}")
        self._append_log(f"CA certificate: {ca_path}")
        self._append_log("Start the server from the Real-Time Voice Chat Server desktop shortcut.")

    def _copy_token(self) -> None:
        if self.last_token:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_token)
            self.status.set("Access token copied to the clipboard.")

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "log":
                    self.log.configure(state=tk.NORMAL)
                    self.log.insert(tk.END, event[1] + "\n")
                    self.log.see(tk.END)
                    self.log.configure(state=tk.DISABLED)
                elif kind == "status":
                    self.status.set(event[1])
                elif kind == "token":
                    self.copy_token_button.config(state=tk.NORMAL)
                elif kind == "done":
                    _, succeeded, destination, error = event
                    self.progress.stop()
                    self.action_button.config(state=tk.NORMAL)
                    self.close_button.config(state=tk.NORMAL)
                    if succeeded:
                        self.action_button.config(text="Open install folder", command=lambda: os.startfile(destination))
                        self.status.set("Server installation is ready.")
                        token_message = (
                            "Copy the access token from the log and share it only with trusted clients."
                            if self.last_token
                            else "The previous access token was preserved but cannot be displayed again."
                        )
                        messagebox.showinfo(
                            "Installation complete",
                            "The server is ready.\n\n"
                            f"Open this URL on the server computer:\nhttps://localhost:8000\n\n"
                            "Start it from the Real-Time Voice Chat Server desktop shortcut. "
                            "Its console shows startup errors and stays open when the server stops. "
                            "Press Ctrl+C or close the console window to stop the server. "
                            f"{token_message}\nShare code/data/server-ca.crt only with trusted clients.",
                            parent=self.root,
                        )
                    else:
                        self.status.set("Installation failed. Details are shown in the log.")
                        messagebox.showerror("Installation failed", error, parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)


def main() -> None:
    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
