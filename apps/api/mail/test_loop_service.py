from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.auth import AuthContext, get_auth_context
from core.database import get_db, get_engine
from core.settings import API_DIR, get_settings
from mail.delivery_test_service import TestSendPayload as DeliveryTestSendPayload, _send_smtp, _send_smtp2go
from mail.delivery_policy import accepted_decision, exception_decision, DeliveryDecision

router = APIRouter(tags=["mail-loop-test"])
_stop_events: dict[int, threading.Event] = {}
_manager_lock = threading.Lock()


class LoopTestStart(BaseModel):
    provider: str = Field(pattern="^(smtp2go|smtp)$")
    emails: list[EmailStr] | None = None
    repetitions: int = Field(default=3, ge=1)
    workers: int = Field(default=2, ge=1)
    subject: str = Field(min_length=1, max_length=500)
    body_html: str = Field(min_length=1)
    body_text: str | None = None
    from_name: str | None = Field(default=None, max_length=255)
    from_email: EmailStr | None = None
    reply_to: EmailStr | None = None

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()


class LoopTestStartResponse(BaseModel):
    campaign_id: int
    unique_emails: int
    repetitions: int
    total_messages: int
    workers: int
    message: str


def _new_session() -> Session:
    engine = get_engine()
    session = Session(bind=engine, autoflush=False, autocommit=False)
    settings = get_settings()
    if settings.oracle_current_schema:
        session.execute(text(f"ALTER SESSION SET CURRENT_SCHEMA = {settings.oracle_current_schema}"))
    return session


