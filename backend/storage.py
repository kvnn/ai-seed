from abc import ABC, abstractmethod
from typing import List, Optional


class StorageBackend(ABC):
    @abstractmethod
    def write_file(self, key: str, content: str, content_type: str = "text/plain") -> None:
        pass

    @abstractmethod
    def read_file(self, key: str) -> str:
        pass

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        pass

    @abstractmethod
    def delete_file(self, key: str) -> None:
        pass

    @abstractmethod
    def get_presigned_url(self, key: str, expiry: int = 3600, filename: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def create_zip_from_prefix(self, prefix: str) -> bytes:
        pass

    @abstractmethod
    def get_public_url(self, key: str) -> str:
        pass

    @property
    @abstractmethod
    def is_remote(self) -> bool:
        pass
