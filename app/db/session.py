"""
  Async database engine, session factory, and dependency injection.
  (Motor de base de datos asíncrono, fábrica de sesiones e inyección de dependencias.)
    - Sesiones & Conexion entre: DB & API - FastAPI
####################### ============================================ #######################
  En una arquitectura profesional de FastAPI, este archivo suele considerarse la capa de infraestructura de persistencia, porque centraliza:

    - Creación del AsyncEngine.
    - Gestión del pool de conexiones.
    - Creación de AsyncSession.
    - Dependency Injection (get_db).
    - Transacciones (commit / rollback).
    - Ciclo de vida (lifespan).
    - Soporte para testing (NullPool).
    
"""  # noqa: E501

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import ( 
    AsyncEngine, 
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.logging import get_logger


## --- Logging (History Process) --- #
logger = get_logger(__name__)

## === Singleton Pattern (Add) === ##
# [Sólo existirá 1 Engine & 1 Session factory en la vida de la aplicación | No se recrean]
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings:Settings | None = None) -> AsyncEngine:
  global _engine

  if _engine is None:
    cfg = settings or get_settings()

    _engine = create_async_engine(
      cfg.db_url_str,
      pool_size=cfg.DATABASE_POOL_SIZE, 
      max_overflow=cfg.DATABASE_MAX_OVERFLOW, 
      pool_timeout=cfg.DATABASE_POOL_TIMEOUT, 
      POOL_PRE_PING=True, 
      echo=cfg.DATABASE_ECHO, 
    )
  return _engine

def get_session_factory(
    settings: Settings | None = None
) -> async_sessionmaker[AsyncSession]: 
  global _session_factory

  pass