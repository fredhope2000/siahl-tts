from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
from app.services.cache import TTLCache
from app.services.metadata import TimeToScoreService
from app.services.tts_client import TimeToScoreClient

logger = logging.getLogger(__name__)


async def _refresh_loop(app: FastAPI) -> None:
    service = app.state.tts_service
    settings = app.state.settings
    meta_interval = max(settings.refresh_meta_interval_seconds, 60)
    standings_interval = max(settings.refresh_standings_interval_seconds, 60)
    schedule_interval = max(settings.refresh_schedule_interval_seconds, 60)
    last_meta = 0.0
    last_standings = 0.0
    last_schedule = 0.0

    while True:
        now = asyncio.get_running_loop().time()
        try:
            if now - last_meta >= meta_interval:
                await service.refresh_meta()
                last_meta = now
            if now - last_standings >= standings_interval:
                await service.refresh_all_standings()
                last_standings = now
            if now - last_schedule >= schedule_interval:
                await service.refresh_schedule(view="upcoming")
                last_schedule = now
        except Exception:
            logger.exception("Background refresh failed")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    refresh_task = None
    service = app.state.tts_service
    settings = app.state.settings
    if settings.upstream_enabled and not settings.use_mock_data:
        if settings.prewarm_on_startup:
            try:
                await service.prewarm_hot_data()
            except Exception:
                logger.exception("Startup prewarm failed")
        refresh_task = asyncio.create_task(_refresh_loop(app))
    try:
        yield
    finally:
        if refresh_task is not None:
            refresh_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await refresh_task


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    cache = TTLCache()
    client = TimeToScoreClient(settings)
    app.state.settings = settings
    app.state.tts_service = TimeToScoreService(settings, cache, client)

    app.include_router(pages_router)
    app.include_router(api_router)
    return app


app = create_app()
