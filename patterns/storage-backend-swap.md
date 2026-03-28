# Pattern: Swappable Storage Backend

## Problem

You need to store files (generated sites, uploads, assets) somewhere. In development, you want the filesystem. In production, you want S3 (or GCS, or Azure Blob). If your code has `with open(path, 'w')` scattered through it, migrating to cloud storage means rewriting every call site.

## Pattern

Define an **abstract interface** for file storage, then implement it per backend. All application code depends on the interface, never on a concrete backend.

```
┌────────────────────┐
│  StorageBackend    │  ← Abstract base class
│                    │
│  write_file()      │
│  read_file()       │
│  file_exists()     │
│  list_files()      │
│  delete_file()     │
│  get_presigned_url()│
│  create_zip()      │
│  get_public_url()  │
│  is_remote         │
└────────┬───────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ Local │ │  S3   │
│Storage│ │Storage│
└───────┘ └───────┘
```

### The Interface

```python
from abc import ABC, abstractmethod
from typing import List, Optional


class StorageBackend(ABC):
    """Abstract base class for file storage."""

    @abstractmethod
    def write_file(self, key: str, content: str, content_type: str = "text/plain") -> None:
        """Write a text file to storage.

        Args:
            key: Storage path (e.g., "projects/abc123/v1/site/index.html")
            content: File content as string
            content_type: MIME type
        """
        ...

    @abstractmethod
    def read_file(self, key: str) -> str:
        """Read a text file. Raises FileNotFoundError if missing."""
        ...

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        """List all file keys under a prefix."""
        ...

    @abstractmethod
    def delete_file(self, key: str) -> None:
        ...

    @abstractmethod
    def get_presigned_url(self, key: str, expiry: int = 3600,
                          filename: Optional[str] = None) -> str:
        """Get a time-limited URL for file access.

        For S3: presigned URL. For local: file path or localhost URL.
        """
        ...

    @abstractmethod
    def create_zip_from_prefix(self, prefix: str) -> bytes:
        """Create a zip archive of all files under a prefix."""
        ...

    @abstractmethod
    def get_public_url(self, key: str) -> str:
        """Get a permanent public URL for a file."""
        ...

    @property
    @abstractmethod
    def is_remote(self) -> bool:
        """Whether this is a remote backend (affects URL generation logic)."""
        ...
```

**Key decisions:**
- **Key-based, not path-based**: Use forward-slash-separated keys (`"projects/abc/v1/index.html"`), not OS paths. This maps naturally to both S3 keys and filesystem paths.
- **`is_remote` property**: Callers sometimes need to know whether to redirect to a presigned URL or serve the file directly. This flag enables that branch without `isinstance` checks.
- **`create_zip_from_prefix`**: Downloading a collection of files as a zip is a common operation. Putting it on the interface means both backends handle it natively (S3 can stream from the bucket; local reads from disk).
- **`content_type` parameter**: S3 needs this for proper `Content-Type` headers on direct access. Local storage can ignore it or use it for metadata.

### Local Implementation

```python
import io
import os
import zipfile
from pathlib import Path


class LocalStorage(StorageBackend):
    def __init__(self, base_dir: str):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        path = (self._base / key).resolve()
        # Prevent path traversal
        if not str(path).startswith(str(self._base.resolve())):
            raise ValueError(f"Invalid key: {key}")
        return path

    def write_file(self, key: str, content: str, content_type: str = "text/plain") -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_file(self, key: str) -> str:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return path.read_text(encoding="utf-8")

    def file_exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def list_files(self, prefix: str) -> List[str]:
        base = self._resolve(prefix)
        if not base.exists():
            return []
        return [
            str(p.relative_to(self._base)).replace(os.sep, "/")
            for p in base.rglob("*")
            if p.is_file()
        ]

    def delete_file(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    def get_presigned_url(self, key: str, expiry: int = 3600,
                          filename: str | None = None) -> str:
        return f"/files/{key}"

    def create_zip_from_prefix(self, prefix: str) -> bytes:
        files = self.list_files(prefix)
        if not files:
            raise FileNotFoundError(f"No files under: {prefix}")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_key in files:
                rel = file_key[len(prefix):].lstrip("/")
                content = self.read_file(file_key)
                zf.writestr(rel, content)
        return buf.getvalue()

    def get_public_url(self, key: str) -> str:
        return f"/files/{key}"

    @property
    def is_remote(self) -> bool:
        return False
```

### S3 Implementation

