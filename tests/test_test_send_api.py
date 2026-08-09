import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps/api"
sys.path.insert(0, str(API))

from fastapi import HTTPException
from mail import delivery_test_service as test_send


def payload(provider="smtp2go"):
    return test_send.TestSendPayload(
        provider=provider,
        to_email="destino@example.org",
        to_name="Destino",
        subject="Teste",
        body_html="<p>Olá</p>",
        body_text=None,
        from_name="Orbital",
        from_email="remetente@example.org",
    )


def test_plain_text_is_generated_from_html():
    assert test_send._plain_text("<p>Olá <strong>mundo</strong></p>") == "Olá mundo"


def test_smtp2go_requires_key(monkeypatch):
    monkeypatch.setattr(test_send, "get_settings", lambda: SimpleNamespace(smtp2go_api_key=None))
    try:
        test_send._send_smtp2go(payload())
        assert False, "deveria falhar"
    except HTTPException as exc:
        assert exc.status_code == 503


def test_test_endpoint_is_locked_by_default(monkeypatch):
    monkeypatch.setattr(test_send, "get_settings", lambda: SimpleNamespace(mail_send_enabled=False))
    context = SimpleNamespace(require_module_access=lambda: None)
    try:
        test_send.send_test_email(payload(), context)
        assert False, "deveria falhar"
    except HTTPException as exc:
        assert exc.status_code == 409


def test_test_endpoint_routes_provider(monkeypatch):
    monkeypatch.setattr(test_send, "get_settings", lambda: SimpleNamespace(mail_send_enabled=True))
    expected = test_send.TestSendResponse(ok=True, provider="smtp2go", message="ok")
    monkeypatch.setattr(test_send, "_send_smtp2go", lambda value: expected)
    context = SimpleNamespace(require_module_access=lambda: None)
    assert test_send.send_test_email(payload(), context) == expected


def test_smtp2go_uses_complete_endpoint_from_settings(monkeypatch):
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"data":{"request_id":"req-1","failures":[]}}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse()

    endpoint = "https://gateway.example.test/custom/send"
    monkeypatch.setattr(
        test_send,
        "get_settings",
        lambda: SimpleNamespace(
            smtp2go_api_key="secret",
            smtp2go_api_url=endpoint,
            mail_from_address="remetente@example.org",
            mail_from_name="Orbital",
            mail_reply_to=None,
            mail_send_timeout_seconds=12,
        ),
    )
    monkeypatch.setattr(test_send.urllib.request, "urlopen", fake_urlopen)

    result = test_send._send_smtp2go(payload())

    assert result.ok is True
    assert captured["url"] == endpoint
    assert captured["timeout"] == 12


def test_smtp2go_returns_provider_diagnostic(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"data":{"request_id":"req-diag","succeeded":1,"failed":0,"failures":[]}}'

    monkeypatch.setattr(
        test_send,
        "get_settings",
        lambda: SimpleNamespace(
            smtp2go_api_key="secret",
            smtp2go_api_url="https://api.example.test/send",
            mail_from_address="remetente@example.org",
            mail_from_name="Orbital",
            mail_reply_to=None,
            mail_send_timeout_seconds=12,
        ),
    )
    monkeypatch.setattr(test_send.urllib.request, "urlopen", lambda request, timeout: FakeResponse())

    result = test_send._send_smtp2go(payload())

    assert result.accepted is True
    assert result.provider_message_id == "req-diag"
    assert result.diagnostic["http_status"] == 200
    assert result.diagnostic["succeeded"] == 1
    assert result.diagnostic["failed"] == 0
    assert "entrega" in result.message.lower()


def test_smtp2go_http_error_returns_structured_diagnostic(monkeypatch):
    import io
    import urllib.error

    error = urllib.error.HTTPError(
        url="https://api.example.test/send",
        code=400,
        msg="Bad Request",
        hdrs=None,
        fp=io.BytesIO(b'{"data":{"error":"sender not verified"}}'),
    )
    monkeypatch.setattr(
        test_send,
        "get_settings",
        lambda: SimpleNamespace(
            smtp2go_api_key="secret",
            smtp2go_api_url="https://api.example.test/send",
            mail_from_address="remetente@example.org",
            mail_from_name="Orbital",
            mail_reply_to=None,
            mail_send_timeout_seconds=12,
        ),
    )
    monkeypatch.setattr(test_send.urllib.request, "urlopen", lambda request, timeout: (_ for _ in ()).throw(error))

    try:
        test_send._send_smtp2go(payload())
        assert False, "deveria falhar"
    except HTTPException as exc:
        assert exc.status_code == 502
        assert exc.detail["provider"] == "smtp2go"
        assert exc.detail["accepted"] is False
        assert exc.detail["diagnostic"]["http_status"] == 400
        assert exc.detail["diagnostic"]["provider_response"]["data"]["error"] == "sender not verified"
