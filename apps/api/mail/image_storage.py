import re
from pathlib import Path

from fastapi import HTTPException, status

from core.settings import Settings

TENANT_CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
IMAGE_FILENAME_PATTERN = re.compile(r"^[a-f0-9]{32}\.(?:png|jpg|webp|gif)$")


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
