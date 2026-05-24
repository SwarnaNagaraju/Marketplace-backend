from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.schemas.cart import CartAddRequest, CartUpdateRequest
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("")
async def get_cart(user: dict = Depends(require_roles(["customer"]))):
    return await CartService.get_or_create_cart(user["id"])


@router.post("/add")
async def add_to_cart(data: CartAddRequest, user: dict = Depends(require_roles(["customer"]))):
    return await CartService.add_item(user["id"], data.productId, data.quantity)


@router.put("/{product_id}")
async def update_cart_item(
    product_id: str,
    data: CartUpdateRequest,
    user: dict = Depends(require_roles(["customer"])),
):
    return await CartService.update_quantity(user["id"], product_id, data.quantity)


@router.delete("/{product_id}")
async def remove_from_cart(product_id: str, user: dict = Depends(require_roles(["customer"]))):
    return await CartService.remove_item(user["id"], product_id)


@router.delete("")
async def clear_cart(user: dict = Depends(require_roles(["customer"]))):
    return await CartService.clear(user["id"])
