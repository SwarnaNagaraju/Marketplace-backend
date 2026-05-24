from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("")
async def get_wishlist(user: dict = Depends(require_roles(["customer"]))):
    return await WishlistService.get(user["id"])


@router.post("/toggle/{product_id}")
async def toggle_wishlist(product_id: str, user: dict = Depends(require_roles(["customer"]))):
    return await WishlistService.toggle(user["id"], product_id)
