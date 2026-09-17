from abc import ABC, abstractmethod


class StorageBase(ABC):
    @abstractmethod
    async def save(self, content: bytes, original_name: str, subfolder: str = "") -> str:
        pass

    @abstractmethod
    def get_full_path(self, storage_path: str) -> str:
        pass
