from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, Index, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "parent_id", "name", name="uq_folder_sibling_name"),
        Index("ix_folders_owner_parent", "owner_user_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("folders.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    children: Mapped[list["Folder"]] = relationship(
        "Folder", backref="parent", remote_side="Folder.id", cascade="all, delete"
    )


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        Index("ix_files_owner_folder", "owner_user_id", "folder_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    folder_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("folders.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(200))
    # status: pending → ready. (Multipart uploads stay pending until completion.)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    upload_id: Mapped[str | None] = mapped_column(String(200))  # S3 multipart upload id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
