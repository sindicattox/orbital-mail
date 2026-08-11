from __future__ import annotations

import json
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage
from html import unescape
from re import sub
from time import perf_counter
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from core.settings import Settings, get_settings


class MailProviderError(RuntimeError):
    def __init__(self, status_code: int, detail: Any) -> None:
        self.status_code = status_code
        self.detail = detail
        message = detail.get("message") if isinstance(detail, dict) else detail
        super().__init__(str(message or "Falha no provider de e-mail."))


class MailSendPayload(BaseModel):
    provider: str = Field(pattern="^(smtp2go|smtp)$")
    to_email: EmailStr
    to_name: str = Field(default="", max_length=255)
    subject: str = Field(min_length=1, max_length=500)
    body_html: str = Field(min_length=1)
    body_text: str | None = None
    from_name: str | None = Field(default=None, max_length=255)
    from_email: EmailStr | None = None
    reply_to: EmailStr | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()


class MailSendResponse(BaseModel):
    ok: bool
    provider: str
    message: str
    provider_message_id: str | None = None
    accepted: bool = False
    diagnostic: dict[str, Any] = Field(default_factory=dict)


def plain_text(html: str) -> str:
    text = sub(r"(?is)<(script|style).*?>.*?</\1>", "", html or "")
    text = sub(r"(?i)<br\s*/?>", "\n", text)
    text = sub(r"(?i)</p\s*>", "\n\n", text)
    text = sub(r"<[^>]+>", "", text)
    return unescape(text).strip()


def _resolve_sender(payload: MailSendPayload, settings: Settings) -> tuple[str, str, str | None]:
    from_email = str(payload.from_email or settings.mail_from_address or "").strip()
    if not from_email:
        raise MailProviderError(status_code=503, detail="Configuração ausente: EMAIL_FROM_ADDRESS.")
    from_name = (payload.from_name or settings.mail_from_name or "Orbital Mail").strip()
    reply_to = str(payload.reply_to or settings.mail_reply_to or "").strip() or None
    return from_email, from_name, reply_to


