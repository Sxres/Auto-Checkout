"""The S3 layout under a local directory or an S3 bucket, by object key (issue #12).

Kept apart from annotate.py so the capture API (#14) can reuse it with the default
dependencies only: no cv2/numpy/ultralytics here, and boto3 is imported lazily for S3.
"""

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path


class PreconditionFailed(Exception):
    """A conditional write failed its precondition (S3 412, or local if_none_match on an existing key)."""


class Store:
    """The S3 layout under a local directory or an S3 bucket ("s3://bucket"), by object key."""

    def __init__(self, root: str):
        self.bucket = root.removeprefix("s3://").strip("/") if root.startswith("s3://") else None
        if self.bucket:
            import boto3

            # Pin the regional endpoint: generate_presigned_post otherwise builds the URL with the
            # legacy global host (s3.amazonaws.com), which a browser can't POST to for a bucket in
            # another region. Lambda sets AWS_REGION at runtime.
            region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
            kwargs = {"region_name": region}
            if region:
                kwargs["endpoint_url"] = f"https://s3.{region}.amazonaws.com"
            self.s3 = boto3.client("s3", **kwargs)
        else:
            self.dir = Path(root)

    def get(self, key: str) -> bytes:
        if self.bucket:
            return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        return (self.dir / key).read_bytes()

    def get_with_etag(self, key: str) -> tuple[bytes | None, str | None]:
        """(bytes, ETag) for a conditional read; (None, None) if the key is missing. Local has no ETag."""
        if self.bucket:
            from botocore.exceptions import ClientError

            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=key)
            except ClientError as exc:
                if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    return None, None
                raise
            return obj["Body"].read(), obj.get("ETag")
        path = self.dir / key
        if not path.is_file():
            return None, None
        return path.read_bytes(), None

    def put(self, key: str, data: bytes, *, if_match: str | None = None, if_none_match: str | None = None) -> None:
        """Write a key. if_match (S3 ETag) makes it a conditional update; if_none_match="*" creates only
        if absent. A failed precondition raises PreconditionFailed. The local store ignores if_match."""
        if if_none_match not in (None, "*"):
            raise ValueError("if_none_match must be '*' or None")
        if self.bucket:
            from botocore.exceptions import ClientError

            kwargs = {}
            if if_match is not None:
                kwargs["IfMatch"] = if_match
            if if_none_match is not None:
                kwargs["IfNoneMatch"] = if_none_match
            try:
                self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, **kwargs)
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "PreconditionFailed":
                    raise PreconditionFailed(key) from exc
                raise
        else:
            path = self.dir / key
            if if_none_match == "*" and path.exists():
                raise PreconditionFailed(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def keys(self, prefix: str) -> list[str]:
        if self.bucket:
            pages = self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix)
            return [o["Key"] for page in pages for o in page.get("Contents", [])]
        files = (p.relative_to(self.dir).as_posix() for p in (self.dir / prefix.rpartition("/")[0]).rglob("*"))
        return sorted(k for k in files if k.startswith(prefix) and (self.dir / k).is_file())

    def exists(self, key: str) -> bool:
        return key in self.keys(key)

    def download(self, key: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.bucket:
            self.s3.download_file(self.bucket, key, str(path))
        else:
            shutil.copyfile(self.dir / key, path)

    def upload(self, path: Path, key: str) -> None:
        if self.bucket:
            self.s3.upload_file(str(path), self.bucket, key)
        else:
            (self.dir / key).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, self.dir / key)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")