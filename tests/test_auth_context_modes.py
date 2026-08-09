import asyncio

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from core import auth as auth_core
from core.settings import Settings


def _request(authorization: str | None = None) -> Request:
    headers = []
    if authorization:
        headers.append((b"authorization", authorization.encode("latin-1")))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def _settings(**kwargs) -> Settings:
    values = {
        "APP_ENV": "development",
        "AUTH_MODE": "remote",
        "AUTH_CONTEXT_URL": "http://orbital.test/auth/context",
    }
    values.update(kwargs)
    return Settings(_env_file=None, **values)


def test_standalone_auth_is_forbidden():
    with pytest.raises(ValidationError, match="AUTH_MODE deve ser remote"):
        Settings(
            _env_file=None,
            APP_ENV="development",
            AUTH_MODE="standalone",
            AUTH_CONTEXT_URL="http://orbital.test/auth/context",
        )


def test_remote_requires_token(monkeypatch):
    settings = _settings()
    monkeypatch.setattr(auth_core, "get_settings", lambda: settings)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(auth_core.get_auth_context(_request(), None))
    assert getattr(exc_info.value, "status_code", None) == 401


def test_remote_forwards_bearer_and_uses_orbital_context(monkeypatch):
    settings = _settings()
    monkeypatch.setattr(auth_core, "get_settings", lambda: settings)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"user_id": 91, "tenant_code": "Asaclub", "is_admin": True, "is_dev": False, "permissions": [{"page_alias": "orbital-mail-home", "action_code": "access_page"}]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, headers, cookies):
            assert url == settings.auth_context_url
            assert headers == {"Authorization": "Bearer token-123"}
            return FakeResponse()

    monkeypatch.setattr(auth_core.httpx, "AsyncClient", FakeClient)
    context = asyncio.run(auth_core.get_auth_context(_request("Bearer token-123"), "Bearer token-123"))
    assert context.user_id == 91
    assert context.tenant_code == "asaclub"
    assert context.is_admin is True
    assert context.is_dev is False
    context.require_module_access()
