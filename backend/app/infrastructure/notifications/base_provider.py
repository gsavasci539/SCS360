from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseNotificationProvider(ABC):
    """Base class for notification providers"""
    
    @abstractmethod
    async def send(self, recipient: str, subject: str, body: str, **kwargs) -> Dict[str, Any]:
        """
        Send notification
        
        Args:
            recipient: Recipient address (email, phone, etc.)
            subject: Subject of the notification
            body: Body content of the notification
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dict containing success status, provider response, etc.
        """
        pass
    
    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """
        Validate recipient address format
        
        Args:
            recipient: Recipient address
            
        Returns:
            True if valid, False otherwise
        """
        pass
