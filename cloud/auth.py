from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cloud.database import CloudDatabase


_bearer = HTTPBearer(auto_error=False)


def password_hash(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("Administrator passwords must be at least 12 characters.")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return "$".join(
        (
            "pbkdf2_sha256",
            "310000",
            base64.urlsafe_b64encode(salt).decode().rstrip("="),
            base64.urlsafe_b64encode(digest).decode().rstrip("="),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, raw_iterations, salt_text, expected_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(raw_iterations)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        salt = _decode(salt_text)
        expected = _decode(expected_text)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(actual, expected)


def issue_user_token(
    user_id: str,
    company_id: str,
    secret: str,
    lifetime_seconds: int,
) -> str:
    now = int(time.time())
    header = _encode_json({"alg": "HS256", "typ": "JWT"})
    payload = _encode_json(
        {
            "sub": user_id,
            "company_id": company_id,
            "iat": now,
            "exp": now + lifetime_seconds,
        }
    )
    signed = f"{header}.{payload}"
    signature = hmac.new(
        secret.encode(),
        signed.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signed}.{_encode(signature)}"


def verify_user_token(token: str, secret: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
        header = json.loads(_decode(header_part))
        payload = json.loads(_decode(payload_part))
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Unsupported token header.")
        expected = hmac.new(
            secret.encode(),
            f"{header_part}.{payload_part}".encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_decode(signature_part), expected):
            raise ValueError("Invalid token signature.")
        if not isinstance(payload, dict) or int(payload["exp"]) <= int(time.time()):
            raise ValueError("Token expired.")
        if not isinstance(payload.get("sub"), str) or not isinstance(
            payload.get("company_id"), str
        ):
            raise ValueError("Invalid token claims.")
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_station(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, str]:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Station bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    station = request.app.state.database.authenticate_station(token_hash)
    if station is None:
        raise HTTPException(status_code=401, detail="Invalid or disabled station token.")
    return station


def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, str]:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="User bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = request.app.state.settings
    claims = verify_user_token(credentials.credentials, settings.jwt_secret)
    user = request.app.state.database.get_active_user(claims["sub"])
    if user is None or user["company_id"] != claims["company_id"]:
        raise HTTPException(status_code=401, detail="User account is inactive.")
    return dict(user)


def require_permission(permission: str):
    def dependency(
        request: Request,
        user: dict[str, str] = Depends(require_user),
    ) -> dict[str, str]:
        with request.app.state.database.connection() as connection:
            row = connection.execute(
                "SELECT permissions FROM roles WHERE role_id = %s",
                (user["role_id"],),
            ).fetchone()
        if row is None or permission not in row["permissions"]:
            raise HTTPException(status_code=403, detail="Insufficient role permissions.")
        return user

    return dependency


def _encode_json(value: dict[str, Any]) -> str:
    return _encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode())


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
