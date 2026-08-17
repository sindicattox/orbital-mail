from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import AuthContext, get_auth_context
from core.database import get_db
from core.settings import get_settings
from mail.runtime_config import SUPPORTED_PROVIDERS, effective_provider, provider_status, set_provider_override

router = APIRouter(tags=["mail-settings"])


class DeliveryProviderUpdate(BaseModel):
    provider: str = Field(pattern="^(ses|smtp2go|smtp)$")


def _response(db: Session, auth: AuthContext) -> dict:
    settings = get_settings()
    provider = effective_provider(db, auth.tenant_code, settings)
    return {
        "provider": provider,
        "env_provider": settings.mail_provider,
        "send_enabled": bool(settings.mail_send_enabled),
        "providers": [{"code": code, **provider_status(settings, code)} for code in SUPPORTED_PROVIDERS],
    }


@router.get("/settings/delivery")
def get_delivery_settings(db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    auth.require_dev()
    return _response(db, auth)


@router.put("/settings/delivery")
def update_delivery_settings(payload: DeliveryProviderUpdate, db: Session = Depends(get_db), auth: AuthContext = Depends(get_auth_context)):
    auth.require_dev()
    settings = get_settings()
    status = provider_status(settings, payload.provider)
    if not status["configured"]:
        raise HTTPException(status_code=409, detail=f"Provider {payload.provider} ainda não está configurado: {status['detail']}.")
    try:
        set_provider_override(db, auth.tenant_code, payload.provider, auth.user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _response(db, auth)
