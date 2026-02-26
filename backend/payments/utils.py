# payments/utils.py
import base64, hashlib, hmac, json

def esewa_make_signature(secret_key: str, total_amount: str, transaction_uuid: str, product_code: str) -> str:
    msg = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    digest = hmac.new(secret_key.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()

def esewa_make_signature_from_signed_fields(secret_key: str, payload: dict) -> str:
    signed = payload.get("signed_field_names", "")
    fields = [f.strip() for f in signed.split(",") if f.strip()]
    msg = ",".join([f"{name}={payload.get(name)}" for name in fields])
    digest = hmac.new(secret_key.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()

def b64_to_json(b64_str: str) -> dict:
    raw = base64.b64decode(b64_str).decode("utf-8")
    return json.loads(raw)
