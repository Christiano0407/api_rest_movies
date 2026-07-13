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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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

# ----  tmdb_sessions  ---- #

# ---- token_blocklist ---- #