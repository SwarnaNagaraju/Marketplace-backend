from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.schemas.quota import QuotaRequestCreate
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/quota-requests", tags=["Quota"])


@router.post("")
async def create_quota_request(
    data: QuotaRequestCreate,
    user: dict = Depends(require_roles(["seller"])),
):
    return await QuotaService.create_request(user, data)


@router.get("/my")
async def my_quota_requests(user: dict = Depends(require_roles(["seller"]))):
    return await QuotaService.seller_requests(user["id"])
