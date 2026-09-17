from datetime import datetime, timezone

from app.infrastructure.models.models import NotificationChannel, NotificationStatus
from app.infrastructure.notifications.base import NotificationProvider
from app.infrastructure.notifications.email_provider import SmtpEmailProvider
from app.infrastructure.notifications.sms_provider import NetgsmSmsProvider
from app.infrastructure.notifications.whatsapp_provider import MetaWhatsAppProvider


class NotificationDispatcher:
    def __init__(self):
        self._providers: dict[NotificationChannel, NotificationProvider] = {
            NotificationChannel.EMAIL: SmtpEmailProvider(),
            NotificationChannel.SMS: NetgsmSmsProvider(),
            NotificationChannel.WHATSAPP: MetaWhatsAppProvider(),
        }

    def get_provider(self, channel: NotificationChannel) -> NotificationProvider:
        return self._providers[channel]

    async def dispatch(self, channel: NotificationChannel, recipient: str, subject: str | None, body: str):
        provider = self.get_provider(channel)
        return await provider.send(recipient, subject, body)
