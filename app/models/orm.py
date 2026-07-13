"""
  SQLAlchemy ORM models
"""

from __future__ import annotations
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
  BigInteger, 
  Boolean, 
  DateTime, 
  Enum, 
  Float, 
  ForeignKey, 
  Integer, 
  SmallInteger, 
  String, 
  Text, 
  UniqueConstraint, 
  func,
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column

from app.db.base import Base
from app.enums import RoleEnum

# === Declarative (db) | enum ===
# ---- User ---- #
class Users(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(primary_key=True)
  user_name: Mapped[str] = mapped_column(
    String(50), 
    nullable=False,
    unique=True, 
    index=True,
  )
  email: Mapped[str] = mapped_column(
    String(255), 
    nullable=False,
    unique=True, 
    index=True,
  )
  password_hash: Mapped[str] = mapped_column(
    String(255), 
    nullable=False,
  )
  role: Mapped[RoleEnum] = mapped_column(
    Enum(RoleEnum, name="user_role"), 
    default=RoleEnum.USER,
    nullable=False,
  )
  is_active: Mapped[bool] = mapped_column(
    Boolean, 
    nullable=False, 
    default=True,
  )
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
  )
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(), 
    onupdate=func.now(),
  )


# ----  tmdb_sessions  ---- #
class TMDBSessions(Base):
  __tablename__ = "tmdb_sessions"

  id: Mapped[int] = mapped_column(primary_key=True)
  user_id: Mapped[str] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    unique=True, 
    index=True,
  )
  tmdb_account_id: Mapped[str] = mapped_column(
    String(100), 
    nullable=False,
  )
  tmdb_session_id: Mapped[str] = mapped_column(
    String(255), 
    nullable=False,
  )
  connected_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), 
    server_default=func.now(),
  )
  users: Mapped["Users"] = relationship(
    back_popular="tmdb_sessions"
  )


# ---- token_blocklist ---- #
class TokenBlocklist(Base): 
  __tablename__ = "token_blocklist"

  id: Mapped[int] = mapped_column(primary_key=True)
  jti: Mapped[str] = mapped_column(
    String(255), 
    nullable=False, 
    unique=True, 
    index=True
  )
  exp: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False
  )
  blocked_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), 
    server_default=func.now()
  )