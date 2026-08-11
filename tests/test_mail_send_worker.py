from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import sys

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))

from mail.delivery_worker_service import MailDeliveryWorkerService, TEST_CAMPAIGN_PATTERN


class FakeResult:
    def __init__(self, row=None, rowcount=0):
        self.row = row
        self.rowcount = rowcount

    def mappings(self):
        return self

    def first(self):
        return self.row


class FakeSession:
    def __init__(self, claim_row=None):
        self.claim_row = claim_row
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self._transaction = False

    def execute(self, statement, params=None):
        sql = str(statement)
        self.calls.append((sql, params or {}))
        self._transaction = True
        if "SELECT q.id, q.email_campaign_id" in sql:
            return FakeResult(self.claim_row)
        return FakeResult(rowcount=1)

    def commit(self):
        self.commits += 1
        self._transaction = False

    def rollback(self):
        self.rollbacks += 1
        self._transaction = False

    def in_transaction(self):
        return self._transaction


def worker_settings(**overrides):
    values = {
        "mail_send_enabled": True,
        "mail_worker_max_attempts": 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def queue_item(**overrides):
    values = {
        "id": 11,
        "email_campaign_id": 7,
        "tenant_code": "anpprev",
        "email": "destino@example.com",
        "name": "Destino",
        "try_count": 1,
        "subject": "Assunto",
        "body_html": "<p>Olá</p>",
        "body_text": "Olá",
        "sender_name": "Sindicatto",
        "sender_email": "contato@sindicatto.com",
        "reply_to": None,
    }
    values.update(overrides)
    return values


def test_real_worker_claim_is_atomic_and_excludes_test_campaigns():
    db = FakeSession(claim_row=queue_item(try_count=0))
    service = MailDeliveryWorkerService(db, worker_settings())

    item = service.claim_next()

    assert item["id"] == 11
    assert item["try_count"] == 1
    select_sql, select_params = db.calls[0]
    assert "FOR UPDATE OF q.status SKIP LOCKED" in select_sql
    assert "c.status = 'sending'" in select_sql
    assert "NOT LIKE :test_campaign_pattern" in select_sql
    assert select_params["test_campaign_pattern"] == TEST_CAMPAIGN_PATTERN
    update_sql, update_params = db.calls[1]
    assert "status = 'processing'" in update_sql
    assert "try_count = try_count + 1" in update_sql
    assert update_params == {"id": 11}
    assert db.commits == 1


def test_test_loop_can_use_same_motor_without_real_worker_filter():
    db = FakeSession(claim_row=queue_item())
    service = MailDeliveryWorkerService(db, worker_settings())

    service.claim_next(campaign_id=7, tenant_code="anpprev", include_test_campaigns=True)

    select_sql, params = db.calls[0]
    assert "email_campaign_id = :campaign_id" in select_sql
    assert "LOWER(q.tenant_code) = LOWER(:tenant_code)" in select_sql
    assert "NOT LIKE :test_campaign_pattern" not in select_sql
    assert params == {"campaign_id": 7, "tenant_code": "anpprev"}


def test_worker_never_claims_when_send_switch_is_off(monkeypatch):
    db = FakeSession(claim_row=queue_item())
    service = MailDeliveryWorkerService(db, worker_settings(mail_send_enabled=False))
    monkeypatch.setattr(service, "claim_next", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("não deve claimar")))

    assert service.process_one("smtp2go") is None


def test_smtp2go_success_updates_queue_and_immutable_log(monkeypatch):
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())
    captured = {}

    def accepted(payload):
        captured["payload"] = payload
        return SimpleNamespace(
            provider_message_id="request-1",
            diagnostic={
                "http_status": 200,
                "provider_response": {"data": {"email_id": "email-1"}},
            },
        )

    monkeypatch.setattr("mail.delivery_worker_service.send_provider_message", lambda payload, _settings: accepted(payload))
    decision = service.deliver_claimed(queue_item(), "smtp2go")

    assert decision.queue_status == "sent"
    assert decision.provider_message_id == "email-1"
    assert "List-Unsubscribe" in captured["payload"].headers
    assert "Descadastrar" in captured["payload"].body_html
    update_sql, update_params = db.calls[0]
    log_sql, log_params = db.calls[1]
    assert "UPDATE email_queue" in update_sql
    assert update_params["status"] == "sent"
    assert update_params["provider_message_id"] == "email-1"
    assert "INSERT INTO email_send_log" in log_sql
    assert log_params["status"] == "success"
    assert log_params["event_type"] == "accepted"
    assert db.commits == 1


def test_temporary_provider_failure_returns_to_queue_for_retry(monkeypatch):
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings(mail_worker_max_attempts=3))

    def timeout(_payload):
        raise HTTPException(
            status_code=502,
            detail={"message": "connection timeout", "diagnostic": {"http_status": 503}},
        )

    monkeypatch.setattr("mail.delivery_worker_service.send_provider_message", lambda payload, _settings: timeout(payload))
    decision = service.deliver_claimed(queue_item(try_count=1), "smtp2go")

    assert decision.error_class == "temporary"
    assert decision.retryable is True
    assert decision.queue_status == "pending"
    update_sql, update_params = db.calls[0]
    assert "SYSDATE + (1 / 1440)" in update_sql
    assert update_params["retryable"] == 1
    assert update_params["blocked"] == 0


