from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from outception.config import settings

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


def get_client(
    *, signature_version: str = settings.AWS_SIGNATURE_VERSION
) -> "S3Client":
    return boto3.client(
        "s3",
        # Empty string makes botocore raise "Invalid endpoint"; treat a
        # blank/unset value as "use the provider default" (real AWS).
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(
            region_name=settings.AWS_REGION, signature_version=signature_version
        ),
    )


client = get_client()

__all__ = ("client", "get_client")
