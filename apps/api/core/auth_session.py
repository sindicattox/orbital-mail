import base64
import hashlib
import hmac
import json
import time


class AuthSessionError(ValueError):
    pass


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_auth_session(payload: dict, secret: str, ttl_seconds: int) -> str:
    data = dict(payload)
    data["exp"] = int(time.time()) + ttl_seconds
    body = _encode(json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _encode(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def read_auth_session(token: str, secret: str) -> dict:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise AuthSessionError("Sessão inválida.") from exc

    expected = _encode(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise AuthSessionError("Sessão inválida.")

    try:
        payload = json.loads(_decode(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthSessionError("Sessão inválida.") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise AuthSessionError("Sessão expirada.")
    return payload
