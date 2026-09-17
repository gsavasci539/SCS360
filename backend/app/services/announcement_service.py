from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import AnnouncementRepository
from app.domain.entities.announcement import Announcement
from app.domain.entities.announcement_recipient import AnnouncementRecipient
from app.core.exceptions import AppException


class AnnouncementService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.announcement_repo = AnnouncementRepository()

    async def create_announcement(
        self,
        organization_id: UUID,
        title: str,
        content: str,
        audience: str,
        channels: str,
        recipient_ids: Optional[List[dict]] = None,
        **kwargs
    ) -> Announcement:
        announcement_data = {
            "organization_id": organization_id,
            "title": title,
            "content": content,
            "audience": audience,
            "channels": channels,
            **kwargs
        }
        
        announcement = await self.announcement_repo.create(self.db, announcement_data)
        
        # Create recipients
        if recipient_ids:
            for recipient in recipient_ids:
                recipient_data = {
                    "announcement_id": announcement.id,
                    "recipient_type": recipient["type"],
                    "recipient_id": recipient["id"],
                    "channel": recipient.get("channel", "email")
                }
                announcement_recipient = AnnouncementRecipient(**recipient_data)
                self.db.add(announcement_recipient)
            await self.db.flush()
        
        return announcement

    async def send_announcement(self, announcement_id: UUID) -> dict:
        announcement = await self.announcement_repo.get(self.db, announcement_id)
        if not announcement:
            raise AppException("Duyuru bulunamadı", status_code=404)
        
        if announcement.status == "sent":
            raise AppException("Duyuru zaten gönderilmiş", status_code=400)
        
        # TODO: Send notification jobs for each recipient
        # TODO: Update announcement status to sent
        
        return {"message": "Duyuru gönderildi"}

    async def update_announcement(
        self,
        announcement_id: UUID,
        **kwargs
    ) -> Announcement:
        announcement = await self.announcement_repo.get(self.db, announcement_id)
        if not announcement:
            raise AppException("Duyuru bulunamadı", status_code=404)
        
        return await self.announcement_repo.update(self.db, announcement, kwargs)
