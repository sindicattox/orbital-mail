from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException


@dataclass(frozen=True)
class DeliveryDecision:
    provider: str
    queue_status: str
    provider_status: str
    log_status: str
    event_type: str
    error_class: str | None
    retryable: bool
    blocked: bool
    provider_code: str | None
    provider_message_id: str | None
    error: str | None
    raw_response: str | None


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, default=str)[:30000]
    except Exception:
        return str(value)[:30000]


def accepted_decision(provider: str, result: Any) -> DeliveryDecision:
    diagnostic = getattr(result, "diagnostic", {}) or {}
    provider_message_id = getattr(result, "provider_message_id", None)
    if provider == "smtp2go":
        response = diagnostic.get("provider_response") or {}
        provider_message_id = ((response.get("data") or {}).get("email_id") or provider_message_id)
    return DeliveryDecision(
        provider=provider,
        queue_status="sent",
        provider_status="accepted",
        log_status="success",
        event_type="accepted",
        error_class=None,
        retryable=False,
        blocked=False,
        provider_code=str(diagnostic.get("http_status") or diagnostic.get("smtp_code") or "") or None,
        provider_message_id=provider_message_id,
        error=None,
        raw_response=_json_text(diagnostic),
    )


def exception_decision(provider: str, exc: Exception, try_count: int, max_attempts: int) -> DeliveryDecision:
    detail = getattr(exc, "detail", None)
    diagnostic: dict[str, Any] = {}
    message = str(exc)
    if isinstance(detail, dict):
        diagnostic = detail.get("diagnostic") or {}
        message = str(detail.get("message") or detail)
    elif detail is not None:
        message = str(detail)

    normalized = f"{message} {diagnostic}".lower()
    provider_code = diagnostic.get("http_status") or diagnostic.get("smtp_code")

    configuration_terms = (
        "api_key", "api key", "credential", "authentication", "auth", "sender",
        "remetente", "not verified", "não verificado", "account suspended",
        "conta suspensa", "daily quota", "cota diária",
        "configuração ausente", "configuration missing", "missing configuration",
        "email_from_address", "mail_public_url", "mail_unsubscribe_secret",
        "smtp_host", "smtp_password",
    )
    recipient_terms = (
        "invalid recipient", "invalid email", "not a valid email address", "email address is not valid",
        "destinatário inválido", "recipient rejected",
        "mailbox unavailable", "user unknown", "does not exist", "suppressed",
        "unsubscribe", "complaint", "hard bounce",
    )
    temporary_terms = (
        "timeout", "timed out", "temporarily", "temporary", "rate limit", "throttl",
        "connection", "conectar", "service unavailable", "try again", "soft bounce",
        "maximum sending rate",
    )

    if any(term in normalized for term in configuration_terms):
        error_class = "configuration"
        retryable = False
        blocked = False
    elif any(term in normalized for term in recipient_terms):
        error_class = "recipient"
        retryable = False
        blocked = True
    elif any(term in normalized for term in temporary_terms):
        error_class = "temporary"
        retryable = try_count < max_attempts
        blocked = False
    else:
        # HTTP 429 e 5xx tendem a ser transitórios; demais erros ficam como provider.
        code = int(provider_code) if str(provider_code or "").isdigit() else None
        if code == 429 or (code is not None and code >= 500):
            error_class = "temporary"
            retryable = try_count < max_attempts
        else:
            error_class = "provider"
            retryable = False
        blocked = False

    queue_status = "pending" if retryable else "error"
    return DeliveryDecision(
        provider=provider,
        queue_status=queue_status,
        provider_status="rejected",
        log_status="error",
        event_type="send_error",
        error_class=error_class,
        retryable=retryable,
        blocked=blocked,
        provider_code=str(provider_code) if provider_code is not None else None,
        provider_message_id=None,
        error=message[:3900],
        raw_response=_json_text(detail if detail is not None else {"error": str(exc)}),
    )
