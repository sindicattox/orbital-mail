from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from core.settings import Settings
from mail.delivery_provider import (
    MailProviderError,
    MailSendPayload,
    send_provider_message,
    send_ses,
    send_smtp2go,
)
from mail.delivery_worker_service import MailDeliveryWorkerService
from mail.runtime_config import effective_provider, provider_status


ROOT = Path(__file__).resolve().parents[1]


def payload(**overrides) -> MailSendPayload:
    values = {
        "provider": "smtp2go",
        "to_email": "destino@example.com",
        "to_name": "Destino",
        "subject": "Assunto",
        "body_html": "<p>Olá</p>",
        "from_email": "contato@sindicatto.com",
        "from_name": "Sindicatto",
    }
    values.update(overrides)
    return MailSendPayload(**values)


def settings(**overrides) -> SimpleNamespace:
    values = {
        "smtp2go_api_key": "api-test",
        "smtp2go_api_url": "https://api.example.test/v3/email/send",
        "mail_from_address": "contato@sindicatto.com",
        "mail_from_name": "Sindicatto",
        "mail_reply_to": None,
        "mail_send_timeout_seconds": 5,
        "aws_ses_region": "us-east-1",
        "mail_provider": "smtp2go",
        "mail_send_enabled": True,
        "mail_worker_max_attempts": 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_smtp2go_requires_api_key():
    with pytest.raises(MailProviderError) as exc:
        send_smtp2go(payload(), settings(smtp2go_api_key=""))
    assert exc.value.status_code == 503
    assert "SMTP2GO_API_KEY" in str(exc.value.detail)


def test_smtp2go_success_returns_provider_message_id(monkeypatch):
    class FakeResponse:
        status = 200

        def read(self):
            return b'{"request_id":"req-1","data":{"email_id":"em-9","succeeded":1,"failed":0,"failures":[]}}'

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("mail.delivery_provider.urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse())
    result = send_smtp2go(payload(), settings())
    assert result.ok is True
    assert result.accepted is True
    assert result.provider == "smtp2go"
    assert result.provider_message_id == "em-9"


def test_ses_success_uses_sesv2_raw_and_region(monkeypatch):
    import sys

    captured = {}

    class FakeClient:
        def send_email(self, **kwargs):
            captured.update(kwargs)
            return {
                "MessageId": "ses-123",
                "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": "req-ses"},
            }

    monkeypatch.setitem(
        sys.modules,
        "boto3",
        SimpleNamespace(client=lambda service, region_name=None: captured.update(service=service, region=region_name) or FakeClient()),
    )
    result = send_ses(payload(provider="ses"), settings(aws_ses_region="sa-east-1"))
    assert result.ok is True
    assert result.provider == "ses"
    assert result.provider_message_id == "ses-123"
    assert captured["service"] == "sesv2"
    assert captured["region"] == "sa-east-1"
    assert captured["FromEmailAddress"] == "contato@sindicatto.com"
    assert captured["Destination"]["ToAddresses"] == ["destino@example.com"]
    assert "Raw" in captured["Content"]


def test_ses_provider_error_is_wrapped(monkeypatch):
    import sys

    class FakeClient:
        def send_email(self, **_kwargs):
            raise RuntimeError("MessageRejected")

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *_args, **_kwargs: FakeClient()))
    with pytest.raises(MailProviderError) as exc:
        send_ses(payload(provider="ses"), settings())
    assert exc.value.status_code == 502
    assert exc.value.detail["provider"] == "ses"


def test_ses_requires_from_address():
    with pytest.raises(MailProviderError) as exc:
        send_ses(
            payload(provider="ses", from_email=None),
            settings(mail_from_address=""),
        )
    assert exc.value.status_code == 503
    assert "EMAIL_FROM_ADDRESS" in str(exc.value.detail)


def test_send_provider_message_routes_smtp2go_and_ses(monkeypatch):
    seen = []

    def fake_smtp2go(message, _settings):
        seen.append(("smtp2go", message.provider))
        return SimpleNamespace(ok=True, provider="smtp2go")

    def fake_ses(message, _settings):
        seen.append(("ses", message.provider))
        return SimpleNamespace(ok=True, provider="ses")

    monkeypatch.setattr("mail.delivery_provider.send_smtp2go", fake_smtp2go)
    monkeypatch.setattr("mail.delivery_provider.send_ses", fake_ses)
    send_provider_message(payload(provider="smtp2go"), settings())
    send_provider_message(payload(provider="ses"), settings())
    assert seen == [("smtp2go", "smtp2go"), ("ses", "ses")]


