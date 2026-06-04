"""FastAPI application factory.

Wires CORS, rate limiting, structured logging, and global exception handlers that
never leak stack traces or secrets to clients (Constitution Principle VI).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("app")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Recruiter copilot that builds verifiable, explainable candidate dossiers",
    )

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded, _rate_limit_exceeded_handler  # type: ignore[arg-type]
    )
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        log.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "docs": "/docs"}

    return app


app = create_app()
