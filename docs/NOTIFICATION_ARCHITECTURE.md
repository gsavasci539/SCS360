# Notification Architecture

## Overview

The notification system is designed to be provider-independent, reliable, and scalable using the Outbox Pattern. It supports multiple channels (Email, SMS, WhatsApp) with automatic retry mechanisms and comprehensive logging.

---

## Architecture Principles

1. **Provider Independence:** System is not coupled to specific notification providers
2. **Reliability:** Outbox pattern ensures notifications are never lost
3. **Scalability:** Background worker processes notifications asynchronously
4. **Observability:** Comprehensive logging and status tracking
5. **Flexibility:** Easy to add new notification channels and providers

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Payment      │  │ Announcement │  │ Debt Reminder│          │
│  │ Created      │  │ Sent         │  │ Scheduled    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
│                           │                                       │
│                           ▼                                       │
│                  ┌────────────────┐                               │
│                  │ Notification  │                               │
│                  │ Dispatcher    │                               │
│                  └────────┬───────┘                               │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Database Layer                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              notification_jobs Table                       │   │
│  │  - id, channel, recipient_type, recipient_id             │   │
│  │  - subject, body, status, scheduled_for                   │   │
│  │  - sent_at, failed_at, error_message, retry_count         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Background Worker                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Outbox Worker Process                        │   │
│  │  - Polls for PENDING jobs                                │   │
│  │  - Processes by scheduled_for timestamp                   │   │
│  │  - Routes to appropriate provider                         │   │
│  │  - Updates job status                                     │   │
│  │  - Handles retries                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│   Email Provider │ │ SMS Provider│ │WhatsApp      │
│   (SMTP)         │ │ (Netgsm/    │ │Provider      │
│                  │ │ Twilio)     │ │(Meta API)    │
└──────────────────┘ └──────────────┘ └──────────────┘
```

---

## Component Design

### 1. Base Notification Provider

**File:** `backend/app/infrastructure/notifications/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class NotificationProvider(ABC):
    """Abstract base class for notification providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send notification
        
        Args:
            recipient: Recipient address/number
            subject: Message subject (for email)
            body: Message body
            **kwargs: Provider-specific parameters
        
        Returns:
            Dict containing provider response
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name for logging"""
        pass
```

### 2. Email Provider

**File:** `backend/app/infrastructure/notifications/email_provider.py`

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from .base import NotificationProvider

class EmailProvider(NotificationProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get("smtp_host")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_user = config.get("smtp_user")
        self.smtp_password = config.get("smtp_password")
        self.from_email = config.get("from_email")
        self.from_name = config.get("from_name")
    
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = recipient
            
            # Add body
            text_part = MIMEText(body, "plain")
            message.attach(text_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            
            return {
                "success": True,
                "provider_response": "Email sent successfully",
                "message_id": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider_response": None
            }
    
    def validate_config(self) -> bool:
        return all([
            self.smtp_host,
            self.smtp_port,
            self.smtp_user,
            self.smtp_password,
            self.from_email
        ])
    
    def get_provider_name(self) -> str:
        return "Email (SMTP)"
```

### 3. SMS Provider

**File:** `backend/app/infrastructure/notifications/sms_provider.py`

```python
import httpx
from typing import Dict, Any
from .base import NotificationProvider

class SMSProvider(NotificationProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.header = config.get("header", "SCHOOL")
    
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    data={
                        "usercode": self.username,
                        "password": self.password,
                        "gsmno": recipient,
                        "message": body,
                        "msgheader": self.header
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider_response": response.text,
                        "message_id": response.json().get("message_id")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "provider_response": response.text
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider_response": None
            }
    
    def validate_config(self) -> bool:
        return all([self.api_url, self.username, self.password])
    
    def get_provider_name(self) -> str:
        return "SMS"
```

### 4. WhatsApp Provider

**File:** `backend/app/infrastructure/notifications/whatsapp_provider.py`

```python
import httpx
from typing import Dict, Any
from .base import NotificationProvider

class WhatsAppProvider(NotificationProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url")
        self.access_token = config.get("access_token")
        self.phone_number_id = config.get("phone_number_id")
    
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        try:
            # Format phone number
            phone_number = recipient.replace("+", "")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": phone_number,
                        "type": "text",
                        "text": {"body": body}
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider_response": response.json(),
                        "message_id": response.json().get("messages", [{}])[0].get("id")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "provider_response": response.text
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider_response": None
            }
    
    def validate_config(self) -> bool:
        return all([self.api_url, self.access_token, self.phone_number_id])
    
    def get_provider_name(self) -> str:
        return "WhatsApp (Meta)"
```

