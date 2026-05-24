from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_roles
from app.database import get_database
from app.models import collections as C
from app.schemas.address import ShippingAddressSchema
from app.schemas.auth import UserUpdateRequest
from app.services.address_service import AddressService
from app.utils.helpers import oid, serialize_doc, utc_now

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/shipping-address")
async def get_shipping_address(user: dict = Depends(require_roles(["customer"]))):
    """Get the customer's saved shipping address."""
    address = await AddressService.get_shipping_address(user["id"])
    return {"address": address}


@router.put("/shipping-address")
async def save_shipping_address(
    data: ShippingAddressSchema,
    user: dict = Depends(require_roles(["customer"])),
):
    """Save or update the customer's default shipping address."""
    updated_user = await AddressService.save_shipping_address(user["id"], data)
    return {
        "message": "Shipping address saved",
        "address": updated_user.get("address"),
        "user": updated_user,
    }


@router.put("/profile")
async def update_profile(data: UserUpdateRequest, user: dict = Depends(get_current_user)):
    database = get_database()
    updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "sellerDetails" in updates and updates["sellerDetails"]:
        updates["sellerDetails"] = data.sellerDetails.model_dump()
    if "address" in updates and updates["address"]:
        updates["address"] = ShippingAddressSchema(**updates["address"]).model_dump()
    updates["updatedAt"] = utc_now()
    await database[C.USERS].update_one({"_id": oid(user["id"])}, {"$set": updates})
    updated = await database[C.USERS].find_one({"_id": oid(user["id"])})
    return serialize_doc(updated)
