from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .auth import AuthService
from .config import Settings, get_settings
from .database import Database
from .errors import BackendError
from .repositories import AnalysisRepository


def create_app(
    settings: Settings | None = None,
    *,
    analysis_repository: AnalysisRepository | Any | None = None,
    auth_service: AuthService | Any | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    database = None
    if analysis_repository is None:
        database = Database(resolved_settings)
        analysis_repository = AnalysisRepository(database, resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if database is not None:
            database.open()
        try:
            yield
        finally:
            if database is not None:
                database.close()

    app = FastAPI(title="SystemLab Backend", version="0.1.0", lifespan=lifespan)
    app.state.analysis_repository = analysis_repository
    app.state.auth_service = auth_service or AuthService(resolved_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in resolved_settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(BackendError)
    async def backend_error_handler(_: Request, exc: BackendError) -> JSONResponse:
        headers = dict(exc.headers)
        if exc.status_code == 401:
            headers.setdefault("Cache-Control", "private, no-store")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
            headers=headers,
        )

    app.include_router(router)
    return app


def run() -> None:
    uvicorn.run("systemlab_backend.main:create_app", factory=True, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    run()
