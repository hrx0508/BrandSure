"""Consistent error format: {"error": {"code", "message", "request_id"}}."""
import logging
import uuid

log = logging.getLogger("brandsure")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _body(request, code: str, message: str) -> dict:
    rid = getattr(request.state, "request_id", "req_unknown")
    return {"error": {"code": code, "message": message, "request_id": rid}}


async def request_id_middleware(request, call_next):
    request.state.request_id = "req_" + uuid.uuid4().hex[:10]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def install(app) -> None:
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status, content=_body(request, exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in first.get("loc", [])[1:])
        msg = f"Invalid request{': ' + loc if loc else ''}. {first.get('msg', '')}".strip()
        return JSONResponse(status_code=422, content=_body(request, "VALIDATION_ERROR", msg))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        # Log metadata only (never draft text); never return stack traces.
        log.exception("Unhandled error %s", getattr(request.state, "request_id", ""))
        return JSONResponse(status_code=500, content=_body(request, "INTERNAL_ERROR", "Something went wrong on our side."))
