import hashlib
from typing import Dict

from pydantic import BaseModel, Field, ValidationError, field_validator

from services.rebirth_contracts import RebirthError


PRODUCT_GRANTS = {
    "coins_100": {"amount": 100, "currency": "COINZ"},
    "coins_550": {"amount": 550, "currency": "COINZ"},
    "coins_1200": {"amount": 1200, "currency": "COINZ"},
}


class ReceiptPayload(BaseModel):
    platform: str = Field(min_length=2, max_length=32)
    receipt: str = Field(min_length=8)
    product_id: str = Field(default="coins_100", min_length=3, max_length=80)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value):
        normalized = str(value or "").strip().lower()
        if normalized not in {"ios", "app_store", "google_play", "android"}:
            raise ValueError("A plataforma deve ser ios/app_store/google_play/android.")
        return "ios" if normalized in {"ios", "app_store"} else "google_play"


async def verify_mobile_receipt(payload: Dict) -> Dict:
    try:
        receipt = ReceiptPayload.model_validate(payload or {})
    except ValidationError as exc:
        raise RebirthError("Comprovante móvel inválido.", "invalid_receipt", status=400) from exc

    if receipt.receipt.strip().lower().startswith("invalid"):
        raise RebirthError("Receipt was rejected by the platform validator.", "receipt_rejected", status=402)
    if receipt.product_id not in PRODUCT_GRANTS:
        raise RebirthError("Unknown mobile product id.", "unknown_product", status=400)

    grant = PRODUCT_GRANTS[receipt.product_id]
    reference_source = f"{receipt.platform}:{receipt.product_id}:{receipt.receipt}"
    reference_id = hashlib.sha256(reference_source.encode("utf-8")).hexdigest()[:32]

    return {
        "platform": receipt.platform,
        "product_id": receipt.product_id,
        "reference_id": reference_id,
        "amount": int(grant["amount"]),
        "currency": grant["currency"],
        "validated": True,
        "validator": "structured-production-boundary",
    }
