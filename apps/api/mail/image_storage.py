import base64
import html
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from core.settings import Settings

TENANT_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
IMAGE_FILENAME_PATTERN = re.compile(r"^[a-f0-9]{32}\.(?:png|jpg|webp|gif)$")
MARKDOWN_DATA_IMAGE_PATTERN = re.compile(
    r"^!\[([^\]]*)\]\(data:image/(png|jpeg|webp|gif);base64,([A-Za-z0-9+/=\r\n]+)\)$",
    re.IGNORECASE | re.DOTALL,
)


def normalize_tenant_code(value: str) -> str:
    tenant_code = str(value or "").strip().lower()
    if not TENANT_CODE_PATTERN.fullmatch(tenant_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant inválido para armazenamento de imagem.",
        )
    return tenant_code


def tenant_upload_dir(settings: Settings, tenant_code: str) -> Path:
    tenant = normalize_tenant_code(tenant_code)
    configured = str(settings.mail_upload_dir).strip()
    if not configured:
        raise RuntimeError("EMAIL_UPLOAD_DIR não configurado.")

    if "{tenant}" in configured:
        resolved = Path(configured.replace("{tenant}", tenant)).expanduser().resolve()
    else:
        resolved = (Path(configured).expanduser().resolve() / tenant)

    return resolved


def validate_image_filename(filename: str) -> str:
    normalized = str(filename or "").strip().lower()
    if not IMAGE_FILENAME_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagem não encontrada.")
    return normalized


def materialize_markdown_data_image(settings: Settings, tenant_code: str, body_html: str | None) -> str | None:
    """Convert a legacy Markdown data image into public, email-safe HTML."""
    if body_html is None:
        return None

    source = str(body_html).strip()
    match = MARKDOWN_DATA_IMAGE_PATTERN.fullmatch(source)
    if match is None:
        return body_html

    alt_text, subtype, encoded = match.groups()
    try:
        content = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Imagem Base64 inválida.") from error
    if not content:
        raise HTTPException(status_code=400, detail="A imagem está vazia.")
    if len(content) > settings.mail_upload_max_bytes:
        raise HTTPException(status_code=413, detail="A imagem excede o limite configurado.")

    tenant = normalize_tenant_code(tenant_code)
    extension = "jpg" if subtype.lower() == "jpeg" else subtype.lower()
    filename = f"{uuid4().hex}.{extension}"
    upload_dir = tenant_upload_dir(settings, tenant)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(content)

    public_base = settings.mail_public_upload_url.rstrip("/")
    public_url = f"{public_base}/{tenant}/{filename}"
    safe_alt = html.escape(alt_text.strip() or "Imagem da campanha", quote=True)
    return (
        f'<p><img src="{public_url}" alt="{safe_alt}" '
        'style="display:block;width:100%;max-width:100%;height:auto;margin:0 auto;"></p>'
    )