def send_smtp2go(payload: MailSendPayload, settings: Settings | None = None) -> MailSendResponse:
    settings = settings or get_settings()
    if not settings.smtp2go_api_key:
        raise MailProviderError(status_code=503, detail="Configuração ausente: SMTP2GO_API_KEY.")

    from_email, from_name, reply_to = _resolve_sender(payload, settings)
    request_payload: dict[str, Any] = {
        "to": [f"{payload.to_name} <{payload.to_email}>" if payload.to_name else str(payload.to_email)],
        "sender": f"{from_name} <{from_email}>",
        "subject": payload.subject,
        "html_body": payload.body_html,
        "text_body": payload.body_text or plain_text(payload.body_html),
    }
    if reply_to:
        request_payload["reply_to"] = reply_to
    if payload.headers:
        request_payload["custom_headers"] = [
            {"header": name, "value": value}
            for name, value in payload.headers.items()
        ]

    request = urllib.request.Request(
        settings.smtp2go_api_url,
        data=json.dumps(request_payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Smtp2go-Api-Key": settings.smtp2go_api_key,
        },
    )
    started_at = perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=settings.mail_send_timeout_seconds) as response:
            http_status = int(getattr(response, "status", 0) or 0)
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        try:
            provider_response: Any = json.loads(raw_body or "{}")
        except json.JSONDecodeError:
            provider_response = raw_body[:4000]
        raise MailProviderError(
            status_code=502,
            detail={
                "message": "SMTP2GO recusou a solicitação de envio.",
                "provider": "smtp2go",
                "accepted": False,
                "diagnostic": {
                    "http_status": exc.code,
                    "elapsed_ms": elapsed_ms,
                    "provider_response": provider_response,
                },
            },
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
        raise MailProviderError(
            status_code=502,
            detail={
                "message": "Não foi possível conectar ao SMTP2GO.",
                "provider": "smtp2go",
                "accepted": False,
                "diagnostic": {
                    "elapsed_ms": elapsed_ms,
                    "connection_error": str(getattr(exc, "reason", exc)),
                },
            },
        ) from exc

    elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
    try:
        result = json.loads(raw_body or "{}")
    except json.JSONDecodeError as exc:
        raise MailProviderError(
            status_code=502,
            detail={
                "message": "SMTP2GO retornou uma resposta inválida.",
                "provider": "smtp2go",
                "accepted": False,
                "diagnostic": {
                    "http_status": http_status,
                    "elapsed_ms": elapsed_ms,
                    "provider_response": raw_body[:4000],
                },
            },
        ) from exc

    data = result.get("data") or {}
    failures = data.get("failures") or []
    succeeded = data.get("succeeded")
    failed = data.get("failed")
    if failures or failed not in (None, 0) or succeeded == 0:
        raise MailProviderError(
            status_code=502,
            detail={
                "message": "SMTP2GO não aceitou o destinatário.",
                "provider": "smtp2go",
                "accepted": False,
                "diagnostic": {
                    "http_status": http_status,
                    "elapsed_ms": elapsed_ms,
                    "succeeded": succeeded,
                    "failed": failed,
                    "failures": failures,
                    "provider_response": result,
                },
            },
        )

    request_id = result.get("request_id") or data.get("request_id")
    email_id = data.get("email_id")
    return MailSendResponse(
        ok=True,
        accepted=True,
        provider="smtp2go",
        message="O SMTP2GO aceitou a solicitação de envio. Isso ainda não confirma entrega na caixa postal.",
        provider_message_id=email_id or request_id,
        diagnostic={
            "http_status": http_status,
            "elapsed_ms": elapsed_ms,
            "request_id": request_id,
            "email_id": email_id,
            "succeeded": succeeded,
            "failed": failed,
            "failures": failures,
            "provider_response": result,
        },
    )


def send_smtp(payload: MailSendPayload, settings: Settings | None = None) -> MailSendResponse:
    settings = settings or get_settings()
    if not settings.smtp_host:
        raise MailProviderError(status_code=503, detail="Configuração ausente: SMTP_HOST.")

    from_email, from_name, reply_to = _resolve_sender(payload, settings)
    message = EmailMessage()
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = f"{payload.to_name} <{payload.to_email}>" if payload.to_name else str(payload.to_email)
    message["Subject"] = payload.subject
    if reply_to:
        message["Reply-To"] = reply_to
    for name, value in payload.headers.items():
        message[name] = value
    message.set_content(payload.body_text or plain_text(payload.body_html))
    message.add_alternative(payload.body_html, subtype="html")

    security = settings.smtp_security
    started_at = perf_counter()
    smtp_diagnostic: dict[str, Any] = {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "security": security,
        "authenticated": bool(settings.smtp_username),
    }
    try:
        if security == "ssl":
            client = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.mail_send_timeout_seconds,
                context=ssl.create_default_context(),
            )
        else:
            client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.mail_send_timeout_seconds)
        with client:
            ehlo_code, ehlo_message = client.ehlo()
            smtp_diagnostic["ehlo_code"] = ehlo_code
            smtp_diagnostic["ehlo_message"] = (
                ehlo_message.decode("utf-8", errors="replace") if isinstance(ehlo_message, bytes) else str(ehlo_message)
            )
            if security == "tls":
                tls_code, tls_message = client.starttls(context=ssl.create_default_context())
                smtp_diagnostic["starttls_code"] = tls_code
                smtp_diagnostic["starttls_message"] = (
                    tls_message.decode("utf-8", errors="replace") if isinstance(tls_message, bytes) else str(tls_message)
                )
                client.ehlo()
            if settings.smtp_username:
                if not settings.smtp_password:
                    raise MailProviderError(status_code=503, detail="Configuração ausente: SMTP_PASSWORD.")
                login_code, login_message = client.login(settings.smtp_username, settings.smtp_password)
                smtp_diagnostic["login_code"] = login_code
                smtp_diagnostic["login_message"] = (
                    login_message.decode("utf-8", errors="replace") if isinstance(login_message, bytes) else str(login_message)
                )
            refused = client.send_message(message) or {}
            smtp_diagnostic["refused_recipients"] = {
                str(email): {
                    "code": value[0],
                    "message": value[1].decode("utf-8", errors="replace") if isinstance(value[1], bytes) else str(value[1]),
                }
                for email, value in refused.items()
            }
    except MailProviderError:
        raise
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        smtp_diagnostic["elapsed_ms"] = round((perf_counter() - started_at) * 1000, 2)
        smtp_diagnostic["error_type"] = type(exc).__name__
        smtp_diagnostic["error"] = str(exc)
        smtp_code = getattr(exc, "smtp_code", None)
        smtp_error = getattr(exc, "smtp_error", None)
        if smtp_code is not None:
            smtp_diagnostic["smtp_code"] = smtp_code
        if smtp_error is not None:
            smtp_diagnostic["smtp_error"] = (
                smtp_error.decode("utf-8", errors="replace") if isinstance(smtp_error, bytes) else str(smtp_error)
            )
        raise MailProviderError(
            status_code=502,
            detail={
                "message": "Não foi possível comunicar-se com o servidor SMTP.",
                "provider": "smtp",
                "accepted": False,
                "diagnostic": smtp_diagnostic,
            },
        ) from exc

    smtp_diagnostic["elapsed_ms"] = round((perf_counter() - started_at) * 1000, 2)
    refused_recipients = smtp_diagnostic.get("refused_recipients") or {}
    if refused_recipients:
        raise MailProviderError(
            status_code=502,
            detail={
                "message": "O servidor SMTP recusou um ou mais destinatários.",
                "provider": "smtp",
                "accepted": False,
                "diagnostic": smtp_diagnostic,
            },
        )

    return MailSendResponse(
        ok=True,
        accepted=True,
        provider="smtp",
        message="O servidor SMTP aceitou a mensagem. Isso ainda não confirma entrega na caixa postal.",
        diagnostic=smtp_diagnostic,
    )


def send_provider_message(payload: MailSendPayload, settings: Settings | None = None) -> MailSendResponse:
    settings = settings or get_settings()
    if payload.provider == "smtp2go":
        return send_smtp2go(payload, settings)
    return send_smtp(payload, settings)