def test_settings_accepts_ses_without_smtp2go_key_when_send_enabled():
    configured = Settings(
        _env_file=None,
        EMAIL_PROVIDER="ses",
        EMAIL_SEND_ENABLED=True,
        SMTP2GO_API_KEY="",
        EMAIL_FROM_ADDRESS="contato@sindicatto.com",
        AWS_SES_REGION="us-east-1",
    )
    assert configured.mail_provider == "ses"
    assert configured.mail_send_enabled is True


def test_settings_still_requires_smtp2go_key_when_that_provider_is_enabled():
    with pytest.raises(ValidationError, match="SMTP2GO_API_KEY"):
        Settings(
            _env_file=None,
            EMAIL_PROVIDER="smtp2go",
            EMAIL_SEND_ENABLED=True,
            SMTP2GO_API_KEY="",
        )


def test_settings_requires_from_address_for_ses_when_send_enabled():
    with pytest.raises(ValidationError, match="EMAIL_FROM_ADDRESS"):
        Settings(
            _env_file=None,
            EMAIL_PROVIDER="ses",
            EMAIL_SEND_ENABLED=True,
            EMAIL_FROM_ADDRESS="",
            SMTP2GO_API_KEY="",
        )


def test_worker_does_not_claim_when_send_switch_is_off():
    service = MailDeliveryWorkerService(SimpleNamespace(), settings(mail_send_enabled=False))
    assert service.process_one("smtp2go") is None
    assert service.process_one("ses") is None


def test_worker_uses_item_provider_or_effective_fallback(monkeypatch):
    class FakeSession:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("claim não deveria ocorrer neste recorte")

    seen = []

    def fake_claim(self, **_kwargs):
        return {
            "id": 1,
            "email_campaign_id": 9,
            "tenant_code": "anpprev",
            "email": "destino@example.com",
            "provider": "ses",
            "try_count": 1,
            "subject": "Assunto",
            "body_html": "<p>x</p>",
            "body_text": "x",
            "name": "Destino",
            "sender_name": "Sindicatto",
            "sender_email": "contato@sindicatto.com",
            "reply_to": None,
        }

    def fake_deliver(self, item, provider):
        seen.append((item["email"], provider))
        return SimpleNamespace(queue_status="sent")

    monkeypatch.setattr(MailDeliveryWorkerService, "claim_next", fake_claim)
    monkeypatch.setattr(MailDeliveryWorkerService, "deliver_claimed", fake_deliver)
    service = MailDeliveryWorkerService(FakeSession(), settings(mail_provider="smtp2go"))
    service.process_one("smtp2go")
    assert seen == [("destino@example.com", "ses")]


def test_effective_provider_prefers_tenant_override():
    class FakeDb:
        def execute(self, *_args, **_kwargs):
            return SimpleNamespace(scalar_one_or_none=lambda: "ses")

    selected = effective_provider(FakeDb(), "anpprev", settings(mail_provider="smtp2go"))
    assert selected == "ses"


def test_provider_status_does_not_mark_ses_ready_without_from_address():
    smtp2go = provider_status(settings(smtp2go_api_key="api-test"), "smtp2go")
    ses_ready = provider_status(settings(mail_from_address="contato@sindicatto.com"), "ses")
    ses_missing = provider_status(settings(mail_from_address=""), "ses")
    assert smtp2go["configured"] is True
    assert ses_ready["configured"] is True
    assert ses_missing["configured"] is False


def test_test_send_page_and_settings_offer_both_cloud_providers():
    page = (ROOT / "apps/web/src/pages/teste-envio/index.astro").read_text(encoding="utf-8")
    settings_page = (ROOT / "apps/web/src/pages/configuracoes/index.astro").read_text(encoding="utf-8")
    assert 'value="smtp2go"' in page
    assert 'value="ses"' in page
    assert 'value="ses"' in settings_page
    assert 'value="smtp2go"' in settings_page


def test_ses_migration_and_router_are_present():
    migration = (ROOT / "database/oracle/004_email_delivery_config.sql").read_text(encoding="utf-8")
    router = (ROOT / "apps/api/mail/settings_router.py").read_text(encoding="utf-8")
    main = (ROOT / "apps/api/main.py").read_text(encoding="utf-8")
    requirements = (ROOT / "apps/api/requirements.txt").read_text(encoding="utf-8")
    assert "email_delivery_config" in migration
    assert "ses" in migration
    assert "smtp2go" in migration
    assert "require_dev()" in router
    assert "mail_settings_router" in main
    assert "boto3" in requirements
