"""Respuestas de validación sin reproducir datos privados del cliente."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import DatabaseConfigurationError, DatabaseConnectionError


async def safe_validation_error(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    # FastAPI incluye `input` por defecto: puede contener una contraseña o nota.
    details = [
        {"loc": list(error["loc"]), "type": error["type"], "msg": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})


async def safe_database_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "La base de datos no está disponible. Intenta más tarde."},
    )


def register_error_handlers(application):
    application.add_exception_handler(RequestValidationError, safe_validation_error)
    for error_type in (SQLAlchemyError, DatabaseConfigurationError, DatabaseConnectionError):
        application.add_exception_handler(error_type, safe_database_error)
