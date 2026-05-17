from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.db import get_db
from app.models import File, Folder
from app.permissions import can_access_folder
from app.schemas import FolderCreate, FolderListing, FolderOut, FileOut, FolderUpdate


router = APIRouter()


async def _get_owned_folder(db: AsyncSession, user_id: str, folder_id: int) -> Folder:
    folder = (await db.execute(select(Folder).where(Folder.id == folder_id))).scalar_one_or_none()
    if folder is None or folder.owner_user_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found")
    return folder


@router.get("", response_model=FolderListing)
async def list_root(user: CurrentUser, db: AsyncSession = Depends(get_db)) -> FolderListing:
    return await _list_contents(db, user.id, folder=None)


@router.get("/{folder_id}", response_model=FolderListing)
async def list_folder(folder_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> FolderListing:
    folder = await _get_owned_folder(db, user.id, folder_id)
    if not can_access_folder(user, folder, "read"):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return await _list_contents(db, user.id, folder=folder)


async def _list_contents(db: AsyncSession, user_id: str, folder: Folder | None) -> FolderListing:
    parent_id = folder.id if folder else None
    folder_match = Folder.parent_id.is_(None) if parent_id is None else Folder.parent_id == parent_id
    file_match = File.folder_id.is_(None) if parent_id is None else File.folder_id == parent_id
    sub = (await db.execute(
        select(Folder).where(Folder.owner_user_id == user_id, folder_match).order_by(Folder.name)
    )).scalars().all()
    files = (await db.execute(
        select(File)
        .where(File.owner_user_id == user_id, file_match, File.status == "ready")
        .order_by(File.name)
    )).scalars().all()
    return FolderListing(
        folder=FolderOut.model_validate(folder) if folder else None,
        folders=[FolderOut.model_validate(f) for f in sub],
        files=[FileOut.model_validate(f) for f in files],
    )


@router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(req: FolderCreate, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> FolderOut:
    if req.parent_id is not None:
        parent = await _get_owned_folder(db, user.id, req.parent_id)
        if not can_access_folder(user, parent, "write"):
            raise HTTPException(status.HTTP_403_FORBIDDEN)

    folder = Folder(owner_user_id=user.id, parent_id=req.parent_id, name=req.name)
    db.add(folder)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A folder with that name already exists here")
    await db.refresh(folder)
    return FolderOut.model_validate(folder)


@router.patch("/{folder_id}", response_model=FolderOut)
async def update_folder(folder_id: int, req: FolderUpdate, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> FolderOut:
    folder = await _get_owned_folder(db, user.id, folder_id)
    if not can_access_folder(user, folder, "write"):
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    if req.name is not None:
        folder.name = req.name
    if req.parent_id is not None and req.parent_id != folder.parent_id:
        # Prevent moving into self/descendant — simple ancestor walk.
        target = await _get_owned_folder(db, user.id, req.parent_id)
        cursor: Folder | None = target
        while cursor is not None:
            if cursor.id == folder.id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot move folder into itself")
            cursor = (
                await db.execute(select(Folder).where(Folder.id == cursor.parent_id))
            ).scalar_one_or_none() if cursor.parent_id else None
        folder.parent_id = req.parent_id

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Name conflict in destination")
    await db.refresh(folder)
    return FolderOut.model_validate(folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(folder_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> None:
    """Recursive delete. Cascades via FK; also removes S3 objects for descendant files."""
    folder = await _get_owned_folder(db, user.id, folder_id)
    if not can_access_folder(user, folder, "delete"):
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    # Collect all descendant file s3_keys before delete (cascade will remove rows).
    from app.storage.s3 import delete_object

    descendant_folder_ids: set[int] = {folder.id}
    frontier = [folder.id]
    while frontier:
        rows = (await db.execute(
            select(Folder.id).where(Folder.parent_id.in_(frontier))
        )).scalars().all()
        if not rows:
            break
        descendant_folder_ids.update(rows)
        frontier = list(rows)

    keys = (await db.execute(
        select(File.s3_key).where(File.folder_id.in_(descendant_folder_ids))
    )).scalars().all()

    await db.delete(folder)
    await db.commit()

    for key in keys:
        delete_object(key)
