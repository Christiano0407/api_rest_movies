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

## === Errorers (Excepciones que pueden pasar) al  Registarse (User) | No han tenido éxito (Handler) ===  # noqa: E501
def register_exception_handler(app: FastAPI) -> None: 
   
   ### --- Error: registro 
   @app.exception_handler(StarletteHTTPException)
   async def http_exception_handler(
      request: Request, exc: StarletteHTTPException
   ) -> JSONResponse:
    return JSONResponse(
       status_code=status.status_code, 
       content={"detail": exc.detail},
    )
   
   ### --- Error: Peticiones / Request
   @app.exception_handler(RequestValidationError)
   async def not_found_handler(
         request: Request, exc: RequestValidationError
   ) -> JSONResponse: 
      return JSONResponse(
         status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, 
         content={"detail": exc.errors()}, 
      )
   
   ### --- Error: No ha sido encontrado
   @app.exception_handler(NotFoundError)
   async def validator_exception_handler(
      request: Request, exc: NotFoundError
   ) -> JSONResponse:
      return JSONResponse(
         status_code=status.HTTP_404_NOT_FOUND, 
         content={"detail": str(exc)}
      )
   
   ### --- Error: Conflicto
   @app.exception_handler(ConflictError)
   async def conflict_error_handler(
      request: Request, exc: ConflictError
   ) -> JSONResponse: 
      return JSONResponse(
         status_code=status.HTTP_409_CONFLICT, 
         content={"detail": exc.detail}
      )


   ### --- Error: Auth (Authentication)
   @app.exception_handler(AuthenticationError)
   async def authentication_error_handler(
      request: Request, exc: AuthenticationError
   ) -> JSONResponse: 
      return JSONResponse(
         status_code=status.HTTP_401_UNAUTHORIZED, 
         content={"detail": exc.detail}, 
         headers={"WWW-Authenticate": "Bearer"}
      )

   ### --- Error: Authorization 


   ### --- Error: Lógica de Negocio 


   ### --- Error: Interno de Servidor


