from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.schemas.review import ReviewCreateRequest
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/product/{product_id}")
async def product_reviews(product_id: str):
    return await ReviewService.by_product(product_id)


@router.post("")
async def create_review(
    data: ReviewCreateRequest,
    user: dict = Depends(require_roles(["customer"])),
):
    return await ReviewService.create(user["id"], data)
