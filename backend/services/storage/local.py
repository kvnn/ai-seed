"""Local filesystem storage backend."""

import io
import zipfile
from pathlib import Path
from typing import List, Optional

from backend.storage import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem storage backend.

    Stores files in a local directory, maintaining the same structure
    as the S3 keys.
    """

    def __init__(self, base_dir: str):
        """Initialize local storage.

        Args:
            base_dir: Base directory for file storage (e.g., "./data")
        """
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get the full filesystem path for a storage key."""
        return self._base_dir / key

    def write_file(self, key: str, content: str, content_type: str = "text/plain") -> None:
        """Write a text file to local storage."""
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_file(self, key: str) -> str:
        """Read a text file from local storage."""
        path = self._get_path(key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return path.read_text(encoding="utf-8")

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in local storage."""
        return self._get_path(key).exists()

    def list_files(self, prefix: str) -> List[str]:
        """List all files under a prefix in local storage."""
        prefix_path = self._get_path(prefix)
        if not prefix_path.exists():
            return []

        files = []
        for path in prefix_path.rglob("*"):
            if path.is_file():
                # Return the key relative to base_dir
                files.append(str(path.relative_to(self._base_dir)))
        return files

    def delete_file(self, key: str) -> None:
        """Delete a file from local storage."""
        path = self._get_path(key)
        if path.exists():
            path.unlink()

    def get_presigned_url(self, key: str, expiry: int = 3600, filename: Optional[str] = None) -> str:
        """Get the local file path.

        For local storage, this just returns the absolute path.
        The API layer will handle serving the file directly.
        """
        path = self._get_path(key)
        return str(path.resolve())

    def create_zip_from_prefix(self, prefix: str) -> bytes:
        """Create a zip file from all files under a prefix."""
        prefix_path = self._get_path(prefix)
        if not prefix_path.exists():
            raise FileNotFoundError(f"Directory not found: {prefix}")

        files = list(prefix_path.rglob("*"))
        if not any(f.is_file() for f in files):
            raise FileNotFoundError(f"No files found under: {prefix}")

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                if path.is_file():
                    # Use path relative to prefix for archive name
                    arcname = str(path.relative_to(prefix_path))
                    zf.write(path, arcname)

        buffer.seek(0)
        return buffer.getvalue()

    def get_public_url(self, key: str) -> str:
        """Get the local file path (local storage has no public URL)."""
        path = self._get_path(key)
        return str(path.resolve())

    @property
    def is_remote(self) -> bool:
        """Local storage is not remote."""
        return False

    @property
    def base_dir(self) -> Path:
        """Get the base directory."""
        return self._base_dir
