import hashlib
import hmac
import json
import os
import re
import secrets
import socket
from datetime import datetime, timedelta
from ipaddress import ip_address
from pathlib import Path
from typing import Any


_DATA_DIR = Path(__file__).resolve().parent / "data"
SERVER_CONFIG_PATH = _DATA_DIR / "server.json"
_SERVER_CONFIG_DEFAULTS = {
    "mode": "local",
    "bind_host": "127.0.0.1",
    "port": 8000,
    "access_token_hash": "",
    "certificate": "",
    "private_key": "",
    "lan_host": "",
}


def load_server_config() -> dict[str, Any]:
    try:
        config = json.loads(SERVER_CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return dict(_SERVER_CONFIG_DEFAULTS)
    except json.JSONDecodeError as error:
        raise ValueError(f"Server configuration is not valid JSON: {SERVER_CONFIG_PATH}") from error

    if not isinstance(config, dict):
        raise ValueError(f"Server configuration must be a JSON object: {SERVER_CONFIG_PATH}")

    merged = dict(_SERVER_CONFIG_DEFAULTS)
    merged.update(config)
    if not isinstance(merged["mode"], str) or merged["mode"] not in {"local", "server"}:
        raise ValueError("Server mode must be 'local' or 'server'.")
    if type(merged["port"]) is not int or not 1 <= merged["port"] <= 65535:
        raise ValueError("Server port must be an integer from 1 to 65535.")
    if not isinstance(merged["bind_host"], str) or not merged["bind_host"]:
        raise ValueError("Server bind host must be a non-empty string.")
    if merged["mode"] == "server":
        if not isinstance(merged["access_token_hash"], str) or not re.fullmatch(
            r"[a-f0-9]{64}", merged["access_token_hash"]
        ):
            raise ValueError("LAN server access token hash is invalid. Run setup.py to configure the server again.")
        if not all(
            isinstance(merged[field], str) and merged[field]
            for field in ("certificate", "private_key", "lan_host")
        ):
            raise ValueError("LAN server configuration is incomplete. Run setup.py and configure the server again.")
    return merged


def verify_access_token(token: object, expected_hash: str) -> bool:
    if not isinstance(token, str) or not token or not expected_hash:
        return False
    actual_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual_hash, expected_hash)


def get_default_lan_host() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 80))
            address = probe.getsockname()[0]
            if not ip_address(address).is_loopback:
                return address
    except OSError:
        pass
    return socket.gethostname()


def configure_lan_server(lan_host: str) -> str:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    except ImportError as error:
        raise RuntimeError("The cryptography package is required to create HTTPS certificates.") from error

    lan_host = lan_host.strip()
    if not lan_host or any(character.isspace() for character in lan_host):
        raise ValueError("Enter a valid server IP address or hostname.")
    try:
        host_address = ip_address(lan_host)
    except ValueError as error:
        labels = lan_host.rstrip(".").split(".")
        valid_hostname = (
            len(lan_host) <= 253
            and all(
                len(label) <= 63
                and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
                for label in labels
            )
        )
        if not valid_hostname:
            raise ValueError("Enter a valid server IP address or hostname.") from error
    else:
        if host_address.is_loopback or host_address.is_unspecified:
            raise ValueError("Enter the server's private LAN IP address, not a loopback or wildcard address.")

    now = datetime.utcnow()
    valid_until = now + timedelta(days=3650)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "RealtimeVoiceChat Local CA")])
    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(valid_until)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, lan_host)])
    dns_names = {"localhost"}
    machine_hostname = socket.gethostname()
    if re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", machine_hostname):
        dns_names.add(machine_hostname)
    alternate_names = [x509.DNSName(name) for name in sorted(dns_names)]
    try:
        alternate_names.append(x509.IPAddress(ip_address(lan_host)))
    except ValueError:
        alternate_names.append(x509.DNSName(lan_host))
    alternate_names.append(x509.IPAddress(ip_address("127.0.0.1")))

    server_certificate = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(valid_until)
        .add_extension(x509.SubjectAlternativeName(alternate_names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    certificate_path = _DATA_DIR / "server.crt"
    private_key_path = _DATA_DIR / "server.key"
    ca_path = _DATA_DIR / "server-ca.crt"
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    certificate_path.write_bytes(server_certificate.public_bytes(serialization.Encoding.PEM))
    private_key_path.write_bytes(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    ca_path.write_bytes(ca_certificate.public_bytes(serialization.Encoding.PEM))
    try:
        os.chmod(private_key_path, 0o600)
    except OSError:
        pass

    access_token = secrets.token_urlsafe(32)
    config = {
        "mode": "server",
        "bind_host": "0.0.0.0",
        "port": 8000,
        "access_token_hash": hashlib.sha256(access_token.encode("utf-8")).hexdigest(),
        "certificate": str(certificate_path),
        "private_key": str(private_key_path),
        "ca_certificate": str(ca_path),
        "lan_host": lan_host,
    }
    temporary_path = SERVER_CONFIG_PATH.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary_path, SERVER_CONFIG_PATH)
    return access_token