def _dedupe_emails(values: list[EmailStr]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        email = str(value).strip().lower()
        if email and email not in seen:
            seen.add(email)
            result.append(email)
    return result




TEST_EMAILS_FILE = API_DIR / ".emails_para_teste"


def _load_test_emails() -> list[str]:
    """Lê a allowlist local de destinatários de teste, um endereço por linha."""
    if not TEST_EMAILS_FILE.is_file():
        raise HTTPException(
            status_code=409,
            detail=f"Arquivo de destinatários de teste não encontrado: {TEST_EMAILS_FILE}",
        )

    raw_values: list[str] = []
    for line_number, raw_line in enumerate(TEST_EMAILS_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue
        # Permite comentários no fim da linha: email@exemplo.com # principal
        value = value.split("#", 1)[0].strip()
        try:
            raw_values.append(str(EmailStr._validate(value)))
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"E-mail inválido em {TEST_EMAILS_FILE.name}, linha {line_number}: {value}",
            ) from exc

    emails = _dedupe_emails(raw_values)
    if not emails:
        raise HTTPException(
            status_code=409,
            detail=f"Nenhum e-mail foi configurado em {TEST_EMAILS_FILE}.",
        )
    return emails


def _create_test_campaign_and_queue(db: Session, tenant_code: str, payload: LoopTestStart, emails: list[str]) -> int:
    """Cria uma campanha técnica única e sua fila em uma única transação.

    O banco possui a restrição UK_EMAIL_CAMPAIGN_STATS (SUBJECT, SEND_DATE).
    Por isso, cada execução recebe um marcador único também no assunto e preenche
    SEND_DATE já na criação. Se qualquer etapa falhar, toda a transação é desfeita.
    """
    last_integrity_error: IntegrityError | None = None

    for _attempt in range(3):
        marker = f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{uuid4().hex[:8]}"
        internal_name = f"[TESTE LOOP] {marker}"
        # O assunto técnico precisa ser único por causa da restrição real do Oracle.
        # Mantém o texto informado pelo usuário e limita ao VARCHAR2(500).
        campaign_subject = f"[TESTE {marker}] {payload.subject}"[:500]

        try:
            db.execute(text("""
                INSERT INTO email_campaign (
                    tenant_code, internal_name, subject, body_html, body_text,
                    sender_name, sender_email, reply_to, send_date, status, created_at, updated_at
                ) VALUES (
                    :tenant_code, :internal_name, :subject, :body_html, :body_text,
                    :sender_name, :sender_email, :reply_to, SYSDATE, 'sending', SYSDATE, SYSDATE
                )
            """), {
                "tenant_code": tenant_code,
                "internal_name": internal_name,
                "subject": campaign_subject,
                "body_html": payload.body_html,
                "body_text": payload.body_text,
                "sender_name": payload.from_name,
                "sender_email": str(payload.from_email or get_settings().mail_from_address or ""),
                "reply_to": str(payload.reply_to or get_settings().mail_reply_to or "") or None,
            })
            campaign_id = int(db.execute(text("""
                SELECT id FROM email_campaign
                 WHERE tenant_code = :tenant_code AND internal_name = :internal_name
            """), {"tenant_code": tenant_code, "internal_name": internal_name}).scalar_one())

            rows = []
            for email in emails:
                for copy_no in range(1, payload.repetitions + 1):
                    rows.append({
                        "campaign_id": campaign_id,
                        "email": email,
                        "name": f"Teste {copy_no}/{payload.repetitions}",
                        "tenant_code": tenant_code,
                    })
            db.execute(text("""
                INSERT INTO email_queue (
                    email_campaign_id, member_id, member_insert_date, email, status,
                    name, blocked, priority, created_at, tenant_code, try_count
                ) VALUES (
                    :campaign_id, NULL, NULL, :email, 'pending',
                    :name, 0, 10, SYSDATE, :tenant_code, 0
                )
            """), rows)
            db.commit()
            return campaign_id
        except IntegrityError as exc:
            db.rollback()
            last_integrity_error = exc
            continue
        except Exception:
            db.rollback()
            raise

    raise HTTPException(
        status_code=409,
        detail="Não foi possível gerar uma identificação única para a campanha de teste. Tente novamente.",
    ) from last_integrity_error


def _reserve_one(db: Session, campaign_id: int, tenant_code: str) -> dict[str, Any] | None:
    statement = text("""
        SELECT id, email, name
          FROM email_queue
         WHERE email_campaign_id = :campaign_id
           AND LOWER(tenant_code) = LOWER(:tenant_code)
           AND status = 'pending'
           AND blocked = 0
           AND (next_try_at IS NULL OR next_try_at <= SYSDATE)
         ORDER BY priority, created_at, id
         FOR UPDATE SKIP LOCKED
    """).execution_options(stream_results=True, yield_per=1)
    row = db.execute(
        statement,
        {"campaign_id": campaign_id, "tenant_code": tenant_code},
    ).mappings().first()
    if row is None:
        db.rollback()
        return None
    db.execute(text("""
        UPDATE email_queue
           SET status = 'processing', last_try = SYSDATE, updated_at = SYSDATE,
               try_count = try_count + 1, error = NULL, retryable = 0
         WHERE id = :id
    """), {"id": row["id"]})
    db.commit()
    return dict(row)


def _load_campaign(db: Session, campaign_id: int, tenant_code: str) -> dict[str, Any]:
    row = db.execute(text("""
        SELECT subject, body_html, body_text, sender_name, sender_email, reply_to
          FROM email_campaign
         WHERE id = :campaign_id AND LOWER(tenant_code) = LOWER(:tenant_code)
    """), {"campaign_id": campaign_id, "tenant_code": tenant_code}).mappings().one()
    return dict(row)


def _finish_item(
    db: Session,
    queue_id: int,
    campaign_id: int,
    email: str,
    subject: str,
    decision: DeliveryDecision,
) -> None:
    next_try_sql = "SYSDATE + (1 / 1440)" if decision.retryable else "NULL"
    db.execute(text(f"""
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
        "queue_id": queue_id,
    })
    db.execute(text("""
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
        "queue_id": queue_id,
        "campaign_id": campaign_id,
        "email": email,
        "subject": subject,
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
        db.execute(text("""
            MERGE INTO email_blacklist b
            USING (SELECT :email AS email, :tenant_code AS tenant_code FROM dual) src
               ON (LOWER(b.email) = LOWER(src.email)
                   AND NVL(LOWER(b.tenant_code), '*') = NVL(LOWER(src.tenant_code), '*'))
            WHEN MATCHED THEN UPDATE SET
                b.reason = :reason, b.source = 'send_error', b.provider = :provider,
                b.permanent = 1, b.updated_at = SYSDATE
            WHEN NOT MATCHED THEN INSERT (
                email, reason, created_at, tenant_code, source, provider, permanent, updated_at
            ) VALUES (
                :email, :reason, SYSDATE, :tenant_code, 'send_error', :provider, 1, SYSDATE
            )
        """), {
            "email": email,
            "tenant_code": db.execute(text("SELECT tenant_code FROM email_queue WHERE id = :id"), {"id": queue_id}).scalar_one(),
            "reason": decision.error or "Erro definitivo do destinatário",
            "provider": decision.provider,
        })
    db.commit()


def _worker(campaign_id: int, tenant_code: str, provider: str, stop_event: threading.Event) -> None:
    settings = get_settings()
    while not stop_event.is_set():
        db = _new_session()
        try:
            item = _reserve_one(db, campaign_id, tenant_code)
            if item is None:
                return
            campaign = _load_campaign(db, campaign_id, tenant_code)
            payload = DeliveryTestSendPayload(
                provider=provider,
                to_email=item["email"],
                to_name=item.get("name") or "",
                subject=campaign["subject"],
                body_html=campaign.get("body_html") or "",
                body_text=campaign.get("body_text"),
                from_name=campaign.get("sender_name"),
                from_email=campaign.get("sender_email"),
                reply_to=campaign.get("reply_to"),
            )
            try:
                result = _send_smtp2go(payload) if provider == "smtp2go" else _send_smtp(payload)
                provider_message_id = result.provider_message_id
                if provider == "smtp2go":
                    provider_message_id = (
                        ((result.diagnostic.get("provider_response") or {}).get("data") or {}).get("email_id")
                        or provider_message_id
                    )
                decision = accepted_decision(provider, result)
                _finish_item(db, int(item["id"]), campaign_id, item["email"], campaign["subject"], decision)
            except Exception as exc:  # classifica retry, bloqueio e erro de configuração
                try_count = int(db.execute(text("SELECT try_count FROM email_queue WHERE id = :id"), {"id": item["id"]}).scalar_one() or 0)
                decision = exception_decision(provider, exc, try_count, settings.mail_worker_max_attempts)
                _finish_item(db, int(item["id"]), campaign_id, item["email"], campaign["subject"], decision)
                if decision.error_class == "configuration":
                    stop_event.set()
                    db.execute(text("""
                        UPDATE email_campaign SET status = 'error', updated_at = SYSDATE
                         WHERE id = :campaign_id AND LOWER(tenant_code) = LOWER(:tenant_code)
                    """), {"campaign_id": campaign_id, "tenant_code": tenant_code})
                    db.commit()
                    return
            if settings.mail_worker_delay_ms > 0:
                time.sleep(settings.mail_worker_delay_ms / 1000)
        finally:
            db.close()


def _run_job(campaign_id: int, tenant_code: str, provider: str, workers: int, stop_event: threading.Event) -> None:
    try:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix=f"mail-test-{campaign_id}") as executor:
            futures = [executor.submit(_worker, campaign_id, tenant_code, provider, stop_event) for _ in range(workers)]
            for future in futures:
                future.result()

        db = _new_session()
        try:
            remaining = int(db.execute(text("""
                SELECT COUNT(*) FROM email_queue
                 WHERE email_campaign_id = :campaign_id
                   AND LOWER(tenant_code) = LOWER(:tenant_code)
                   AND status IN ('pending', 'processing')
            """), {"campaign_id": campaign_id, "tenant_code": tenant_code}).scalar_one() or 0)
            current_status = str(db.execute(text("""
                SELECT LOWER(status) FROM email_campaign
                 WHERE id = :campaign_id
                   AND LOWER(tenant_code) = LOWER(:tenant_code)
            """), {"campaign_id": campaign_id, "tenant_code": tenant_code}).scalar_one() or "")
            if current_status == "error":
                final_status = "error"
            elif remaining:
                final_status = "paused"
            else:
                final_status = "completed"
            db.execute(text("""
                UPDATE email_campaign
                   SET status = :status,
                       send_date = CASE WHEN :status = 'completed' THEN SYSDATE ELSE send_date END,
                       updated_at = SYSDATE
                 WHERE id = :campaign_id
                   AND LOWER(tenant_code) = LOWER(:tenant_code)
            """), {
                "status": final_status,
                "campaign_id": campaign_id,
                "tenant_code": tenant_code,
            })
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        # Nunca deixa a tela presa em “em andamento” quando o gerenciador falha.
        db = _new_session()
        try:
            db.execute(text("""
                UPDATE email_queue
                   SET status = 'pending',
                       error = :error
                 WHERE email_campaign_id = :campaign_id
                   AND LOWER(tenant_code) = LOWER(:tenant_code)
                   AND status = 'processing'
            """), {
                "error": f"Worker interrompido: {exc}"[:3900],
                "campaign_id": campaign_id,
                "tenant_code": tenant_code,
            })
            db.execute(text("""
                UPDATE email_campaign
                   SET status = 'error', updated_at = SYSDATE
                 WHERE id = :campaign_id
                   AND LOWER(tenant_code) = LOWER(:tenant_code)
            """), {"campaign_id": campaign_id, "tenant_code": tenant_code})
            db.commit()
        finally:
            db.close()
    finally:
        with _manager_lock:
            _stop_events.pop(campaign_id, None)


@router.get("/test-loop/allowed-emails")
def allowed_test_emails(auth: AuthContext = Depends(get_auth_context)):
    auth.require("mail.send")
    emails = _load_test_emails()
    return {
        "file": TEST_EMAILS_FILE.name,
        "count": len(emails),
        "emails": emails,
    }


@router.post("/test-loop/start", response_model=LoopTestStartResponse, status_code=status.HTTP_202_ACCEPTED)
def start_loop_test(payload: LoopTestStart, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    auth.require("mail.send")
    settings = get_settings()
    if not settings.mail_send_enabled:
        raise HTTPException(status_code=409, detail="Envio bloqueado. Configure MAIL_SEND_ENABLED=true.")
    configured_emails = _load_test_emails()
    requested_emails = _dedupe_emails(payload.emails or [])
    if requested_emails:
        unauthorized = sorted(set(requested_emails) - set(configured_emails))
        if unauthorized:
            raise HTTPException(
                status_code=422,
                detail="Destinatário(s) não autorizado(s) em .emails_para_teste: " + ", ".join(unauthorized),
            )
        emails = requested_emails
    else:
        emails = configured_emails
    if len(emails) > settings.mail_test_max_recipients:
        raise HTTPException(status_code=422, detail=f"Máximo de {settings.mail_test_max_recipients} e-mails únicos por teste.")
    if payload.repetitions > settings.mail_test_max_repetitions:
        raise HTTPException(status_code=422, detail=f"Máximo de {settings.mail_test_max_repetitions} repetições por e-mail.")
    if payload.workers > settings.mail_test_max_workers:
        raise HTTPException(status_code=422, detail=f"Máximo de {settings.mail_test_max_workers} workers no teste.")
    total = len(emails) * payload.repetitions
    if total > settings.mail_test_max_messages:
        raise HTTPException(status_code=422, detail=f"Máximo de {settings.mail_test_max_messages} mensagens por teste.")

    try:
        campaign_id = _create_test_campaign_and_queue(db, auth.tenant_code, payload, emails)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Falha ao criar a campanha e a fila de teste no Oracle.",
        ) from exc

    stop_event = threading.Event()
    with _manager_lock:
        _stop_events[campaign_id] = stop_event
    thread = threading.Thread(
        target=_run_job,
        args=(campaign_id, auth.tenant_code, payload.provider, payload.workers, stop_event),
        daemon=True,
        name=f"mail-loop-manager-{campaign_id}",
    )
    thread.start()
    return LoopTestStartResponse(
        campaign_id=campaign_id,
        unique_emails=len(emails),
        repetitions=payload.repetitions,
        total_messages=total,
        workers=payload.workers,
        message=f"Teste iniciado: {total} mensagens com {payload.workers} worker(s).",
    )


@router.get("/test-loop/{campaign_id}/status")
def loop_test_status(campaign_id: int, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    auth.require("mail.view")
    row = db.execute(text("""
        SELECT c.id, c.internal_name, c.status,
               COUNT(q.id) AS total,
               SUM(CASE WHEN q.status = 'pending' THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN q.status = 'processing' THEN 1 ELSE 0 END) AS processing,
               SUM(CASE WHEN q.status = 'sent' THEN 1 ELSE 0 END) AS sent,
               SUM(CASE WHEN q.status IN ('error', 'invalid_email') THEN 1 ELSE 0 END) AS errors
          FROM email_campaign c
          LEFT JOIN email_queue q ON q.email_campaign_id = c.id AND LOWER(q.tenant_code) = LOWER(c.tenant_code)
         WHERE c.id = :campaign_id AND LOWER(c.tenant_code) = LOWER(:tenant_code)
         GROUP BY c.id, c.internal_name, c.status
    """), {"campaign_id": campaign_id, "tenant_code": auth.tenant_code}).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Teste não encontrado.")
    result = dict(row)
    for key in ("total", "pending", "processing", "sent", "errors"):
        result[key] = int(result[key] or 0)
    with _manager_lock:
        manager_active = campaign_id in _stop_events

    # Após reload da API, threads em memória deixam de existir. Marca o teste como
    # interrompido em vez de manter a interface eternamente em 0%.
    if result["status"] == "sending" and not manager_active and result["processing"] == 0 and result["pending"] > 0:
        db.execute(text("""
            UPDATE email_campaign
               SET status = 'error', updated_at = SYSDATE
             WHERE id = :campaign_id
               AND LOWER(tenant_code) = LOWER(:tenant_code)
        """), {"campaign_id": campaign_id, "tenant_code": auth.tenant_code})
        db.commit()
        result["status"] = "error"
        result["job_error"] = "Worker interrompido ou API recarregada. Inicie um novo teste."

    terminal_status = result["status"] in {"completed", "error", "paused", "cancelled"}
    done = terminal_status or (result["pending"] == 0 and result["processing"] == 0)
    result["done"] = done
    result["manager_active"] = manager_active
    result["percent"] = round(((result["sent"] + result["errors"]) / result["total"] * 100), 1) if result["total"] else 100.0
    return result


@router.post("/test-loop/{campaign_id}/stop")
def stop_loop_test(campaign_id: int, auth: AuthContext = Depends(get_auth_context)):
    auth.require("mail.send")
    with _manager_lock:
        event = _stop_events.get(campaign_id)
    if event is None:
        return {"stopped": False, "message": "O teste já terminou ou não está ativo nesta instância da API."}
    event.set()
    return {"stopped": True, "message": "Parada solicitada. Mensagens em processamento terminam; pendentes permanecem na fila."}
