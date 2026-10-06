"""Respuestas de validación sin reproducir datos privados del cliente."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def safe_validation_error(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    # FastAPI incluye `input` por defecto: puede contener una contraseña o nota.
    details = [
        {"loc": list(error["loc"]), "type": error["type"], "msg": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})
