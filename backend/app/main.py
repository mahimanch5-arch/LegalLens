"""Legal Lens API — FastAPI application factory."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routes import auth, conversations, dev, documents, modes, ops
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.db.migrate import run_migrations
from app.db.session import dispose_engine, init_engine, sessionmaker
from app.ingestion.blob_store import BlobStore
from app.ingestion.worker import InProcessQueue
from app.orchestrator.stub.orchestrator import StubOrchestrator
from app.runtime import Runtime
from app.services import chat_turn
from app.services.auth import ensure_seed_user
from app.services.scenario import scenario

log = logging.getLogger("legallens")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await asyncio.to_thread(run_migrations, settings)
        init_engine(settings)
        async with sessionmaker()() as db:
            await ensure_seed_user(db, settings)
        recovered = await chat_turn.recover_interrupted()
        if recovered:
            log.info("marked %d interrupted turn(s) incomplete", recovered)

        blobs = BlobStore(settings)
        queue = InProcessQueue(settings, blobs)
        orchestrator = StubOrchestrator(
            sessionmaker(), lambda: scenario.token_delay_ms(settings.stub_token_delay_ms)
        )
        app.state.runtime = Runtime(settings=settings, blobs=blobs, queue=queue, orchestrator=orchestrator)
        await queue.start()
        log.info("Legal Lens API ready (env=%s, data=%s)", settings.env, settings.data_dir.resolve())
        try:
            yield
        finally:
            await queue.stop()
            await dispose_engine()

    app = FastAPI(
        title="Legal Lens API",
        version=settings.version,
        description="Backend for Legal Lens (milestone M3). Contract mirrors frontend/src/api/types.ts.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Content-Type", "Accept", "X-Request-ID"],
            expose_headers=["X-Request-ID", "Retry-After"],
        )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(RequestContextMiddleware)

    for router in (auth.router, conversations.router, modes.router, documents.router, ops.router):
        app.include_router(router)
    if settings.is_dev:
        app.include_router(dev.router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """The API lives under /api; send a browser at the bare origin to the interactive docs."""
        return RedirectResponse("/api/docs")

    return app


app = create_app()
