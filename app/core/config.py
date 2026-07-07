"""Application settings — loaded from environment / .env via Pydantic Settings v2."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, EmailStr, PostgresDsn, RedisDsn, field_validator, model_validator
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
  
  # --- Server [Local] --- #
  HOST: str = "0.0.0.0"
  PORT: int = 8000
  WORKERS: int = 1
  RELOAD: bool = False
  
  # ---- Esto debe coincidir con las variables de entorno de tu docker-compose.yml ---- #
  POSTGRES_USER: str = "postgres"
  POSTGRES_PASSWORD: str = "cinema_db_api_gateway"
  POSTGRES_DB: str = "cinema_db"
  POSTGRES_HOST: str = "postgres"
  POSTGRES_PORT: int = 5432
  
  # --- Database URL | Cache --- #
  DATABASE_URL: str | None = None
  DATABASE_POOL_TIMEOUT: int = 30
  DATABASE_ECHO: bool = False
  REDIS_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")
  CACHE_TTL_SECONDS: int = 300 # 5 min Default
  
  # --- JWT (JSON Web Tokens) --- #
  JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_32+_random_chars"
  JWT_ALGORITHM: str = "HS256"
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

  # --- DB: MinIO / Storage s3 --- #

  # --- Celery / ARQ (ETL async) --- # 

  ## ── Docs ─────────────────────────────────────────────────────────────────

  ## ── Validators ───────────────────────────────────────────────────────────
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
  
settings = Settings()