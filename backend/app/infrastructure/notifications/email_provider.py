import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.infrastructure.notifications.base import NotificationProvider, ProviderResult

settings = get_settings()


class SmtpEmailProvider(NotificationProvider):
    async def send(self, recipient: str, subject: str | None, body: str) -> ProviderResult:
        try:
            if not settings.NOTIFICATION_DELIVERY_ENABLED:
                return ProviderResult(success=False, message="Bildirim gönderimi yapılandırmada kapalı")
            if not settings.SMTP_HOST or settings.SMTP_HOST == "smtp.example.com" or not settings.SMTP_FROM_EMAIL:
                return ProviderResult(success=False, message="SMTP sunucusu yapılandırılmamış")
            msg = MIMEMultipart()
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = recipient
            msg["Subject"] = subject or "SCS360 Bildirimi"
            msg.attach(MIMEText(body, "plain", "utf-8"))
            def deliver():
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.NOTIFICATION_TIMEOUT_SECONDS) as server:
                    server.starttls(context=ssl.create_default_context())
                    if settings.SMTP_USER:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            await asyncio.to_thread(deliver)
            return ProviderResult(success=True, message="Email sent")
        except Exception:
            return ProviderResult(success=False, message="E-posta sağlayıcısı gönderimi tamamlayamadı")
