from datetime import datetime
from pydantic import BaseModel, Field


# ---------- Auth ----------

class DevLoginRequest(BaseModel):
    email: str
    display_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None = None

    class Config:
        from_attributes = True


# ---------- Folders ----------

class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: int | None = None


class FolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: int | None = None  # move to a different parent


class FolderOut(BaseModel):
    id: int
    name: str
    parent_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Files ----------

class FileOut(BaseModel):
    id: int
    name: str
    folder_id: int | None
    size_bytes: int
    mime_type: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FolderListing(BaseModel):
    folder: FolderOut | None  # null = root
    folders: list[FolderOut]
    files: list[FileOut]


class UploadInitRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    mime_type: str | None = None
    folder_id: int | None = None


class UploadPart(BaseModel):
    part_number: int
    url: str


class UploadInitResponse(BaseModel):
    file_id: int
    type: str  # "single" | "multipart"
    url: str | None = None  # single
    upload_id: str | None = None  # multipart
    parts: list[UploadPart] = []  # multipart
    part_size_bytes: int | None = None  # multipart


class UploadCompletePart(BaseModel):
    part_number: int
    etag: str


class UploadCompleteRequest(BaseModel):
    parts: list[UploadCompletePart] = []  # required for multipart, ignored for single


class FileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    folder_id: int | None = None


class DownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int
