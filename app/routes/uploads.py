import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.config.settings import get_settings
from app.core.dependencies import require_roles
from app.core.exceptions import bad_request

router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _: dict = Depends(require_roles(["seller", "admin"])),
):
    settings = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise bad_request(f"Allowed extensions: {', '.join(ALLOWED)}")
    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise bad_request(f"File too large. Max {settings.max_upload_mb}MB")
    base_dir = Path(__file__).resolve().parent.parent.parent
    upload_path = base_dir / settings.upload_dir
    upload_path.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_path / filename
    with open(filepath, "wb") as f:
        f.write(content)
    url = f"/uploads/{filename}"
    return {"url": url, "filename": filename}
