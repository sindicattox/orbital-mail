from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from core.auth import AuthContext, get_auth_context
from core.settings import get_settings

router = APIRouter(tags=["Orbital Mail Images"])
settings = get_settings()

ALLOWED_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_campaign_image(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
):
    auth.require("mail.manage")

    extension = ALLOWED_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(415, "Formato não permitido. Use PNG, JPG, WEBP ou GIF.")

    content = await file.read(settings.mail_upload_max_bytes + 1)
    if not content:
        raise HTTPException(400, "A imagem está vazia.")
    if len(content) > settings.mail_upload_max_bytes:
        raise HTTPException(413, "A imagem excede o limite configurado.")

    # Cada tenant possui sua própria pasta. O código vem do contexto autenticado.
    upload_dir = (
        Path(settings.mail_upload_dir).expanduser().resolve() / auth.tenant_code
    )
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    destination = upload_dir / filename
    destination.write_bytes(content)

    public_base = settings.mail_public_upload_url.rstrip("/")
    return {
        "filename": filename,
        "url": f"{public_base}/{auth.tenant_code}/{filename}",
        "size": len(content),
        "content_type": file.content_type,
    }
