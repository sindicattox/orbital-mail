from fastapi import APIRouter, Depends, HTTPException, status

from core.auth import AuthContext, get_auth_context
from core.settings import get_settings
from mail.delivery_provider import (
    MailProviderError,
    MailSendPayload,
    MailSendResponse,
    plain_text,
    send_ses,
    send_smtp,
    send_smtp2go,
)

router = APIRouter(tags=["mail-test"])

# Mantém o contrato já usado pela rota de teste, enquanto o código de produção
# depende apenas do provider neutro.
TestSendPayload = MailSendPayload
TestSendResponse = MailSendResponse
_plain_text = plain_text


def _send_smtp2go(payload: TestSendPayload) -> TestSendResponse:
    try:
        return send_smtp2go(payload, get_settings())
    except MailProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _send_ses(payload: TestSendPayload) -> TestSendResponse:
    try:
        return send_ses(payload, get_settings())
    except MailProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _send_smtp(payload: TestSendPayload) -> TestSendResponse:
    try:
        return send_smtp(payload, get_settings())
    except MailProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/test-send", response_model=TestSendResponse)
def send_test_email(payload: TestSendPayload, context: AuthContext = Depends(get_auth_context)) -> TestSendResponse:
    context.require_dev()
    settings = get_settings()
    if not settings.mail_send_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Envio bloqueado. Configure EMAIL_SEND_ENABLED=true somente para executar o teste.",
        )
    if payload.provider == "smtp2go":
        return _send_smtp2go(payload)
    if payload.provider == "ses":
        return _send_ses(payload)
    return _send_smtp(payload)
