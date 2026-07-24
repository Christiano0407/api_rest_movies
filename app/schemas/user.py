"""
  Pydantic v2 schemas — mirrors the OpenAPI contract exactly.
  ("Los esquemas de Pydantic v2 (Tipar Datos) reflejan exactamente el contrato OpenAPI")
  - "Pydantic es la biblioteca de validación de datos más popular en Python, diseñada para 
    validar, convertir y serializar datos estructurados utilizando las anotaciones de tipo (type hints)
     nativas del lenguaje."
  # =============================================== #
    - " En Pydantic v2, model_config = ConfigDict(from_attributes=True) es una configuración que permite a
      los modelos validar y construir instancias a partir de objetos Python (como modelos ORM) en lugar 
      de únicamente diccionarios "
"""  # noqa: E501

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.enums import RoleEnum

T = TypeVar("T")

# ─── Shared ───────────────────────────────────────────────────────────────────

class ErrorOut(BaseModel):
  detail: str

class HealthOut(BaseModel):
  status: Literal["ok", "degraded", "down"]
  version: str
  environment: str


# ─── Create ─────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
  username: str = Field(min_length=3, max_length=30)
  email: EmailStr
  password: str = Field(min_length=8, max_length=128)


# ─── Update ─────────────────────────────────────────────────────────────────────
class UserUpdate(BaseModel):
  username: str | None = Field(default=None, min_length=3, max_length=50)
  email: EmailStr | None = None
  is_active: bool | None = None
  role: RoleEnum | None = None


# ─── Response ─────────────────────────────────────────────────────────────────────
class UserResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: int
  username: str
  email: EmailStr
  role: RoleEnum
  is_active: bool
  created_at: datetime
  update_at: datetime