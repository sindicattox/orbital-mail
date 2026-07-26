from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from core.auth import AuthContext, get_auth_context
from core.settings import get_settings
from mail.image_storage import tenant_upload_dir, validate_image_filename

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

    upload_dir = tenant_upload_dir(settings, auth.tenant_code)
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


@router.get("/uploads/{tenant_code}/{filename}", include_in_schema=False)
def public_campaign_image(tenant_code: str, filename: str):
    safe_filename = validate_image_filename(filename)
    image_path = tenant_upload_dir(settings, tenant_code) / safe_filename
    if not image_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagem não encontrada.")

    return FileResponse(
        image_path,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
