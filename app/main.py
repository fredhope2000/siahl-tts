from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
from app.services.cache import TTLCache
from app.services.metadata import TimeToScoreService
from app.services.tts_client import TimeToScoreClient


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    cache = TTLCache()
    client = TimeToScoreClient(settings)
    app.state.settings = settings
    app.state.tts_service = TimeToScoreService(settings, cache, client)

    app.include_router(pages_router)
    app.include_router(api_router)
    return app


app = create_app()
