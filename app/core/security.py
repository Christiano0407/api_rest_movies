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
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Cookie, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError



#? ─── Hash | Hashing | Hashed | Bcrypt) ───────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain:str) -> str:
  return _pwd_context.hash(plain)

def verify_password(plain:str, hashed:str) -> bool:
  return _pwd_context.verify(plain, hashed)


#? ─── JWT (JSON Web Token) [Tipado - Seguridad Token] ─────────────────────────────────────────────
_bearer_scheme = HTTPBearer(auto_error=False)

# === Create & Type Token (Creamos & Tipamos) Token === 
def _create_token(
    subject: str, # Usuario
    kind: str, # Tipo de Token
    expires_delta: timedelta, # Fecha de Expiración
    settings: Settings, # Datos: DB & key Access - 
    extra: dict[str, Any] | None = None,
) -> str:
  now = datetime.now(UTC) # Fecha Actual (Token)
  # Payload: Claims [Es un objeto JSON codificado en Base64 que almacena pares clave-valor.]
  payload: dict[str, Any] = {
    "sub": subject, 
    "kind": kind, 
    "iat": now, 
    "exp": now + expires_delta,
    "jti": str(uuid.uuid4()), # Tipando | Clave única - uuid 
    **(extra or {}), 
  }
  return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# === Create: Access Token ===
def access_token(user_id:str, role:str, settings: Settings) -> str:
  return _create_token(
    subject=user_id, 
    kind= "access", 
    expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES), 
    settings= settings, 
    extra={"role":role}
  )

# === Create: Refresh Token ===
def refresh_token(user_id:str, settings:Settings) -> str:
  return _create_token(
    subject=user_id, 
    kind="refresh",
    expires_delta=timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    settings=settings,
  )

# === Decode (Decodificar el Error) Token  | Error Token ===
def decode_token(token:str, settings:Settings) -> dict[str, Any]: 
  try: 
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
  except JWTError as exec:
      raise AuthenticationError(
        "Credenciales Inválidas o Expiraron | Fecha del 'Token' expiró") from exec

#? ─── FastAPI Dependencies ────────────────────────────────────────────────────
# - Minimal parsed token payload injected into routes. (Carga útil mínima del token analizado inyectada en las rutas)  # noqa: E501

class CurrentUser: 
  """
    Minimal parsed token payload injected into routes. (Carga útil mínima del token analizado inyectada en las rutas)  # noqa: E501
    - ID User 
    - Role (RBAC)
  """  # noqa: E501
  def __init__(self, user_id:str, role:str) -> None:
    self.user_id = user_id
    self.role = role

  def _get_current_user(
      credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
      settings: Settings = Depends(get_settings), 
  ) -> CurrentUser: 
    if not credentials: 
      raise AuthenticationError("Credenciales Inválidas o han expirado | Tiempo del Token expiró")
    payload = decode_token(credentials.credentials, settings)
    if payload.get("kind") != "access":
        raise AuthenticationError("Token Inválido - Se requiere access token")
    return CurrentUser(user_id=payload["sub"], role=payload.get("role", "reader"))
  
  def get_current_user(
      user: CurrentUser=Depends(_get_current_user)
  ) -> CurrentUser:
    return user
  
  def require_roles(*roles:str): 
    """
        Factory that returns a dependency enforcing role membership.(Fábrica que devuelve 
        una dependencia que impone la membresía del rol.)
        - 403 Forbidden en la autenticación 'JWT' indica que el servidor rechaza 
            el acceso porque el token es inválido, está ausente 
            o carece de los permisos necesarios.
        - 403 Forbidden indica que el servidor entiende la solicitud pero niega 
            el acceso porque el cliente carece de los permisos necesarios.
    """
    def _dep(user:CurrentUser = Depends(get_current_user)) -> CurrentUser:
      if user.role not in roles: 
        raise AuthorizationError(
          "Acceso denegado | el token es inválido, está ausente o carece de los permisos necesarios"
        )
      return user
      
    return _dep
  
  require_admin = require_roles("admin")
  require_editor_or_admin = require_roles("admin", "editor")

  def get_refresh_token_cookies(
      refresh_token: str | None = Cookie(default=None, alias="refresh_token"), 
      settings: Settings=Depends(get_settings),
  ) -> dict[str, Any]: 
    if not refresh_token: 
      raise AuthenticationError("Refresh Token Ausente")
    payload = decode_token(refresh_token, settings)

    if payload.get("kind") != "refresh":
      raise AuthenticationError("Token Inválido - se requiere 'refresh token'")
    return payload