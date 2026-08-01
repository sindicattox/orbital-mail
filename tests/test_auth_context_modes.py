import asyncio

from starlette.requests import Request

from core import auth as auth_core
from core.settings import Settings


def _request(authorization: str | None = None) -> Request:
    headers = []
    if authorization:
        headers.append((b"authorization", authorization.encode("latin-1")))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def test_standalone_uses_all_three_dev_fallback_values(monkeypatch):
    settings = Settings(
        _env_file=None,
        auth_mode="standalone",
        dev_tenant_code="Sinproprev",
        dev_user_id=77,
        dev_is_admin=False,
    )
    monkeypatch.setattr(auth_core, "get_settings", lambda: settings)

    context = asyncio.run(auth_core.get_auth_context(_request(), None))

    assert context.tenant_code == "sinproprev"
    assert context.user_id == 77
    assert context.is_admin is False
    assert context.permissions == frozenset({"mail.view", "mail.manage", "mail.send"})


def test_remote_requires_token(monkeypatch):
    settings = Settings(_env_file=None, auth_mode="remote", auth_context_url="http://orbital.test/auth/context")
    monkeypatch.setattr(auth_core, "get_settings", lambda: settings)

    try:
        asyncio.run(auth_core.get_auth_context(_request(), None))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401
    else:
        raise AssertionError("Remote sem token deveria retornar 401")


def test_remote_forwards_bearer_and_uses_orbital_context(monkeypatch):
    settings = Settings(_env_file=None, auth_mode="remote", auth_context_url="http://orbital.test/auth/context")
    monkeypatch.setattr(auth_core, "get_settings", lambda: settings)

    class FakeResponse:
        status_code = 200
        @staticmethod
        def json():
            return {"user_id": 91, "tenant_code": "Asaclub", "is_admin": True, "permissions": ["mail.view"]}

    class FakeClient:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def get(self, url, headers, cookies):
            assert url == settings.auth_context_url
            assert headers == {"Authorization": "Bearer token-123"}
            return FakeResponse()

    monkeypatch.setattr(auth_core.httpx, "AsyncClient", FakeClient)
    context = asyncio.run(auth_core.get_auth_context(_request("Bearer token-123"), "Bearer token-123"))
    assert context.user_id == 91
    assert context.tenant_code == "asaclub"
    assert context.is_admin is True
