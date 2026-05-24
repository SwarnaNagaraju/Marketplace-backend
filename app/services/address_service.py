from app.core.exceptions import bad_request, not_found
from app.database import get_database
from app.models import collections as C
from app.schemas.address import ShippingAddressSchema
from app.utils.helpers import oid, serialize_doc, utc_now


class AddressService:
    @staticmethod
    def _is_complete(address: dict | None) -> bool:
        if not address:
            return False
        required = ("fullName", "phone", "street", "city", "state", "pincode")
        return all(address.get(k) for k in required)

    @staticmethod
    async def get_shipping_address(user_id: str) -> dict | None:
        database = get_database()
        user = await database[C.USERS].find_one({"_id": oid(user_id)})
        if not user:
            raise not_found("User not found")
        addr = user.get("address")
        if not AddressService._is_complete(addr):
            return None
        return addr

    @staticmethod
    async def save_shipping_address(user_id: str, data: ShippingAddressSchema) -> dict:
        database = get_database()
        address = data.model_dump()
        await database[C.USERS].update_one(
            {"_id": oid(user_id)},
            {"$set": {"address": address, "updatedAt": utc_now()}},
        )
        user = await database[C.USERS].find_one({"_id": oid(user_id)})
        return serialize_doc(user)

    @staticmethod
    async def resolve_checkout_address(
        user_id: str,
        shipping_address: ShippingAddressSchema | None,
        use_saved: bool,
        save_address: bool,
    ) -> ShippingAddressSchema:
        database = get_database()
        user = await database[C.USERS].find_one({"_id": oid(user_id)})
        if not user:
            raise not_found("User not found")

        if use_saved:
            saved = user.get("address")
            if not AddressService._is_complete(saved):
                raise bad_request(
                    "No saved shipping address. Add one in My Address or enter details below."
                )
            return ShippingAddressSchema(**saved)

        if not shipping_address:
            raise bad_request("Shipping address is required")

        if save_address:
            await database[C.USERS].update_one(
                {"_id": oid(user_id)},
                {
                    "$set": {
                        "address": shipping_address.model_dump(),
                        "updatedAt": utc_now(),
                    }
                },
            )

        return shipping_address
