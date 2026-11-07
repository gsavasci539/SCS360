import httpx

from app.core.config import get_settings
from app.infrastructure.notifications.base import NotificationProvider, ProviderResult

settings = get_settings()


class NetgsmSmsProvider(NotificationProvider):
    def __init__(self, configuration=None):
        self.configuration = configuration or settings

    async def send(self, recipient: str, subject: str | None, body: str) -> ProviderResult:
        settings = self.configuration
        try:
            if not settings.NOTIFICATION_DELIVERY_ENABLED:
                return ProviderResult(success=False, message="Bildirim gönderimi yapılandırmada kapalı")
            if not all([settings.SMS_API_URL, settings.SMS_USERNAME, settings.SMS_PASSWORD, settings.SMS_HEADER]):
                return ProviderResult(success=False, message="SMS sağlayıcısı yapılandırılmamış")
            async with httpx.AsyncClient(timeout=settings.NOTIFICATION_TIMEOUT_SECONDS) as client:
                if "/sms/rest/v2/send" in settings.SMS_API_URL:
                    response = await client.post(settings.SMS_API_URL,
                        auth=(settings.SMS_USERNAME, settings.SMS_PASSWORD),
                        json={"msgheader": settings.SMS_HEADER, "messages": [{"msg": body, "no": recipient}], "encoding": "TR"})
                    result = response.json()
                    success = response.status_code == 200 and result.get("code") == "00" and bool(result.get("jobid"))
                    return ProviderResult(success=success, message="SMS sağlayıcısına iletildi" if success else "SMS sağlayıcısı isteği reddetti",
                        response={"code": result.get("code"), "provider_id": result.get("jobid"), "delivery_status": "ACCEPTED" if success else "REJECTED"})
                response = await client.post(
                    settings.SMS_API_URL,
                    data={
                        "usercode": settings.SMS_USERNAME,
                        "password": settings.SMS_PASSWORD,
                        "gsmno": recipient,
                        "message": body,
                        "msgheader": settings.SMS_HEADER,
                    },
                )
            success = response.status_code == 200 and response.text.strip().split()[0:1] == ["00"]
            return ProviderResult(success=success, message=response.text, response={"status": response.status_code})
        except Exception:
            return ProviderResult(success=False, message="SMS sağlayıcısı gönderimi tamamlayamadı")
