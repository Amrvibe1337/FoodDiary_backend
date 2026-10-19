from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Identity, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .diary import DiaryEntry, Favorite
    from .wall import Comment, Post, PostLike


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="users_role_check"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", server_default="user"
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    diary_entries: Mapped[list[DiaryEntry]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    favorites: Mapped[list[Favorite]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    posts: Mapped[list[Post]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    comments: Mapped[list[Comment]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    post_likes: Mapped[list[PostLike]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )