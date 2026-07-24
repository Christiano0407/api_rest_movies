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
    Claims: 
      -  # Payload: Claims [Es un objeto JSON codificado en Base64 que almacena pares clave-valor.]
    # ------------------------------------------------------------------------------------------- #
    # --- Nivel de módulo (NO anidada dentro de configure_logging) ---
    Nota de arquitectura: se evaluó migrar a HS256 + python-jose + refresh en cookies,
    pero se descartó — HS256 requiere distribuir un secreto compartido a cada servicio
    que necesite *verificar* tokens, mientras que RS256 permite publicar la llave pública
    libremente (relevante en un patrón Gateway, donde otros servicios podrían necesitar
    verificar sin poder emitir). python-jose además tiene menos mantenimiento activo que
    PyJWT. Se mantiene lo ya probado end-to-end (19/19 tests, Docker, CI).

"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError



#? ─── Hash | Hashing | Hashed | Bcrypt) ───────────────────────────────────────────────────────────

_BCRYPT_MAX_BYTES = 72

def hash_password(plain_password: str) -> str:
  secret = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
  return bcrypt.hashpw(secret, bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password:str, hashed:str) -> bool:
  secret = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
  return bcrypt.checkpw(secret, hashed.encode("utf-8"))


#? ─── JWT (JSON Web Token) [Tipado - Seguridad Token] ─────────────────────────────────────────────

# === Create & Type Token (Creamos & Tipamos) Token === 
def _create_token(
    subject: str, # Usuario
    role: str, # Role (RBAC)
    token_type: str, # Tipo de Token
    expires_delta: timedelta, # Fecha de Expiración 
    extra: dict[str, Any] | None = None,
) ->  tuple[str, str]:
  jti = str(uuid.uuid4()) # Tipando | Clave única - uuid 
  now = datetime.now(UTC) # Fecha Actual (Token)
  # Payload: Claims [Es un objeto JSON codificado en Base64 que almacena pares clave-valor.]
  payload: dict[str, Any] = {
    "sub": subject, 
    "role": role, 
    "type": token_type, 
    "jti": jti,
    "iat": now,
    "exp": now + expires_delta,
    **(extra or {}), 
  }
  token = jwt.encode(payload, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)
  return token, jti


# === Create: Access Token ===
def access_token(subject:str, role:str) -> tuple[str,str]:
  return _create_token(
    subject=subject, 
    role=role,
    token_type= "access", 
    expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES), 
  )

# === Create: Refresh Token ===
def refresh_token(subject:str, role:str) -> tuple[str,str]:
  return _create_token(
    subject=subject, 
    role=role,
    token_type="refresh",
    expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
  )

# === Decode (Decodificar el Error) Token  | Error Token ===
def decode_token(token:str) -> dict[str, Any]: 
  return jwt.decode(token, settings.jwt_public_key, algorithms=[settings.JWT_ALGORITHM])

