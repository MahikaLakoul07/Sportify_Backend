import base64
import hashlib
import hmac
import json


def esewa_make_signature(secret_key, total_amount, transaction_uuid, product_code):
    total_amount = str(total_amount).strip()
    transaction_uuid = str(transaction_uuid).strip()
    product_code = str(product_code).strip()
    secret_key = str(secret_key).strip()

    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"

    digest = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(digest).decode("utf-8").strip()


def esewa_make_signature_from_signed_fields(secret_key, payload):
    secret_key = str(secret_key).strip()
    signed_fields = str(payload.get("signed_field_names", "")).strip()
    fields = [f.strip() for f in signed_fields.split(",") if f.strip()]

    message = ",".join(
        f"{name}={str(payload.get(name, '')).strip()}" for name in fields
    )

    digest = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(digest).decode("utf-8").strip()


def b64_to_json(b64_str):
    decoded = base64.b64decode(b64_str).decode("utf-8")
    return json.loads(decoded)