"""File upload, download, rename/move, delete.

Upload flow (the interesting part):
  1) POST /files/upload-init    → backend creates DB row (status=pending),
                                  picks single-PUT or multipart based on size,
                                  returns presigned URL(s) to the client.
  2) Client PUTs bytes directly to S3 (one URL or one per part, parallel-able).
  3) POST /files/{id}/upload-complete → backend HEADs (single) or completes-
                                        multipart (multipart), flips status=ready.
"""

import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.config import settings
from app.db import get_db
from app.models import File, Folder
from app.permissions import can_access_file, can_access_folder
from app.schemas import (
    DownloadResponse,
    FileOut,
    FileUpdate,
    UploadCompleteRequest,
    UploadInitRequest,
    UploadInitResponse,
    UploadPart,
)
from app.storage import s3


router = APIRouter()


async def _get_owned_file(db: AsyncSession, user_id: str, file_id: int) -> File:
    f = (await db.execute(select(File).where(File.id == file_id))).scalar_one_or_none()
    if f is None or f.owner_user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return f


@router.post("/upload-init", response_model=UploadInitResponse)
async def upload_init(req: UploadInitRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> UploadInitResponse:
    if req.folder_id is not None:
        folder = (await db.execute(select(Folder).where(Folder.id == req.folder_id))).scalar_one_or_none()
        if folder is None or not can_access_folder(user, folder, "write"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")

    # Insert row first so we can use its id in the S3 key.
    f = File(
        owner_user_id=user.id,
        folder_id=req.folder_id,
        name=req.name,
        s3_key="",  # filled below
        size_bytes=req.size_bytes,
        mime_type=req.mime_type,
        status="pending",
    )
    db.add(f)
    await db.flush()  # get id
    f.s3_key = s3.object_key(user.id, f.id)

    if req.size_bytes < settings.multipart_threshold_bytes:
        url = s3.presign_put(f.s3_key, settings.presigned_url_ttl_seconds)
        await db.commit()
        return UploadInitResponse(file_id=f.id, type="single", url=url)

    # Multipart
    part_size = settings.multipart_part_size_bytes
    num_parts = max(1, math.ceil(req.size_bytes / part_size))
    upload_id = s3.create_multipart(f.s3_key, req.mime_type)
    f.upload_id = upload_id
    parts = [
        UploadPart(part_number=i + 1, url=s3.presign_part(f.s3_key, upload_id, i + 1, settings.presigned_url_ttl_seconds))
        for i in range(num_parts)
    ]
    await db.commit()
    return UploadInitResponse(
        file_id=f.id,
        type="multipart",
        upload_id=upload_id,
        parts=parts,
        part_size_bytes=part_size,
    )


@router.post("/{file_id}/upload-complete", response_model=FileOut)
async def upload_complete(file_id: int, req: UploadCompleteRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> FileOut:
    f = await _get_owned_file(db, user.id, file_id)
    if f.status == "ready":
        return FileOut.model_validate(f)

    if f.upload_id:  # multipart
        if not req.parts:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing parts list for multipart upload")
        s3_parts = [{"PartNumber": p.part_number, "ETag": p.etag} for p in sorted(req.parts, key=lambda p: p.part_number)]
        try:
            s3.complete_multipart(f.s3_key, f.upload_id, s3_parts)
        except Exception as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Multipart completion failed: {e}")
        f.upload_id = None
    else:  # single PUT — verify the object exists
        head = s3.head_object(f.s3_key)
        if head is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Object not found in S3 — did the upload PUT succeed?")
        # Trust uploaded size; could also enforce equality with f.size_bytes.
        f.size_bytes = int(head.get("ContentLength", f.size_bytes))

    f.status = "ready"
    await db.commit()
    await db.refresh(f)
    return FileOut.model_validate(f)


@router.get("/{file_id}/download", response_model=DownloadResponse)
async def download(file_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> DownloadResponse:
    f = await _get_owned_file(db, user.id, file_id)
    if not can_access_file(user, f, "read"):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    if f.status != "ready":
        raise HTTPException(status.HTTP_409_CONFLICT, "File upload not complete")
    url = s3.presign_get(f.s3_key, settings.presigned_url_ttl_seconds, download_filename=f.name)
    return DownloadResponse(url=url, expires_in_seconds=settings.presigned_url_ttl_seconds)


@router.patch("/{file_id}", response_model=FileOut)
async def update_file(file_id: int, req: FileUpdate, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> FileOut:
    f = await _get_owned_file(db, user.id, file_id)
    if not can_access_file(user, f, "write"):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    if req.name is not None:
        f.name = req.name
    if req.folder_id is not None and req.folder_id != f.folder_id:
        target = (await db.execute(select(Folder).where(Folder.id == req.folder_id))).scalar_one_or_none()
        if target is None or not can_access_folder(user, target, "write"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Target folder not found")
        f.folder_id = req.folder_id
    await db.commit()
    await db.refresh(f)
    return FileOut.model_validate(f)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> None:
    f = await _get_owned_file(db, user.id, file_id)
    if not can_access_file(user, f, "delete"):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    key = f.s3_key
    upload_id = f.upload_id
    await db.delete(f)
    await db.commit()
    if upload_id:
        s3.abort_multipart(key, upload_id)
    s3.delete_object(key)
