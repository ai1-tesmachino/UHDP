from __future__ import annotations

import base64
from collections import deque
from dataclasses import dataclass, field
import hashlib
import hmac
import ipaddress
import os
import secrets
import stat
import threading
import time
from pathlib import Path

from app.core.config import Settings


PBKDF2_ITERATIONS = 310_000
PBKDF2_SALT_BYTES = 16
PBKDF2_KEY_BYTES = 32
FAILED_ATTEMPT_LIMIT = 5
FAILED_ATTEMPT_WINDOW_SECONDS = 300
LOCKOUT_SECONDS = 600
MAX_TRACKED_PEERS = 256
INVALID_CREDENTIAL_CONFIGURATION = "invalid-local-supervisor-credential-configuration"


def load_local_supervisor_credential_hash(settings: Settings) -> str | None:
    data_directory = Path(settings.DATA_DIR)
    credential_directory = data_directory / "local_auth"
    credential_path = credential_directory / "supervisor.credential"
    if credential_directory.is_symlink() or credential_path.is_symlink():
        return INVALID_CREDENTIAL_CONFIGURATION
    if not credential_path.exists():
        return None
    try:
        directory_stat = credential_directory.stat()
        credential_stat = credential_path.stat()
        if not credential_path.is_file():
            return INVALID_CREDENTIAL_CONFIGURATION
        if os.name == "posix" and (
            stat.S_IMODE(directory_stat.st_mode) != 0o700
            or stat.S_IMODE(credential_stat.st_mode) != 0o600
            or directory_stat.st_uid != os.geteuid()
            or credential_stat.st_uid != os.geteuid()
        ):
            return INVALID_CREDENTIAL_CONFIGURATION
        credential_hash = credential_path.read_text(encoding="utf-8").strip()
        return credential_hash or INVALID_CREDENTIAL_CONFIGURATION
    except OSError:
        return INVALID_CREDENTIAL_CONFIGURATION


def create_credential_hash(password: str) -> str:
    if len(password) < 12:
        raise ValueError("The supervisor credential must be at least 12 characters.")
    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=PBKDF2_KEY_BYTES,
    )
    return "$".join(
        (
            "pbkdf2_sha256",
            str(PBKDF2_ITERATIONS),
            _encode(salt),
            _encode(derived_key),
        )
    )


def verify_credential(password: str, encoded: str | None) -> bool:
    parsed = _parse_hash(encoded)
    if parsed is None:
        return False
    salt, expected = parsed
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=PBKDF2_KEY_BYTES,
    )
    return hmac.compare_digest(actual, expected)


def credential_hash_is_valid(encoded: str | None) -> bool:
    return _parse_hash(encoded) is not None


@dataclass
class _PeerFailures:
    failures: deque[float] = field(default_factory=deque)
    blocked_until: float = 0.0
    last_seen: float = 0.0


class LocalReopenAuthorizer:
    def __init__(self) -> None:
        self._peers: dict[str, _PeerFailures] = {}
        self._lock = threading.Lock()

    def authorize(
        self,
        peer_address: str | None,
        password: str | None,
        credential_hash: str | None,
    ) -> str:
        if not _is_loopback(peer_address):
            return "remote_request"
        if not credential_hash:
            return "credential_not_configured"
        if not credential_hash_is_valid(credential_hash):
            return "credential_configuration_invalid"

        peer = str(ipaddress.ip_address(peer_address))
        now = time.monotonic()
        with self._lock:
            failures = self._peers.get(peer)
            if failures is not None and failures.blocked_until > now:
                return "throttled"
            if failures is not None:
                while (
                    failures.failures
                    and failures.failures[0]
                    <= now - FAILED_ATTEMPT_WINDOW_SECONDS
                ):
                    failures.failures.popleft()
                failures.last_seen = now

            if (
                password is not None
                and len(password) <= 1024
                and verify_credential(password, credential_hash)
            ):
                self._peers.pop(peer, None)
                return "authorized"

            if failures is None:
                self._prune(now)
                if len(self._peers) >= MAX_TRACKED_PEERS:
                    return "throttled"
                failures = _PeerFailures(last_seen=now)
                self._peers[peer] = failures
            failures.failures.append(now)
            failures.last_seen = now
            if len(failures.failures) >= FAILED_ATTEMPT_LIMIT:
                failures.blocked_until = now + LOCKOUT_SECONDS
                return "throttled"
            return "invalid_credential"

    def reset(self) -> None:
        with self._lock:
            self._peers.clear()

    def _prune(self, now: float) -> None:
        expired = [
            peer
            for peer, state in self._peers.items()
            if state.blocked_until <= now
            and state.last_seen <= now - FAILED_ATTEMPT_WINDOW_SECONDS
        ]
        for peer in expired:
            self._peers.pop(peer, None)


def _is_loopback(address: str | None) -> bool:
    if not address:
        return False
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def _parse_hash(encoded: str | None) -> tuple[bytes, bytes] | None:
    if not isinstance(encoded, str):
        return None
    try:
        algorithm, raw_iterations, salt_text, key_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or int(raw_iterations) != PBKDF2_ITERATIONS:
            return None
        salt = _decode(salt_text)
        key = _decode(key_text)
    except (ValueError, TypeError):
        return None
    if len(salt) != PBKDF2_SALT_BYTES or len(key) != PBKDF2_KEY_BYTES:
        return None
    return salt, key


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


local_reopen_authorizer = LocalReopenAuthorizer()
