import asyncio
from urllib.parse import parse_qs, urlparse

from starlette.requests import Request

from core import auth as auth_core
from core.auth_session import create_auth_session, read_auth_session
from core.settings import Settings
from routes import auth as auth_routes


def _request(cookie: str | None = None) -> Request:
    headers = []
    if cookie:
        headers.append((b"cookie", cookie.encode("latin-1")))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def _remote_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "auth_mode": "remote",
        "auth_authorize_url": "http://127.0.0.1:4001/auth/sso/authorize",
        "auth_token_url": "http://127.0.0.1:8001/auth/sso/token",
        "auth_client_id": "email-app",
        "auth_client_secret": "email-app-local-development",
        "auth_redirect_uri": "http://127.0.0.1:8104/api/mail/auth/callback",
        "auth_web_url": "http://127.0.0.1:4104/",
        "auth_session_secret": "orbital-mail-test-secret-with-32-chars",
    }
    values.update(overrides)
    return Settings(**values)


def test_standalone_uses_all_three_dev_fallback_values(monkeypatch):
    settings = Settings(
        _env_file=None,
        auth_mode="disabled",
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


def test_remote_uses_signed_identity_received_from_orbital(monkeypatch):
    settings = _remote_settings()
    session = create_auth_session(
        {"member_id": 91, "tenant_code": "Anpprev", "is_admin": True},
        settings.auth_session_secret,
        settings.auth_session_ttl_seconds,
    )
    monkeypatch.setattr(auth_core, "get_settings", lambda: settings)

    context = asyncio.run(
        auth_core.get_auth_context(_request(f"{settings.auth_cookie_name}={session}"), None)
    )

    assert context.user_id == 91
    assert context.tenant_code == "anpprev"
    assert context.is_admin is True


def test_auth_start_redirects_to_existing_orbital_sso(monkeypatch):
    settings = _remote_settings()
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings)

    response = auth_routes.start_authentication("/campanhas?status=draft")
    parsed = urlparse(response.headers["location"])
    query = parse_qs(parsed.query)

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == settings.auth_authorize_url
    assert query["client_id"] == ["email-app"]
    assert query["redirect_uri"] == [settings.auth_redirect_uri]
    assert query["response_type"] == ["code"]
    assert query["state"][0]
    assert STATE_COOKIE_PRESENT(response.headers.getlist("set-cookie"))


def STATE_COOKIE_PRESENT(headers: list[str]) -> bool:
    return any(header.startswith(f"{auth_routes.STATE_COOKIE}=") for header in headers)


def test_signed_session_round_trip():
    token = create_auth_session(
        {"member_id": 12, "tenant_code": "anpprev", "is_admin": True},
        "a-test-secret-that-is-long-enough",
        60,
    )
    payload = read_auth_session(token, "a-test-secret-that-is-long-enough")

    assert payload["member_id"] == 12
    assert payload["tenant_code"] == "anpprev"
    assert payload["exp"] > 0


def test_sso_callback_accepts_orbital_identity_without_orbital_code_change(monkeypatch):
    settings = _remote_settings()
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "person_id": 7,
                "member_id": 91,
                "tenant_code": "anpprev",
                "etype_code": "admin",
                "is_admin": True,
                "is_dev": False,
            }

    class FakeClient:
        def __init__(self, **_kwargs):
            self.request_payload = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, json):
            assert url == settings.auth_token_url
            assert json["client_id"] == "email-app"
            assert json["redirect_uri"] == settings.auth_redirect_uri
            return FakeResponse()

    monkeypatch.setattr(auth_routes.httpx, "AsyncClient", FakeClient)
    request = _request(
        f"{auth_routes.STATE_COOKIE}=state-123; {auth_routes.RETURN_COOKIE}=/campanhas"
    )

    response = asyncio.run(auth_routes.authentication_callback(request, "code-123", "state-123"))

    assert response.status_code == 302
    assert response.headers["location"] == "http://127.0.0.1:4104/campanhas"
    session_cookie = next(
        header for header in response.headers.getlist("set-cookie")
        if header.startswith(f"{settings.auth_cookie_name}=")
    )
    token = session_cookie.split(";", 1)[0].split("=", 1)[1]
    payload = read_auth_session(token, settings.auth_session_secret)
    assert payload["member_id"] == 91
    assert payload["tenant_code"] == "anpprev"
