import razorpay

from app.config.settings import get_settings


def get_razorpay_client() -> razorpay.Client:
    settings = get_settings()
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


def create_razorpay_order(amount_paise: int, receipt: str, notes: dict | None = None) -> dict:
    client = get_razorpay_client()
    data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
    }
    if notes:
        data["notes"] = notes
    return client.order.create(data=data)


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
