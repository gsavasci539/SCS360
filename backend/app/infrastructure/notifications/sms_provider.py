import httpx

from app.core.config import get_settings
from app.infrastructure.notifications.base import NotificationProvider, ProviderResult

settings = get_settings()


class NetgsmSmsProvider(NotificationProvider):
    async def send(self, recipient: str, subject: str | None, body: str) -> ProviderResult:
        try:
            if settings.APP_ENV in ("development", "test"):
                return ProviderResult(success=True, message="SMS queued (dev mode)", response={"to": recipient})
            async with httpx.AsyncClient() as client:
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
            success = response.status_code == 200
            return ProviderResult(success=success, message=response.text, response={"status": response.status_code})
        except Exception as e:
            return ProviderResult(success=False, message=str(e))
