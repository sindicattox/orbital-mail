from pathlib import Path
import sys

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from mail.delivery_policy import accepted_decision, exception_decision


class Result:
    accepted = True
    provider_message_id = "request-id"
    diagnostic = {
        "http_status": 200,
        "provider_response": {"data": {"email_id": "provider-email-id"}},
    }


def test_accepted_smtp2go_uses_email_id_and_new_log_status():
    decision = accepted_decision("smtp2go", Result())
    assert decision.queue_status == "sent"
    assert decision.log_status == "success"
    assert decision.event_type == "accepted"
    assert decision.provider_message_id == "provider-email-id"
    assert decision.retryable is False


def test_invalid_recipient_is_blocked_and_not_retried():
    exc = HTTPException(status_code=502, detail={
        "message": "Invalid recipient: user does not exist",
        "diagnostic": {"smtp_code": 550},
    })
    decision = exception_decision("smtp", exc, try_count=1, max_attempts=3)
    assert decision.error_class == "recipient"
    assert decision.blocked is True
    assert decision.retryable is False
    assert decision.queue_status == "error"


def test_timeout_is_retried_only_until_limit():
    exc = TimeoutError("connection timeout")
    first = exception_decision("smtp", exc, try_count=1, max_attempts=3)
    last = exception_decision("smtp", exc, try_count=3, max_attempts=3)
    assert first.error_class == "temporary"
    assert first.retryable is True
    assert first.queue_status == "pending"
    assert last.retryable is False
    assert last.queue_status == "error"


def test_configuration_error_does_not_block_recipient():
    exc = HTTPException(status_code=502, detail={
        "message": "Authentication credentials invalid",
        "diagnostic": {"smtp_code": 535},
    })
    decision = exception_decision("smtp", exc, try_count=1, max_attempts=3)
    assert decision.error_class == "configuration"
    assert decision.blocked is False
    assert decision.retryable is False


def test_migration_removes_duplicate_table_and_adds_delivery_fields():
    migration = (ROOT / "database/oracle/002_email_delivery_events.sql").read_text()
    assert "DROP TABLE EMAIL_CAMPAIGN_RECIPIENT" in migration
    assert "EMAIL_CAMPAIGN_RECIPIENT_BKP" in migration
    for field in (
        "PROVIDER_STATUS", "LAST_ERROR_CLASS", "RETRYABLE", "NEXT_TRY_AT",
        "EVENT_TYPE", "RAW_RESPONSE", "PROVIDER_EVENT_ID", "TENANT_CODE",
    ):
        assert field in migration


def test_private_test_addresses_are_not_packaged():
    deploy = (ROOT / "deploy/remote/setup.sh").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "--exclude='apps/api/.emails_para_teste'" in deploy
    assert "apps/api/.emails_para_teste" in gitignore
    assert (API / ".emails_para_teste.example").exists()
