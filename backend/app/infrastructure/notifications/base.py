from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    success: bool
    message: str
    response: dict | None = None


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, recipient: str, subject: str | None, body: str) -> ProviderResult:
        pass
