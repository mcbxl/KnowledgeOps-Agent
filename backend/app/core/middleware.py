from __future__ import annotations

import secrets
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {
        "/api/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.api_key or request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        supplied_key = request.headers.get("x-api-key")
        if supplied_key and secrets.compare_digest(supplied_key, settings.api_key):
            return await call_next(request)

        request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or str(uuid4())
        return JSONResponse(
            status_code=401,
            content={
                "detail": "A valid X-API-Key header is required.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