def test_configuration_failure_stops_campaign_without_blocking_recipient(monkeypatch):
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())

    def bad_auth(_payload):
        raise HTTPException(status_code=502, detail={"message": "SMTP2GO authentication failed", "diagnostic": {"http_status": 401}})

    monkeypatch.setattr("mail.delivery_worker_service.send_provider_message", lambda payload, _settings: bad_auth(payload))
    decision = service.deliver_claimed(queue_item(), "smtp2go")

    assert decision.error_class == "configuration"
    assert decision.blocked is False
    assert decision.retryable is False
    assert any("SET status = 'error'" in sql for sql, _params in db.calls)


def test_permanent_recipient_failure_adds_tenant_blacklist(monkeypatch):
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())

    def invalid_recipient(_payload):
        raise HTTPException(status_code=502, detail={"message": "user unknown", "diagnostic": {"smtp_code": 550}})

    monkeypatch.setattr("mail.delivery_worker_service.send_provider_message", lambda payload, _settings: invalid_recipient(payload))
    decision = service.deliver_claimed(queue_item(), "smtp2go")

    assert decision.error_class == "recipient"
    assert decision.blocked is True
    merge = [(sql, params) for sql, params in db.calls if "MERGE INTO email_blacklist" in sql]
    assert len(merge) == 1
    assert merge[0][1]["tenant_code"] == "anpprev"
    assert merge[0][1]["email"] == "destino@example.com"


def test_stale_processing_items_are_recovered_only_for_real_sending_campaigns():
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())

    recovered = service.recover_stale(900)

    assert recovered == 1
    sql, params = db.calls[0]
    assert "q.status = 'processing'" in sql
    assert "SET q.status" not in sql
    assert "q.retryable =" not in sql
    assert "q.next_try_at =" not in sql
    assert "q.updated_at =" not in sql
    assert "c.status = 'sending'" in sql
    assert "NOT LIKE :test_campaign_pattern" in sql
    assert params["stale_seconds"] == 900
    assert params["test_campaign_pattern"] == TEST_CAMPAIGN_PATTERN


def test_completed_campaign_finalize_ignores_test_campaigns():
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())

    completed = service.finalize_completed_campaigns()

    assert completed == 1
    sql, params = db.calls[0]
    assert "SET status = 'completed'" in sql
    assert "SET c.status" not in sql
    assert "c.send_date =" not in sql
    assert "c.updated_at =" not in sql
    assert "NOT EXISTS" in sql
    assert "q.status IN ('pending', 'processing')" in sql
    assert params["test_campaign_pattern"] == TEST_CAMPAIGN_PATTERN


def test_missing_sender_is_configuration_error_and_stops_campaign(monkeypatch):
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())

    def missing_sender(_payload):
        raise HTTPException(status_code=503, detail="Configuração ausente: EMAIL_FROM_ADDRESS.")

    monkeypatch.setattr("mail.delivery_worker_service.send_provider_message", lambda payload, _settings: missing_sender(payload))
    decision = service.deliver_claimed(queue_item(), "smtp2go")

    assert decision.error_class == "configuration"
    assert decision.retryable is False
    assert any("SET status = 'error'" in sql for sql, _params in db.calls)


def test_message_build_failure_is_persisted_instead_of_leaving_processing(monkeypatch):
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())
    monkeypatch.setattr(
        "mail.delivery_worker_service.send_provider_message",
        lambda *_args: (_ for _ in ()).throw(AssertionError("provider não deve ser chamado")),
    )

    decision = service.deliver_claimed(queue_item(email="email-invalido"), "smtp2go")

    assert decision.error_class == "recipient"
    assert decision.queue_status == "error"
    assert decision.blocked is True
    update_sql, update_params = db.calls[0]
    assert "UPDATE email_queue" in update_sql
    assert update_params["status"] == "error"
    assert update_params["blocked"] == 1
    assert any("INSERT INTO email_send_log" in sql for sql, _params in db.calls)
    assert any("MERGE INTO email_blacklist" in sql for sql, _params in db.calls)
    assert db.commits == 1


def test_unsubscribe_configuration_failure_is_persisted_and_stops_campaign(monkeypatch):
    db = FakeSession()
    service = MailDeliveryWorkerService(db, worker_settings())
    monkeypatch.setattr(
        "mail.delivery_worker_service.unsubscribe_url",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("Configuração ausente: MAIL_UNSUBSCRIBE_SECRET.")),
    )
    monkeypatch.setattr(
        "mail.delivery_worker_service.send_provider_message",
        lambda *_args: (_ for _ in ()).throw(AssertionError("provider não deve ser chamado")),
    )

    decision = service.deliver_claimed(queue_item(), "smtp2go")

    assert decision.error_class == "configuration"
    assert decision.retryable is False
    assert any("UPDATE email_queue" in sql for sql, _params in db.calls)
    assert any("SET status = 'error'" in sql for sql, _params in db.calls)


def test_worker_service_depends_on_neutral_provider_not_test_route_module():
    source = (API / "mail/delivery_worker_service.py").read_text()
    assert "from mail.delivery_provider import" in source
    assert "delivery_test_service" not in source
