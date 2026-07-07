"""
  Security utilities: JWT tokens, password hashing, cookie helpers.
    # ─── Password | Encriptado (bcrypt) | Hash (Hashed | HASHEANDO password  | SALT ───────── #
    # - Un hash es una función matemática: 
    # - bcrypt es un algoritmo especializado de hashing para passwords. [Contiene  salt]
    # - Un salt es un valor aleatorio agregado al password.
    # =======
    # Hash	    Función matemática
    # Hashing	Proceso de aplicar hash
    # Hashed	Resultado ya procesado
    # bcrypt	Algoritmo hashing especializado
    # =======  
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Cookie, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings, get_setting
from app.core.exceptions import AuthenticationError, AuthorizationError



#? ─── Hash | Hashing | Hashed | Bcrypt) ───────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain:str) -> str:
  return _pwd_context.hash(plain)

def verify_password(plain:str, hashed:str) -> bool:
  return _pwd_context.verify(plain, hashed)


#? ─── JWT (JSON Web Token) ────────────────────────────────────────────────────────────────



# === Create Access Token ===


# === Decode (Decodificar el Error) Token  | Error Token ===

#? ─── FastAPI Dependencies ────────────────────────────────────────────────────
# - Minimal parsed token payload injected into routes. (Carga útil mínima del token analizado inyectada en las rutas)  # noqa: E501