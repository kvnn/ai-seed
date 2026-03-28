"""AWS S3 storage backend."""

import io
import zipfile
from typing import List, Optional

from backend.storage import StorageBackend

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None
    ClientError = Exception


# Map file extensions to content types
CONTENT_TYPE_MAP = {
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".txt": "text/plain",
    ".xml": "application/xml",
    ".md": "text/markdown",
}


def get_content_type(key: str) -> str:
    """Get content type based on file extension."""
    for ext, content_type in CONTENT_TYPE_MAP.items():
        if key.lower().endswith(ext):
            return content_type
    return "application/octet-stream"


class S3Storage(StorageBackend):
    """AWS S3 storage backend.

    Stores files in an S3 bucket with the same key structure.
    Uses presigned URLs for serving files.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        presigned_url_expiry: int = 3600,
    ):
        """Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            region: AWS region
            access_key_id: AWS access key ID (optional, uses default credentials if not provided)
            secret_access_key: AWS secret access key (optional)
            presigned_url_expiry: Default expiry time for presigned URLs in seconds
        """
        if boto3 is None:
            raise RuntimeError("boto3 is required to use backend.services.storage.s3")

        self._bucket = bucket
        self._region = region
        self._presigned_url_expiry = presigned_url_expiry

        # Create S3 client
        client_kwargs = {"region_name": region}
        if access_key_id and secret_access_key:
            client_kwargs["aws_access_key_id"] = access_key_id
            client_kwargs["aws_secret_access_key"] = secret_access_key

        self._s3 = boto3.client("s3", **client_kwargs)

    def write_file(self, key: str, content: str, content_type: str = "text/plain") -> None:
        """Write a text file to S3."""
        # Auto-detect content type if not specified
        if content_type == "text/plain":
            content_type = get_content_type(key)

        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType=content_type,
        )

    def read_file(self, key: str) -> str:
        """Read a text file from S3."""
        try:
            response = self._s3.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found: {key}")
            raise

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def list_files(self, prefix: str) -> List[str]:
        """List all files under a prefix in S3."""
        files = []
        paginator = self._s3.get_paginator("list_objects_v2")

        # Ensure prefix ends with / for proper directory listing
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"

        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                files.append(obj["Key"])

        return files

    def delete_file(self, key: str) -> None:
        """Delete a file from S3."""
        self._s3.delete_object(Bucket=self._bucket, Key=key)

    def get_presigned_url(self, key: str, expiry: int = 3600, filename: Optional[str] = None) -> str:
        """Get a presigned URL for accessing the file.

        Args:
            key: The S3 object key
            expiry: URL expiry time in seconds
            filename: Optional filename for Content-Disposition header (triggers download)

        Returns:
            Presigned URL for the object
        """
        params = {
            "Bucket": self._bucket,
            "Key": key,
        }

        # Add Content-Disposition for downloads
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'

        return self._s3.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiry or self._presigned_url_expiry,
        )

    def create_zip_from_prefix(self, prefix: str) -> bytes:
        """Create a zip file from all files under a prefix in S3."""
        files = self.list_files(prefix)
        if not files:
            raise FileNotFoundError(f"No files found under: {prefix}")

        # Normalize prefix for relative path calculation
        if not prefix.endswith("/"):
            prefix = prefix + "/"

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for key in files:
                # Skip directories (keys ending with /)
                if key.endswith("/"):
                    continue

                # Get file content from S3
                response = self._s3.get_object(Bucket=self._bucket, Key=key)
                content = response["Body"].read()

                # Calculate archive name (relative to prefix)
                arcname = key[len(prefix):]
                if arcname:  # Only add non-empty paths
                    zf.writestr(arcname, content)

        buffer.seek(0)
        return buffer.getvalue()

    @property
    def is_remote(self) -> bool:
        """S3 storage is remote."""
        return True

    @property
    def bucket(self) -> str:
        """Get the bucket name."""
        return self._bucket

    def get_public_url(self, key: str) -> str:
        """Get the direct public URL for a file.

        Use this for files that are publicly readable via bucket policy.
        """
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"
