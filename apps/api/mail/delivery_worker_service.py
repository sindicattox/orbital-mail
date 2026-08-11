from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.settings import Settings, get_settings
from mail.delivery_policy import DeliveryDecision, accepted_decision, exception_decision
from mail.delivery_provider import MailSendPayload, send_provider_message
from mail.unsubscribe import (
    append_unsubscribe_footer,
    one_click_unsubscribe_url,
    unsubscribe_headers,
    unsubscribe_url,
)

TEST_CAMPAIGN_PATTERN = "[TESTE LOOP]%"


class MailSendWorkerSchemaMissingError(RuntimeError):
    """O banco ainda não possui o contrato persistente exigido pelo worker."""


def _is_missing_worker_schema(exc: BaseException) -> bool:
    message = str(exc).upper()
    return any(code in message for code in ("ORA-00942", "ORA-00904", "DOES NOT EXIST", "NO SUCH TABLE"))


class MailDeliveryWorkerService:
    """Motor único de entrega da EMAIL_QUEUE.

    O teste controlado e o worker de produção usam exatamente o mesmo claim,
    montagem de mensagem, política de retry, blacklist e log. A diferença é só
    o escopo da fila: o worker real ignora campanhas técnicas [TESTE LOOP].
    """

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def check_readiness(self) -> None:
        try:
            self.db.execute(text("""
                SELECT q.id, q.status, q.try_count, q.next_try_at, q.retryable,
                       q.provider, q.provider_status, q.provider_code,
                       q.provider_message_id, q.last_error_class,
                       c.id, c.tenant_code, c.internal_name, c.status
                  FROM email_queue q
                  JOIN email_campaign c ON c.id = q.email_campaign_id
                 WHERE 1 = 0
            """))
            self.db.execute(text("""
                SELECT id, email_queue_id, email_campaign_id, status, event_type,
                       provider, provider_code, error_class, retryable, raw_response
                  FROM email_send_log
                 WHERE 1 = 0
            """))
            self.db.execute(text("""
                SELECT id, email, tenant_code, source, provider, permanent
                  FROM email_blacklist
                 WHERE 1 = 0
            """))
        except (DBAPIError, SQLAlchemyError) as exc:
            if _is_missing_worker_schema(exc):
                raise MailSendWorkerSchemaMissingError(
                    "Worker de e-mail não configurado no banco. Execute as migrations "
                    "database/oracle/001_email_campaign_columns.sql, "
                    "database/oracle/002_email_delivery_events.sql e "
                    "database/oracle/003_drop_legacy_campaign_stats_unique.sql."
                ) from exc
            raise
        finally:
            if self.db.in_transaction():
                self.db.rollback()

    def claim_next(
        self,
        *,
        campaign_id: int | None = None,
        tenant_code: str | None = None,
        include_test_campaigns: bool = False,
    ) -> dict[str, Any] | None:
        filters = [
            "q.status = 'pending'",
            "q.blocked = 0",
            "(q.next_try_at IS NULL OR q.next_try_at <= SYSDATE)",
            "c.status = 'sending'",
        ]
        params: dict[str, Any] = {}
        if campaign_id is not None:
            filters.append("q.email_campaign_id = :campaign_id")
            params["campaign_id"] = campaign_id
        if tenant_code is not None:
            filters.append("LOWER(q.tenant_code) = LOWER(:tenant_code)")
            params["tenant_code"] = tenant_code
        if not include_test_campaigns:
            filters.append("NVL(c.internal_name, '') NOT LIKE :test_campaign_pattern")
            params["test_campaign_pattern"] = TEST_CAMPAIGN_PATTERN

        statement = text(f"""
            SELECT q.id, q.email_campaign_id, q.tenant_code, q.email, q.name, q.try_count,
                   c.subject, c.body_html, c.body_text,
                   c.sender_name, c.sender_email, c.reply_to
              FROM email_queue q
              JOIN email_campaign c
                ON c.id = q.email_campaign_id
               AND LOWER(c.tenant_code) = LOWER(q.tenant_code)
             WHERE {' AND '.join(filters)}
             ORDER BY q.priority, q.created_at, q.id
             FOR UPDATE OF q.status SKIP LOCKED
        """).execution_options(stream_results=True, yield_per=1)
        row = self.db.execute(statement, params).mappings().first()
        if row is None:
            self.db.rollback()
            return None

        item = dict(row)
        self.db.execute(text("""
            UPDATE email_queue
               SET status = 'processing',
                   last_try = SYSDATE,
                   updated_at = SYSDATE,
                   try_count = try_count + 1,
                   error = NULL,
                   retryable = 0
             WHERE id = :id
        """), {"id": item["id"]})
        self.db.commit()
        item["try_count"] = int(item.get("try_count") or 0) + 1
        return item

    def recover_stale(self, stale_seconds: int) -> int:
        result = self.db.execute(text("""
            UPDATE email_queue q
               SET status = 'pending',
                   retryable = 1,
                   next_try_at = NULL,
                   error = 'Worker interrompido durante o processamento; item devolvido à fila.',
                   updated_at = SYSDATE
             WHERE q.status = 'processing'
               AND q.blocked = 0
               AND q.last_try < SYSDATE - (:stale_seconds / 86400)
               AND EXISTS (
                    SELECT 1
                      FROM email_campaign c
                     WHERE c.id = q.email_campaign_id
                       AND LOWER(c.tenant_code) = LOWER(q.tenant_code)
                       AND c.status = 'sending'
                       AND NVL(c.internal_name, '') NOT LIKE :test_campaign_pattern
               )
        """), {
            "stale_seconds": stale_seconds,
            "test_campaign_pattern": TEST_CAMPAIGN_PATTERN,
        })
        self.db.commit()
        return int(result.rowcount or 0)

    def deliver_claimed(self, item: dict[str, Any], provider: str) -> DeliveryDecision:
        campaign_id = int(item["email_campaign_id"])
        tenant_code = str(item["tenant_code"])

        try:
            email = str(item["email"])
            opt_out_url = unsubscribe_url(email, tenant_code, campaign_id)
            one_click_url = one_click_unsubscribe_url(email, tenant_code, campaign_id)
            body_html, body_text = append_unsubscribe_footer(
                item.get("body_html") or "",
                item.get("body_text"),
                opt_out_url,
            )
            payload = MailSendPayload(
                provider=provider,
                to_email=email,
                to_name=item.get("name") or "",
                subject=item["subject"],
                body_html=body_html,
                body_text=body_text,
                from_name=item.get("sender_name"),
                from_email=item.get("sender_email"),
                reply_to=item.get("reply_to"),
                headers=unsubscribe_headers(one_click_url),
            )
            result = send_provider_message(payload, self.settings)
            decision = accepted_decision(provider, result)
        except Exception as exc:
            decision = exception_decision(
                provider,
                exc,
                int(item.get("try_count") or 0),
                self.settings.mail_worker_max_attempts,
            )

        self.finish_item(item, decision)
        if decision.error_class == "configuration":
            self.mark_campaign_error(campaign_id, tenant_code)
        return decision

    def finish_item(self, item: dict[str, Any], decision: DeliveryDecision) -> None:
        next_try_sql = "SYSDATE + (1 / 1440)" if decision.retryable else "NULL"
        self.db.execute(text(f"""
            UPDATE email_queue
               SET status = :status,
                   provider = :provider,
                   provider_status = :provider_status,
                   provider_code = :provider_code,
                   provider_message_id = NVL(:provider_message_id, provider_message_id),
                   provider_last_event_at = SYSDATE,
                   last_error_class = :error_class,
                   retryable = :retryable,
                   blocked = :blocked,
                   next_try_at = {next_try_sql},
                   error = :error,
                   last_try = SYSDATE,
                   updated_at = SYSDATE
             WHERE id = :queue_id
        """), {
            "status": decision.queue_status,
            "provider": decision.provider,
            "provider_status": decision.provider_status,
            "provider_code": decision.provider_code,
            "provider_message_id": decision.provider_message_id,
            "error_class": decision.error_class,
            "retryable": 1 if decision.retryable else 0,
            "blocked": 1 if decision.blocked else 0,
            "error": decision.error,
            "queue_id": int(item["id"]),
        })
        self.db.execute(text("""
            INSERT INTO email_send_log (
                email_queue_id, email_campaign_id, email, subject, status, error, created_at,
                provider_message_id, event_type, provider, provider_code, error_class,
                retryable, raw_response, event_at
            ) VALUES (
                :queue_id, :campaign_id, :email, :subject, :status, :error, SYSDATE,
                :provider_message_id, :event_type, :provider, :provider_code, :error_class,
                :retryable, :raw_response, SYSDATE
            )
        """), {
            "queue_id": int(item["id"]),
            "campaign_id": int(item["email_campaign_id"]),
            "email": str(item["email"]),
            "subject": str(item["subject"]),
            "status": decision.log_status,
            "error": decision.error,
            "provider_message_id": decision.provider_message_id,
            "event_type": decision.event_type,
            "provider": decision.provider,
            "provider_code": decision.provider_code,
            "error_class": decision.error_class,
            "retryable": 1 if decision.retryable else 0,
            "raw_response": decision.raw_response,
        })

        if decision.blocked and decision.error_class == "recipient":
            self.db.execute(text("""
                MERGE INTO email_blacklist b
                USING (SELECT :email AS email, :tenant_code AS tenant_code FROM dual) src
                   ON (LOWER(b.email) = LOWER(src.email)
                       AND NVL(LOWER(b.tenant_code), '*') = NVL(LOWER(src.tenant_code), '*'))
                WHEN MATCHED THEN UPDATE SET
                    b.reason = :reason,
                    b.source = 'send_error',
                    b.provider = :provider,
                    b.permanent = 1,
                    b.updated_at = SYSDATE
                WHEN NOT MATCHED THEN INSERT (
                    email, reason, created_at, tenant_code, source, provider, permanent, updated_at
                ) VALUES (
                    :email, :reason, SYSDATE, :tenant_code, 'send_error', :provider, 1, SYSDATE
                )
            """), {
                "email": str(item["email"]),
                "tenant_code": str(item["tenant_code"]),
                "reason": decision.error or "Erro definitivo do destinatário",
                "provider": decision.provider,
            })
        self.db.commit()

    def mark_campaign_error(self, campaign_id: int, tenant_code: str) -> None:
        self.db.execute(text("""
            UPDATE email_campaign
               SET status = 'error', updated_at = SYSDATE
             WHERE id = :campaign_id
               AND LOWER(tenant_code) = LOWER(:tenant_code)
        """), {"campaign_id": campaign_id, "tenant_code": tenant_code})
        self.db.commit()

    def finalize_completed_campaigns(self) -> int:
        result = self.db.execute(text("""
            UPDATE email_campaign c
               SET status = 'completed',
                   send_date = NVL(send_date, SYSDATE),
                   updated_at = SYSDATE
             WHERE c.status = 'sending'
               AND NVL(c.internal_name, '') NOT LIKE :test_campaign_pattern
               AND EXISTS (
                    SELECT 1
                      FROM email_queue q
                     WHERE q.email_campaign_id = c.id
                       AND LOWER(q.tenant_code) = LOWER(c.tenant_code)
               )
               AND NOT EXISTS (
                    SELECT 1
                      FROM email_queue q
                     WHERE q.email_campaign_id = c.id
                       AND LOWER(q.tenant_code) = LOWER(c.tenant_code)
                       AND q.status IN ('pending', 'processing')
               )
        """), {"test_campaign_pattern": TEST_CAMPAIGN_PATTERN})
        self.db.commit()
        return int(result.rowcount or 0)

    def process_one(
        self,
        provider: str,
        *,
        campaign_id: int | None = None,
        tenant_code: str | None = None,
        include_test_campaigns: bool = False,
    ) -> DeliveryDecision | None:
        if not self.settings.mail_send_enabled:
            return None
        item = self.claim_next(
            campaign_id=campaign_id,
            tenant_code=tenant_code,
            include_test_campaigns=include_test_campaigns,
        )
        if item is None:
            return None
        return self.deliver_claimed(item, provider)
