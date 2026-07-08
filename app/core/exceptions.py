"""
  Custom exceptions and FastAPI exception handlers.
  Handle (Manejo de Errores) | API
    - "FastAPI simplifica el manejo de errores mediante manejadores de excepciones personalizados registrados con el decorador @app.exception_handler, permitiendo respuestas JSON consistentes y estructuradas.  Para errores específicos, se pueden crear clases de excepciones personalizadas (heredando de Exception) que facilitan la lógica de negocio y el registro de auditoría, mientras que para errores genéricos se utiliza un manejador global que captura excepciones no previstas y devuelve un código '500' seguro sin filtrar información sensible"

  Starlette
    - Starlette es el motor asíncrono sobre el que está construido FastAPI 
    - Manejo de excepciones: Captura y procesa errores antes de que lleguen al cliente.

"""  # noqa: E501
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

## ---- Logging (History) ----
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Domain Exceptions ────────────────────────────────────────────────────────
class NotFoundError(Exception): 
  def __init__(self, resource: str = "Recurso") -> None:
      self.resource = resource
      super().__init__(f"{resource} no encontrado")


class ConflictError(Exception):
    def __init__(self, detail: str = "El Recurso (resource) ya existe") -> None:
       super().__init__(detail)
       self.detail = detail


class AuthenticationError(Exception):
    def __init__(self, detail: str = "Credenciales Inválidas o han Expirado (Token - JWT)") -> None:
       super().__init__(detail)
       self.detail = detail


class AuthorizationError(Exception):
    def __init__(self, detail: str = "Acceso Denegado (No tiene Autorización) | RBAC") -> None:
       super().__init__(detail)
       self.detail = detail


class BusinessLogicError(Exception):
    def __init__(self, detail: str) -> None: 
       super().__init__(detail)
       self.detail = detail



# ─── Handlers | Starlette (Async - FastAPI)  ─────────────────────────────────-


