from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings
from app.services.tts_signing import build_signed_query


class TimeToScoreClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def request(
        self, endpoint: str, params: dict[str, str | int | None]
    ) -> dict[str, Any]:
        if not self.settings.upstream_enabled:
            raise RuntimeError("TimeToScore credentials are not configured.")

        query = build_signed_query(
            endpoint=endpoint,
            api_key=self.settings.tts_api_key,
            api_secret=self.settings.tts_api_secret,
            params=params,
        )
        base = self.settings.tts_api_base.rstrip("/")
        url = f"{base}/{endpoint}?{query}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.json()