### 5. Notification Dispatcher

**File:** `backend/app/infrastructure/notifications/dispatcher.py`

```python
from typing import Dict, Any
from enum import Enum
from .email_provider import EmailProvider
from .sms_provider import SMSProvider
from .whatsapp_provider import WhatsAppProvider

class NotificationChannel(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"

class NotificationDispatcher:
    def __init__(self):
        self.providers: Dict[NotificationChannel, NotificationProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize notification providers from configuration"""
        # Email provider
        email_config = self._get_provider_config("smtp")
        if email_config:
            self.providers[NotificationChannel.EMAIL] = EmailProvider(email_config)
        
        # SMS provider
        sms_config = self._get_provider_config("sms")
        if sms_config:
            self.providers[NotificationChannel.SMS] = SMSProvider(sms_config)
        
        # WhatsApp provider
        whatsapp_config = self._get_provider_config("whatsapp")
        if whatsapp_config:
            self.providers[NotificationChannel.WHATSAPP] = WhatsAppProvider(whatsapp_config)
    
    def _get_provider_config(self, provider_type: str) -> Dict[str, Any]:
        """Get provider configuration from database or environment"""
        # Implementation: Fetch from integration_settings table
        pass
    
    async def dispatch_notification(
        self,
        channel: NotificationChannel,
        recipient: str,
        subject: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Dispatch notification to appropriate provider
        
        Args:
            channel: Notification channel
            recipient: Recipient address/number
            subject: Message subject
            body: Message body
            **kwargs: Provider-specific parameters
        
        Returns:
            Dict containing send result
        """
        provider = self.providers.get(channel)
        
        if not provider:
            return {
                "success": False,
                "error": f"Provider not configured for channel: {channel.value}"
            }
        
        if not provider.validate_config():
            return {
                "success": False,
                "error": f"Provider configuration invalid for: {provider.get_provider_name()}"
            }
        
        return await provider.send(recipient, subject, body, **kwargs)
```

### 6. Outbox Worker

**File:** `backend/app/infrastructure/notifications/outbox_worker.py`

```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.infrastructure.notifications.dispatcher import NotificationDispatcher, NotificationChannel
from app.models.notification import NotificationJob

class OutboxWorker:
    def __init__(self, poll_interval: int = 60):
        self.dispatcher = NotificationDispatcher()
        self.poll_interval = poll_interval
        self.running = False
    
    async def start(self):
        """Start the outbox worker"""
        self.running = True
        print("Outbox worker started")
        
        while self.running:
            try:
                await self.process_pending_jobs()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                print(f"Error in outbox worker: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """Stop the outbox worker"""
        self.running = False
        print("Outbox worker stopped")
    
    async def process_pending_jobs(self):
        """Process pending notification jobs"""
        db: Session = next(get_db())
        
        try:
            # Get pending jobs that are due
            now = datetime.utcnow()
            pending_jobs = db.query(NotificationJob).filter(
                NotificationJob.status == "PENDING",
                NotificationJob.scheduled_for <= now,
                NotificationJob.retry_count < NotificationJob.max_retries
            ).limit(100).all()
            
            for job in pending_jobs:
                await self.process_job(job, db)
            
            db.commit()
        finally:
            db.close()
    
    async def process_job(self, job: NotificationJob, db: Session):
        """Process a single notification job"""
        try:
            # Dispatch notification
            channel = NotificationChannel(job.channel)
            result = await self.dispatcher.dispatch_notification(
                channel=channel,
                recipient=job.recipient_id,
                subject=job.subject,
                body=job.body
            )
            
            if result["success"]:
                # Update job status to SENT
                job.status = "SENT"
                job.sent_at = datetime.utcnow()
                job.provider_response = str(result.get("provider_response"))
            else:
                # Update job status to FAILED
                job.status = "FAILED"
                job.failed_at = datetime.utcnow()
                job.error_message = result.get("error")
                job.provider_response = str(result.get("provider_response"))
                job.retry_count += 1
                
                # If max retries not reached, reset to PENDING for retry
                if job.retry_count < job.max_retries:
                    job.status = "PENDING"
                    # Exponential backoff: 2^retry_count minutes
                    job.scheduled_for = datetime.utcnow() + timedelta(minutes=2 ** job.retry_count)
        
        except Exception as e:
            # Handle unexpected errors
            job.status = "FAILED"
            job.failed_at = datetime.utcnow()
            job.error_message = str(e)
            job.retry_count += 1
            
            if job.retry_count < job.max_retries:
                job.status = "PENDING"
                job.scheduled_for = datetime.utcnow() + timedelta(minutes=2 ** job.retry_count)

# Worker entry point
async def main():
    worker = OutboxWorker(poll_interval=30)
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 7. Template Renderer

**File:** `backend/app/infrastructure/notifications/template_renderer.py`

```python
from typing import Dict, Any
from string import Template

