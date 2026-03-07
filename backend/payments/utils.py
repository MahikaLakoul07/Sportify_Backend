import base64
import hashlib
import hmac
import json


def esewa_make_signature(secret_key, total_amount, transaction_uuid, product_code):
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"

    digest = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()

    return base64.b64encode(digest).decode()


def esewa_make_signature_from_signed_fields(secret_key, payload):
    signed_fields = payload.get("signed_field_names", "")
    fields = [f.strip() for f in signed_fields.split(",") if f.strip()]

    message = ",".join(
        [f"{name}={payload.get(name)}" for name in fields]
    )

    digest = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()

    return base64.b64encode(digest).decode()


def b64_to_json(b64_str):
    decoded = base64.b64decode(b64_str).decode("utf-8")
    return json.loads(decoded)