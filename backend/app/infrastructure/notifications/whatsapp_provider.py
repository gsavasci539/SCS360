import httpx

from app.core.config import get_settings
from app.infrastructure.notifications.base import NotificationProvider, ProviderResult

settings = get_settings()


class MetaWhatsAppProvider(NotificationProvider):
    async def send(self, recipient: str, subject: str | None, body: str) -> ProviderResult:
        try:
            if not settings.NOTIFICATION_DELIVERY_ENABLED:
                return ProviderResult(success=False, message="Bildirim gönderimi yapılandırmada kapalı")
            if not all([settings.WHATSAPP_API_URL, settings.WHATSAPP_ACCESS_TOKEN, settings.WHATSAPP_PHONE_NUMBER_ID]):
                return ProviderResult(success=False, message="WhatsApp sağlayıcısı yapılandırılmamış")
            url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
            headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": body},
            }
            async with httpx.AsyncClient(timeout=settings.NOTIFICATION_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
            success = response.status_code in (200, 201) and bool(response.json().get("messages"))
            return ProviderResult(success=success, message=response.text, response=response.json() if success else None)
        except Exception:
            return ProviderResult(success=False, message="WhatsApp sağlayıcısı gönderimi tamamlayamadı")
