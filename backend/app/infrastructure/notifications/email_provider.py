import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.infrastructure.notifications.base import NotificationProvider, ProviderResult

settings = get_settings()


class SmtpEmailProvider(NotificationProvider):
    async def send(self, recipient: str, subject: str | None, body: str) -> ProviderResult:
        try:
            if settings.APP_ENV in ("development", "test"):
                return ProviderResult(success=True, message="Email queued (dev mode)", response={"to": recipient})
            msg = MIMEMultipart()
            msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg["To"] = recipient
            msg["Subject"] = subject or "EduPanel Bildirimi"
            msg.attach(MIMEText(body, "plain", "utf-8"))
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            return ProviderResult(success=True, message="Email sent")
        except Exception as e:
            return ProviderResult(success=False, message=str(e))
