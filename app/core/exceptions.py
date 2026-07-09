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

# ─── Domain Exceptions (Excepciones de Dominio) ───────────────────────────────────────────────────
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
       status_code=exc.status_code, 
       content={"error": True, "status_code": exc.status_code, "detail": exc.detail},
       headers=exc.headers
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
   # ["El código de estado 403 Forbidden indica que el servidor ha comprendido la solicitud pero se niega a autorizarla,"] #  # noqa: E501
   @app.exception_handler(AuthorizationError)
   async def authorization_error_handler(
      request: Request, exc: AuthorizationError
   ) -> JSONResponse:
      return JSONResponse(
         status_code=status.HTTP_403_FORBIDDEN, 
         content={"detail": exc.detail}
      )


   ### --- Error: Lógica de Negocio 
   @app.exception_handler(BusinessLogicError)
   async def business_error_logic(
      request: Request, exc: BusinessLogicError
   ) -> JSONResponse:
      return JSONResponse(
         status_code=status.HTTP_400_BAD_REQUEST, 
         content={"detail": exc.detail}
      )


   ### --- Error: Interno de Servidor (500)
   @app.exception_handler(Exception)
   async def unhandled_exception_handler(
      request: Request, exc: Exception
   ) -> JSONResponse:
      logger.error(
            "unhandled_exception",
            path=request.url.path, 
            method=request.method, 
            error=str(exc),
            exc_info=True
         ) 
      return JSONResponse(
         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
         content={"detail": "Error Interno del Servidor | Internal Server Error"}
      )