class TemplateRenderer:
    def __init__(self):
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from database"""
        # Implementation: Fetch from message_templates table
        pass
    
    def render(
        self,
        template_name: str,
        channel: str,
        variables: Dict[str, Any]
    ) -> tuple:
        """
        Render template with variables
        
        Args:
            template_name: Name of the template
            channel: Notification channel (EMAIL, SMS, WHATSAPP)
            variables: Dictionary of variables to substitute
        
        Returns:
            Tuple of (subject, body)
        """
        template_key = f"{template_name}_{channel}"
        template = self.templates.get(template_key)
        
        if not template:
            raise ValueError(f"Template not found: {template_key}")
        
        # Render subject
        subject = Template(template["subject"]).safe_substitute(**variables)
        
        # Render body
        body = Template(template["body"]).safe_substitute(**variables)
        
        return subject, body
    
    def get_template(self, template_name: str, channel: str) -> Dict[str, str]:
        """Get template without rendering"""
        template_key = f"{template_name}_{channel}"
        return self.templates.get(template_key)
```

---

## Outbox Pattern Implementation

### Database Schema

**notification_jobs Table:**
```sql
CREATE TABLE notification_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    channel notification_channel NOT NULL,
    recipient_type VARCHAR(50) NOT NULL,
    recipient_id UUID NOT NULL,
    subject VARCHAR(255),
    body TEXT NOT NULL,
    status notification_status DEFAULT 'PENDING',
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    provider_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Transactional Outbox

**Example: Payment Notification**

```python
from sqlalchemy.orm import Session
from app.models.payment import Payment
from app.models.notification import NotificationJob
from app.infrastructure.notifications.dispatcher import NotificationChannel

def create_payment_with_notification(
    payment_data: PaymentCreate,
    db: Session
) -> Payment:
    """Create payment and notification in single transaction"""
    
    # Create payment
    payment = Payment(**payment_data.dict())
    db.add(payment)
    db.flush()  # Get payment ID without committing
    
    # Create notification job (outbox)
    notification_job = NotificationJob(
        organization_id=payment.organization_id,
        channel=NotificationChannel.EMAIL.value,
        recipient_type="parent",
        recipient_id=payment.student.parent_id,
        subject="Payment Received",
        body=f"Payment of {payment.amount} received for {payment.student.name}",
        status="PENDING",
        scheduled_for=datetime.utcnow()
    )
    db.add(notification_job)
    
    # Commit transaction (both payment and notification)
    db.commit()
    
    return payment
```

---

## Notification Scenarios

### 1. Payment Received

**Trigger:** Payment created successfully

**Channels:**
- Email: Payment receipt to parent
- SMS: Optional payment confirmation
- WhatsApp: Optional payment notification

**Template Variables:**
```python
{
    "student_name": "Ahmet Yılmaz",
    "payment_amount": "5,000.00 TL",
    "payment_date": "2024-01-15",
    "receipt_number": "RCP-20240115-000001",
    "remaining_debt": "2,000.00 TL"
}
```

### 2. Announcement Sent

**Trigger:** Announcement created and sent

**Channels:**
- Email: Full announcement with formatting
- SMS: Short summary with link
- WhatsApp: Message with link to full announcement

**Template Variables:**
```python
{
    "announcement_title": "Kış Tatili Duyurusu",
    "announcement_content": "...",
    "school_name": "Demo Eğitim Kurumu",
    "announcement_date": "2024-01-15"
}
```

### 3. Debt Reminder

**Trigger:** Scheduled job checks for overdue debts

**Channels:**
- Email: Detailed debt information
- SMS: Short reminder
- WhatsApp: Reminder with payment link

**Template Variables:**
```python
{
    "parent_name": "Ali Yılmaz",
    "student_name": "Ahmet Yılmaz",
    "debt_amount": "2,000.00 TL",
    "due_date": "2024-01-20",
    "days_overdue": "5"
}
```

### 4. Password Reset

**Trigger:** User requests password reset

**Channels:**
- Email: Password reset link only

**Template Variables:**
```python
{
    "user_name": "Ahmet Yılmaz",
    "reset_link": "https://app.schoolmanagement.com/reset-password/token123",
    "expiry_hours": "1"
}
```

---

## Retry Strategy

### Exponential Backoff

**Algorithm:**
```
Retry delay = 2^retry_count minutes

Retry 1: 2^1 = 2 minutes
Retry 2: 2^2 = 4 minutes
Retry 3: 2^3 = 8 minutes
```

**Configuration:**
- Max retries: 3 (configurable)
- Initial delay: 2 minutes
- Max delay: 1 hour

### Failure Handling

**Permanent Failure:**
- Max retries exceeded
- Provider returns permanent error (e.g., invalid recipient)
- Job marked as FAILED permanently

**Temporary Failure:**
- Network timeout
- Provider rate limit
- Temporary provider outage
- Job rescheduled with exponential backoff

---

## Monitoring and Observability

### Metrics to Track

**Per Channel:**
- Total jobs created
- Total jobs sent successfully
- Total jobs failed
- Average delivery time
- Retry rate

**Per Provider:**
- Provider response time
- Provider error rate
- Provider availability

### Logging

**Log Events:**
- Job created
- Job dispatched
- Job sent successfully
- Job failed
- Retry scheduled
- Provider error

**Log Format:**
```python
{
    "timestamp": "2024-01-15T10:30:00Z",
    "event": "notification_sent",
    "job_id": "uuid",
    "channel": "EMAIL",
    "recipient": "parent@example.com",
    "provider": "Email (SMTP)",
    "duration_ms": 1234,
    "success": true
}
```

### Alerts

**Alert Conditions:**
- Failure rate > 10% for 5 minutes
- Queue size > 1000 jobs
- Provider unavailable for > 5 minutes
- Average delivery time > 30 seconds

---

## Security Considerations

### Data Protection

- Never log sensitive data (passwords, full credit card numbers)
- Encrypt notification content at rest
- Use TLS for all provider communications
- Validate recipient addresses before sending

### Rate Limiting

- Per-recipient rate limiting (prevent spam)
- Per-channel rate limiting (provider limits)
- Global rate limiting (system protection)

### Access Control

- Only authorized users can send notifications
- Audit log of all notification sends
- Role-based notification permissions

---

## Configuration

### Environment Variables

```bash
# Email (SMTP)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=secure_password
SMTP_FROM_EMAIL=noreply@example.com
SMTP_FROM_NAME=School Management

# SMS (Netgsm)
SMS_API_URL=https://api.netgsm.com
SMS_USERNAME=username
SMS_PASSWORD=password
SMS_HEADER=SCHOOL

# WhatsApp (Meta)
WHATSAPP_API_URL=https://graph.facebook.com
WHATSAPP_ACCESS_TOKEN=access_token
WHATSAPP_PHONE_NUMBER_ID=phone_number_id

# Worker Settings
NOTIFICATION_WORKER_POLL_INTERVAL=30
NOTIFICATION_MAX_RETRIES=3
```

### Database Configuration

Provider settings stored in `integration_settings` table:
```json
{
  "integration_type": "smtp",
  "provider_name": "default",
  "settings": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "notifications@example.com",
    "smtp_password": "encrypted_password",
    "from_email": "noreply@example.com",
    "from_name": "School Management"
  },
  "is_active": true
}
```

---

## Testing

### Unit Tests

```python
import pytest
from app.infrastructure.notifications.email_provider import EmailProvider

def test_email_provider_send():
    config = {
        "smtp_host": "localhost",
        "smtp_port": 1025,  # Test SMTP server
        "smtp_user": "test",
        "smtp_password": "test",
        "from_email": "test@example.com",
        "from_name": "Test"
    }
    provider = EmailProvider(config)
    
    result = await provider.send(
        recipient="recipient@example.com",
        subject="Test Subject",
        body="Test Body"
    )
    
    assert result["success"] is True
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_notification_flow():
    # Create notification job
    job = create_notification_job(...)
    
    # Process job
    await worker.process_job(job, db)
    
    # Verify job status
    assert job.status == "SENT"
    assert job.sent_at is not None
```

---

## Future Enhancements

### Planned Features

1. **Webhook Support:** Allow external systems to send notifications
2. **Template Editor:** UI for creating and editing templates
3. **Notification Preferences:** User-level notification preferences
4. **Bulk Sending:** Optimized bulk notification sending
5. **Analytics Dashboard:** Visualization of notification metrics
6. **Multi-language Support:** Templates in multiple languages
7. **Attachment Support:** Send attachments with emails
8. **Scheduled Notifications:** Advanced scheduling options
