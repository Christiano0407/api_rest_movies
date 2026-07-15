"""Application settings — loaded from environment / .env via Pydantic Settings v2."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  
  model_config = SettingsConfigDict (
      env_file=".env", 
      env_file_encoding="utf_8", 
      case_sensitive=False,
      extra="ignore",
  )
  
  # --- App --- #
  APP_NAME: str = "Secure Cinema API Gateway"
  APP_VERSION: str = "0.1.0"
  ENVIRONMENT: Literal["development", "staging", "production"] = "development"
  DEBUG: bool = False
  LOG_LEVEL: str = "INFO"
  API_V1_PREFIX: str = "/api/v1"
  
  # --- Server [Local] | (uvicorn Local) --- #
  HOST: str = "0.0.0.0"
  PORT: int = 8000
  WORKERS: int = 1
  RELOAD: bool = False
  
  # ---- Esto debe coincidir con las variables de entorno de tu docker-compose.yml ---- #
  # --- PostgreSQL — mismas variables que usa el servicio `postgres` en docker-compose.yml ---
  POSTGRES_USER: str = "postgres"
  POSTGRES_PASSWORD: str = "cinema_db_api_gateway"
  POSTGRES_DB: str = "cinema_db"
  POSTGRES_HOST: str = "postgres"
  POSTGRES_PORT: int = 5432
  
  # --- Database URL | Cache --- #
  DATABASE_URL: str | None = None
  DATABASE_POOL_SIZE: int = 20
  DATABASE_POOL_TIMEOUT: int = 30
  DATABASE_MAX_OVERFLOW: int = 10
  DATABASE_ECHO: bool = False
  #REDIS_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")
  REDIS_URL: str = "redis://redis:6379/0"
  CACHE_TTL_SECONDS: int = 120 # Default
  
  # --- JWT (JSON Web Tokens) | RS256 asimétrico (ver nota en core/security.py sobre por qué no HS256) --- #  # noqa: E501
  JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_32+_random_chars"
  #JWT_ALGORITHM: str = "HS256" 
  JWT_PRIVATE_KEY_PATH: str = "/app/keys/private.pem"
  JWT_PUBLIC_KEY_PATH: str = "/app/keys/public.pem"
  JWT_ALGORITHM: str = "RS256"
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
  JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

  # --- AUTH Cookies --- #
  REFRESH_COOKIES_NAME: str = "refresh_token"
  REFRESH_COOKIE_PATH: str = "/api/v1/endpoints/auth/refresh"
  REFRESH_COOKIE_HTTPONLY: bool = True
  REFRESH_COOKIE_SECURE: bool = False
  REFRESH_COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "lax"

  # --- CORS ( Conexión con Navegadores / Browser ) --- #
  CORS_ORIGIN: list[AnyHttpUrl | str] = ["http://localhost:3000", "http://localhost:5173"]
  CORS_ALLOW_CREDENTIALS: bool = True

  # --- Rate Limiting (Límite de 'Request' / Peticiones) --- #
  # Rate limiting por rol (peticiones/minuto) — RBAC + Redis INCR/EXPIRE #
  RATE_LIMIT_PUBLIC: int = 30 # req/min
  RATE_LIMIT_AUTH: int = 10 # req/min
  RATE_LIMITS_PER_MINUTE: dict[str, int] = {
        "Admin": 1000,
        "Manager": 500,
        "Editor": 300,
        "Moderator": 300,
        "Premium": 120,
        "User": 60,
    }

  # --- DB: MinIO / Storage s3 --- #

  # --- Celery / ARQ (ETL async) --- # 

  # --- TMDB (API Movies) --- #
  TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
  TMDB_API_KEY: str 
  TMDB_ACCESS_TOKEN: str
  TMDB_TIMEOUT_SECONDS: int=10
  TMDB_MAX_RETRIES: int=3

  ## ── Docs | DLCS | Propiedades ─────────────────────────────────────────────────────────────────
  @property
  def docs_enable(self) -> bool:
      return self.ENVIRONMENT in ("development", "staging")
  
  @property
  def jwt_private_key(self) -> str:
      return Path(self.JWT_PRIVATE_KEY_PATH).read_text()
  
  @property
  def jwt_public_key(self) -> str:
      return Path(self.JWT_PUBLIC_KEY_PATH).read_text()
  
  @property
  def db_url_str(self) -> str: 
      return (
        f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
      )

  ## ── Validators ───────────────────────────────────────────────────────────----------------------
  
  # --- Database URL (2) --- #
  @model_validator(mode="after")
  def _build_database_url(self) -> Settings:
    if not self.DATABASE_URL:
      # ---- Construye la URL asíncrona usando asyncpg ---- #
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
    return self

  @field_validator("JWT_SECRET_KEY")
  @classmethod
  def validator_secret_key(cls, v:str) -> str:
      if len(v) <32:
        raise ValueError("" \
        "jwt_secret_key must be at least 32 characters (Debe tener al menos 32 caracteres.)")
      return v

  @model_validator(mode="after")
  def secure_cookie_in_production(self) -> Settings:
      if self.ENVIRONMENT == "production" and not self.REFRESH_COOKIE_SECURE:
        raise ValueError("REFRESH_COOKIE_SECURE must be True in production")
      return self
  
  @model_validator(mode="after")
  def _validate_production_settings(self) -> Settings:
      if self.ENVIRONMENT == "production" and self.POSTGRES_PASSWORD == "cinema_db_api_gateway": 
          raise ValueError(
              "POSTGRES_PASSWORD, debe de cambiarse antes de desplegar a production (Deploy)")
      return self

## ---- Cache ----
@lru_cache(maxsize=1)
def get_settings() -> Settings:
      return Settings()

settings = get_settings()