```python
import io
import zipfile

import boto3


class S3Storage(StorageBackend):
    def __init__(self, bucket: str, region: str = "us-east-1"):
        self._bucket = bucket
        self._region = region
        self._s3 = boto3.client("s3", region_name=region)

    def _content_type(self, key: str) -> str:
        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
        return {
            "html": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "json": "application/json",
            "svg": "image/svg+xml",
            "png": "image/png",
            "jpg": "image/jpeg",
            "ico": "image/x-icon",
        }.get(ext, "application/octet-stream")

    def write_file(self, key: str, content: str, content_type: str = "text/plain") -> None:
        ct = content_type if content_type != "text/plain" else self._content_type(key)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType=ct,
        )

    def read_file(self, key: str) -> str:
        try:
            obj = self._s3.get_object(Bucket=self._bucket, Key=key)
            return obj["Body"].read().decode("utf-8")
        except self._s3.exceptions.NoSuchKey:
            raise FileNotFoundError(f"File not found: {key}")

    def file_exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    def list_files(self, prefix: str) -> list[str]:
        keys = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys

    def delete_file(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)

    def get_presigned_url(self, key: str, expiry: int = 3600,
                          filename: str | None = None) -> str:
        params = {"Bucket": self._bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return self._s3.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expiry,
        )

    def create_zip_from_prefix(self, prefix: str) -> bytes:
        files = self.list_files(prefix)
        if not files:
            raise FileNotFoundError(f"No files under: {prefix}")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_key in files:
                rel = file_key[len(prefix):].lstrip("/")
                content = self.read_file(file_key)
                zf.writestr(rel, content)
        return buf.getvalue()

    def get_public_url(self, key: str) -> str:
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"

    @property
    def is_remote(self) -> bool:
        return True
```

### Factory

Select the backend from configuration:

```python
def create_storage(config) -> StorageBackend:
    if config.storage_backend == "s3":
        return S3Storage(bucket=config.s3_bucket, region=config.s3_region)
    return LocalStorage(base_dir=config.local_storage_path)
```

### Using It

All application code takes `StorageBackend` as a dependency:

```python
class DeploymentService:
    def __init__(self, storage: StorageBackend):
        self._storage = storage

    async def deploy_version(self, project_id: str, version_id: str, files: list):
        prefix = f"deployments/{project_id}/{version_id}"
        for f in files:
            self._storage.write_file(f"{prefix}/{f.path}", f.content)

    def get_download_url(self, project_id: str, version_id: str) -> str:
        if self._storage.is_remote:
            # Generate a presigned zip URL
            prefix = f"deployments/{project_id}/{version_id}"
            zip_bytes = self._storage.create_zip_from_prefix(prefix)
            # Upload zip and return presigned URL...
        else:
            return f"/api/projects/{project_id}/versions/{version_id}/download"
```

## Path Traversal Prevention

Both implementations must validate that keys don't escape the storage root:

```python
# Local: resolve and check prefix
path = (self._base / key).resolve()
if not str(path).startswith(str(self._base.resolve())):
    raise ValueError(f"Path traversal attempt: {key}")

# S3: keys are flat strings, but still validate
if ".." in key or key.startswith("/"):
    raise ValueError(f"Invalid key: {key}")
```

This is a security boundary. Files come from LLM output, which can contain anything — including `../../etc/passwd` as a filename.

## Pitfalls

1. **Hardcoded `open()` calls**: Every direct filesystem call is a place that breaks when you switch to S3. Grep for `open(` and `Path(` in your codebase and route them through the backend.

2. **Forgetting content types on S3**: If you upload HTML with `application/octet-stream`, browsers download it instead of rendering it. Auto-detect from extension.

3. **No path traversal check**: LLM-generated filenames can contain `../`. Always validate before writing.

4. **Sync S3 calls in async handlers**: `boto3` is synchronous. If you're in a FastAPI async endpoint, wrap S3 calls in `asyncio.to_thread()` or use `aioboto3`.

5. **Listing without pagination**: S3's `list_objects_v2` returns max 1000 keys. Use the paginator.

6. **Presigned URL expiry too short**: If a user clicks "download" and the URL expires before the download finishes (large files, slow connections), they get a cryptic XML error. Default to 1 hour.

## When NOT to Use This Pattern

- **Binary-heavy workloads**: If you're storing images, videos, or large binaries, you'll need `write_bytes`/`read_bytes` methods alongside the text ones. The interface shown here is text-focused.
- **Single deployment target**: If you'll only ever use S3, the abstraction adds indirection for no benefit. Use S3 directly.
- **High-throughput streaming**: For large file uploads/downloads, you need streaming read/write (not load-into-memory). Add `write_stream`/`read_stream` methods.

## Adapting This Pattern

| If you're using... | Replace... |
|---|---|
| Google Cloud Storage | The S3 implementation with `google.cloud.storage`. Same interface. |
| Azure Blob Storage | The S3 implementation with `azure.storage.blob`. Same interface. |
| MinIO (S3-compatible) | Use the S3 implementation as-is. Just change the endpoint URL in the boto3 client. |
| Both text and binary files | Add `write_bytes(key, data: bytes)` and `read_bytes(key) -> bytes` to the interface. |
