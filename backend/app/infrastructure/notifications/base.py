import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


SAFE_PROVIDER_RESPONSE_KEYS = ("status", "code", "provider_id", "delivery_status")
SAFE_PROVIDER_ERROR = "Bildirim sağlayıcısı isteği tamamlayamadı"
SAFE_PROVIDER_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _safe_opaque_id(value):
    return (isinstance(value, str) and SAFE_PROVIDER_ID.fullmatch(value)
        and (not value.isdigit() or len(value) <= 8))


def safe_provider_response(response):
    """Return bounded delivery metadata, excluding arbitrary provider payloads."""
    if not isinstance(response, dict):
        return None
    safe = {}
    for key in SAFE_PROVIDER_RESPONSE_KEYS:
        value = response.get(key)
        if key == "status" and isinstance(value, int) and not isinstance(value, bool) and 100 <= value <= 599:
            safe[key] = value
        elif key == "delivery_status" and isinstance(value, str) and value in {"ACCEPTED", "REJECTED", "PENDING", "DELIVERED", "FAILED"}:
            safe[key] = value
        elif (key == "code" and isinstance(value, str) and SAFE_PROVIDER_ID.fullmatch(value)
            and (not value.isdigit() or len(value) <= 6)):
            safe[key] = value
        elif key == "provider_id" and _safe_opaque_id(value):
            safe[key] = value
    messages = response.get("messages")
    if isinstance(messages, list):
        message_ids = [item["id"] for item in messages[:20]
            if isinstance(item, dict) and _safe_opaque_id(item.get("id"))]
        if message_ids:
            safe["provider_message_ids"] = message_ids
    return safe or None


def safe_provider_error(error):
    return SAFE_PROVIDER_ERROR if error else None


@dataclass
class ProviderResult:
    success: bool
    message: str
    response: dict | None = None


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, recipient: str, subject: str | None, body: str) -> ProviderResult:
        pass
