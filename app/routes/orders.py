from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.schemas.order import CheckoutRequest, OrderStatusUpdateRequest, SellerOrderActionRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/checkout")
async def checkout(data: CheckoutRequest, user: dict = Depends(require_roles(["customer"]))):
    return await OrderService.checkout(user["id"], data)


@router.get("/my")
async def my_orders(user: dict = Depends(require_roles(["customer"]))):
    return await OrderService.customer_orders(user["id"])


@router.get("/seller")
async def seller_orders(user: dict = Depends(require_roles(["seller"]))):
    return await OrderService.seller_orders(user["id"])


@router.patch("/{order_id}/status")
async def update_status(
    order_id: str,
    data: OrderStatusUpdateRequest,
    user: dict = Depends(require_roles(["seller", "admin"])),
):
    return await OrderService.update_status(user, order_id, data.orderStatus)


@router.post("/{order_id}/action")
async def seller_action(
    order_id: str,
    data: SellerOrderActionRequest,
    user: dict = Depends(require_roles(["seller"])),
):
    return await OrderService.seller_action(user["id"], order_id, data.action)
