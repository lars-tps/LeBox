"""S3 / MinIO client wrapper.

Two clients:
- INTERNAL client: used for actual S3 operations the backend performs itself
  (create_multipart_upload, complete_multipart_upload, head_object, delete_object).
  Points at S3_ENDPOINT_URL (e.g. http://minio:9000 inside docker-compose).

- PRESIGN client: used ONLY to generate presigned URLs that the browser will
  follow. Points at S3_PUBLIC_ENDPOINT_URL (e.g. http://localhost:9000) so the
  hostname inside the signed URL is reachable from the user's browser.

For real AWS S3 these are the same endpoint, so S3_PUBLIC_ENDPOINT_URL is
left unset and falls back to S3_ENDPOINT_URL (which is also unset, so boto3
uses the AWS default).
"""

import boto3
from botocore.client import Config
from functools import lru_cache

from app.config import settings


def _build_client(endpoint_url: str | None):
    cfg = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if settings.s3_use_path_style else "virtual"},
        region_name=settings.s3_region,
    )
    kwargs = {"config": cfg, "region_name": settings.s3_region}
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    if settings.s3_access_key_id and settings.s3_secret_access_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key_id
        kwargs["aws_secret_access_key"] = settings.s3_secret_access_key
    return boto3.client("s3", **kwargs)


@lru_cache(maxsize=1)
def _internal_client():
    return _build_client(settings.s3_endpoint_url)


@lru_cache(maxsize=1)
def _presign_client():
    # Fall back to the internal endpoint if no public endpoint is configured
    # (this is the correct behavior for real AWS S3 where there's only one).
    return _build_client(settings.s3_public_endpoint_url or settings.s3_endpoint_url)


def object_key(user_id: str, file_id: int) -> str:
    """Opaque key — does NOT mirror folder hierarchy.

    Renames/moves are pure DB updates; the S3 object never has to be re-keyed.
    """
    return f"users/{user_id}/{file_id}"


def presign_put(key: str, ttl: int) -> str:
    return _presign_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=ttl,
    )


def presign_get(key: str, ttl: int, download_filename: str | None = None) -> str:
    params: dict = {"Bucket": settings.s3_bucket, "Key": key}
    if download_filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{download_filename}"'
    return _presign_client().generate_presigned_url(
        "get_object", Params=params, ExpiresIn=ttl
    )


def create_multipart(key: str, content_type: str | None) -> str:
    params = {"Bucket": settings.s3_bucket, "Key": key}
    if content_type:
        params["ContentType"] = content_type
    resp = _internal_client().create_multipart_upload(**params)
    return resp["UploadId"]


def presign_part(key: str, upload_id: str, part_number: int, ttl: int) -> str:
    return _presign_client().generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=ttl,
    )


def complete_multipart(key: str, upload_id: str, parts: list[dict]) -> None:
    _internal_client().complete_multipart_upload(
        Bucket=settings.s3_bucket,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )


def abort_multipart(key: str, upload_id: str) -> None:
    try:
        _internal_client().abort_multipart_upload(
            Bucket=settings.s3_bucket, Key=key, UploadId=upload_id
        )
    except Exception:
        pass


def head_object(key: str) -> dict | None:
    try:
        return _internal_client().head_object(Bucket=settings.s3_bucket, Key=key)
    except Exception:
        return None


def delete_object(key: str) -> None:
    try:
        _internal_client().delete_object(Bucket=settings.s3_bucket, Key=key)
    except Exception:
        pass
