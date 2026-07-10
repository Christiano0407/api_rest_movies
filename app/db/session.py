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

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from sqlalchemy.ext.asyncio import ( 
    AsyncEngine, 
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine,
)
from contextlib import asynccontextmanager
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None