import os
import tempfile
from contextlib import contextmanager

import boto3

from app.core.config import settings


def save(contents: bytes, filename: str) -> str:
    """Persist uploaded file bytes, returning a storage_path to save on the Document row."""
    if settings.storage_backend == "s3":
        client = _s3_client()
        client.put_object(Bucket=settings.s3_bucket, Key=filename, Body=contents)
        return filename

    os.makedirs(settings.upload_dir, exist_ok=True)
    path = os.path.join(settings.upload_dir, filename)
    with open(path, "wb") as f:
        f.write(contents)
    return path


@contextmanager
def open_local(storage_path: str):
    """Yield a local filesystem path for storage_path, downloading from S3 first if needed."""
    if settings.storage_backend != "s3":
        yield storage_path
        return

    suffix = os.path.splitext(storage_path)[1]
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        _s3_client().download_fileobj(settings.s3_bucket, storage_path, tmp)
        tmp.flush()
        yield tmp.name


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )
