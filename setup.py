import argparse
import hashlib
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "code"))

from server_security import configure_lan_server, get_default_lan_host


def _client_setup() -> None:
    server_url = input("Server HTTPS URL (for example https://192.168.1.25:8000): ").strip()
    try:
        parsed = urlsplit(server_url)
        parsed.port
    except ValueError as error:
        raise ValueError("Enter a valid server HTTPS URL and port.") from error
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Enter an HTTPS URL without embedded credentials.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Enter only the server origin, without a path, query, or fragment.")
    print("Before connecting, trust the server CA certificate on this device.")
    print("The server administrator can share code/data/server-ca.crt with you.")
    print("Then open the client page and enter the server access token when prompted.")
    input("Press Enter after trusting the CA certificate to open the client page...")
    webbrowser.open(server_url)


def _server_setup() -> None:
    default_host = get_default_lan_host()
    lan_host = input(f"Server LAN IP or hostname [{default_host}]: ").strip() or default_host
    token = configure_lan_server(lan_host)
    print()
    print("LAN server security has been configured.")
    formatted_host = f"[{lan_host}]" if ":" in lan_host and not lan_host.startswith("[") else lan_host
    print(f"Client URL: https://{formatted_host}:8000")
    ca_path = ROOT / "code" / "data" / "server-ca.crt"
    print(f"Share this CA certificate with each client: {ca_path}")
    print(f"CA SHA-256 fingerprint: {hashlib.sha256(ca_path.read_bytes()).hexdigest()}")
    print("Clients must trust the CA certificate before opening the client URL.")
    print("Share this access token with trusted users; it is shown only once:")
    print(token)
    print()
    print("Start the server with: cd code, then python server.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure a Real-Time Voice Chat server or client.")
    parser.add_argument("--client", action="store_true", help="Configure a thin client connection.")
    parser.add_argument("--configure-server", action="store_true", help="Configure secure LAN server mode.")
    args = parser.parse_args()
    if args.client and args.configure_server:
        parser.error("Choose either --client or --configure-server.")

    if args.client:
        _client_setup()
    elif args.configure_server:
        _server_setup()
    else:
        print("1) Set up this computer as a server")
        print("2) Connect as a client (no AI dependencies are installed)")
        choice = input("Choose 1 or 2: ").strip()
        if choice == "1":
            _server_setup()
        elif choice == "2":
            _client_setup()
        else:
            raise ValueError("Choose 1 for server or 2 for client.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
