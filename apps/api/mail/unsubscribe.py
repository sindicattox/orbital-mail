import base64
import hashlib
import hmac
import json
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db
from core.settings import get_settings

router = APIRouter(tags=["mail-unsubscribe"])
TOKEN_VERSION = 1


class UnsubscribeInfo(BaseModel):
    ok: bool = True
    email_masked: str
    tenant_code: str
    campaign_id: int | None = None
    unsubscribed: bool = False


class UnsubscribeResult(UnsubscribeInfo):
    message: str


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _secret() -> bytes:
    value = str(get_settings().mail_unsubscribe_secret or "").strip()
    if not value:
        raise RuntimeError("Configuração ausente: MAIL_UNSUBSCRIBE_SECRET.")
    return value.encode("utf-8")


def create_unsubscribe_token(email: str, tenant_code: str, campaign_id: int | None = None) -> str:
    normalized_email = str(email or "").strip().lower()
    normalized_tenant = str(tenant_code or "").strip().lower()
    if not normalized_email or not normalized_tenant:
        raise ValueError("E-mail e tenant são obrigatórios para gerar o descadastro.")

    payload = {
        "v": TOKEN_VERSION,
        "email": normalized_email,
        "tenant": normalized_tenant,
        "campaign": int(campaign_id) if campaign_id is not None else None,
    }
    encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64encode(hmac.new(_secret(), encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def read_unsubscribe_token(token: str) -> dict:
    try:
        encoded, supplied_signature = str(token or "").split(".", 1)
        expected_signature = hmac.new(_secret(), encoded.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(supplied_signature), expected_signature):
            raise ValueError("assinatura inválida")
        payload = json.loads(_b64decode(encoded).decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link de descadastro inválido.") from exc

    email = str(payload.get("email") or "").strip().lower()
    tenant_code = str(payload.get("tenant") or "").strip().lower()
    campaign_id = payload.get("campaign")
    if payload.get("v") != TOKEN_VERSION or not email or not tenant_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link de descadastro inválido.")
    if campaign_id is not None:
        try:
            campaign_id = int(campaign_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link de descadastro inválido.") from exc
    return {"email": email, "tenant_code": tenant_code, "campaign_id": campaign_id}


def unsubscribe_url(email: str, tenant_code: str, campaign_id: int | None = None) -> str:
    base_url = str(get_settings().mail_public_url or "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("Configuração ausente: MAIL_PUBLIC_URL.")
    token = create_unsubscribe_token(email, tenant_code, campaign_id)
    return f"{base_url}/unsubscribe?{urlencode({'token': token})}"


def one_click_unsubscribe_url(email: str, tenant_code: str, campaign_id: int | None = None) -> str:
    base_url = str(get_settings().mail_public_url or "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("Configuração ausente: MAIL_PUBLIC_URL.")
    token = create_unsubscribe_token(email, tenant_code, campaign_id)
    return f"{base_url}/api/mail/public/unsubscribe?{urlencode({'token': token})}"


def unsubscribe_headers(url: str) -> dict[str, str]:
    return {
        "List-Unsubscribe": f"<{url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def append_unsubscribe_footer(body_html: str, body_text: str | None, url: str) -> tuple[str, str]:
    html_footer = (
        '<div style="margin-top:32px;padding-top:16px;border-top:1px solid #e5e7eb;'
        'font-family:Arial,sans-serif;font-size:12px;line-height:1.5;color:#6b7280;text-align:center">'
        f'Não deseja mais receber estes e-mails? <a href="{url}" style="color:#4b5563">Descadastrar</a>.'
        "</div>"
    )
    text_footer = f"\n\nNão deseja mais receber estes e-mails? Descadastrar: {url}"
    return f"{body_html or ''}{html_footer}", f"{body_text or ''}{text_footer}".strip()


def _mask_email(email: str) -> str:
    local, separator, domain = email.partition("@")
    if not separator:
        return "***"
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _is_unsubscribed(db: Session, email: str, tenant_code: str) -> bool:
    return bool(db.execute(text("""
        SELECT COUNT(*)
          FROM email_blacklist
         WHERE LOWER(TRIM(email)) = :email
           AND LOWER(TRIM(tenant_code)) = :tenant_code
           AND NVL(permanent, 1) = 1
    """), {"email": email, "tenant_code": tenant_code}).scalar_one())


@router.get("/public/unsubscribe", response_model=UnsubscribeInfo)
def get_unsubscribe(token: str, db: Session = Depends(get_db)) -> UnsubscribeInfo:
    payload = read_unsubscribe_token(token)
    return UnsubscribeInfo(
        email_masked=_mask_email(payload["email"]),
        tenant_code=payload["tenant_code"],
        campaign_id=payload["campaign_id"],
        unsubscribed=_is_unsubscribed(db, payload["email"], payload["tenant_code"]),
    )


@router.post("/public/unsubscribe", response_model=UnsubscribeResult)
def post_unsubscribe(
    token: str | None = Query(default=None),
    form_token: str | None = Form(default=None, alias="token"),
    db: Session = Depends(get_db),
) -> UnsubscribeResult:
    payload = read_unsubscribe_token(token or form_token or "")
    db.execute(text("""
        MERGE INTO email_blacklist b
        USING (
            SELECT :email AS email, :tenant_code AS tenant_code
              FROM dual
        ) src
           ON (
               LOWER(TRIM(b.email)) = src.email
               AND LOWER(TRIM(b.tenant_code)) = src.tenant_code
           )
        WHEN MATCHED THEN UPDATE SET
            b.reason = 'Descadastro solicitado pelo destinatário',
            b.source = 'unsubscribe',
            b.permanent = 1,
            b.updated_at = SYSDATE
        WHEN NOT MATCHED THEN INSERT (
            email, reason, created_at, tenant_code, source, permanent, updated_at
        ) VALUES (
            :email, 'Descadastro solicitado pelo destinatário', SYSDATE,
            :tenant_code, 'unsubscribe', 1, SYSDATE
        )
    """), {"email": payload["email"], "tenant_code": payload["tenant_code"]})
    db.commit()
    return UnsubscribeResult(
        email_masked=_mask_email(payload["email"]),
        tenant_code=payload["tenant_code"],
        campaign_id=payload["campaign_id"],
        unsubscribed=True,
        message="Descadastro confirmado.",
    )
