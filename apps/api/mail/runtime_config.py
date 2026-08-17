from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.settings import Settings

SUPPORTED_PROVIDERS = ("ses", "smtp2go", "smtp")


def _missing_table(exc: BaseException) -> bool:
    message = str(exc).upper()
    return "ORA-00942" in message or "DOES NOT EXIST" in message or "NO SUCH TABLE" in message


def provider_status(settings: Settings, provider: str) -> dict:
    if provider == "smtp2go":
        return {"configured": bool(str(settings.smtp2go_api_key or "").strip()), "detail": "SMTP2GO_API_KEY"}
    if provider == "smtp":
        return {"configured": bool(str(settings.smtp_host or "").strip()), "detail": "SMTP_HOST"}
    if provider == "ses":
        ready = bool(str(settings.aws_ses_region or "").strip() and str(settings.mail_from_address or "").strip())
        return {"configured": ready, "detail": f"AWS SDK · {settings.aws_ses_region}"}
    return {"configured": False, "detail": "Provider inválido"}


def get_provider_override(db: Session, tenant_code: str) -> str | None:
    try:
        value = db.execute(text("""
            SELECT LOWER(provider)
              FROM email_delivery_config
             WHERE LOWER(tenant_code) = LOWER(:tenant_code)
        """), {"tenant_code": tenant_code}).scalar_one_or_none()
        return str(value).strip().lower() if value else None
    except (DBAPIError, SQLAlchemyError) as exc:
        if db.in_transaction():
            db.rollback()
        if _missing_table(exc):
            return None
        raise


def effective_provider(db: Session, tenant_code: str, settings: Settings) -> str:
    provider = get_provider_override(db, tenant_code) or settings.mail_provider
    return provider if provider in SUPPORTED_PROVIDERS else settings.mail_provider


def set_provider_override(db: Session, tenant_code: str, provider: str, user_id: int) -> None:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ValueError("Provider inválido.")
    try:
        db.execute(text("""
            MERGE INTO email_delivery_config target
            USING (SELECT :tenant_code AS tenant_code FROM dual) source
               ON (LOWER(target.tenant_code) = LOWER(source.tenant_code))
            WHEN MATCHED THEN UPDATE SET
                target.provider = :provider,
                target.updated_by = :updated_by,
                target.updated_at = SYSDATE
            WHEN NOT MATCHED THEN INSERT (tenant_code, provider, updated_by, updated_at)
                VALUES (:tenant_code, :provider, :updated_by, SYSDATE)
        """), {"tenant_code": tenant_code, "provider": normalized, "updated_by": user_id})
        db.commit()
    except (DBAPIError, SQLAlchemyError) as exc:
        if db.in_transaction():
            db.rollback()
        if _missing_table(exc):
            raise RuntimeError("Configuração dinâmica de provider ainda não foi instalada no banco (migration 004).") from exc
        raise
