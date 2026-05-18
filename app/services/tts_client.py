from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx

from app.config import Settings
from app.services.tts_signing import build_signed_query


class TimeToScoreClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._proxy_base_url: str | None = None
        self._proxy_session: str | None = None

    async def request(
        self, endpoint: str, params: dict[str, str | int | None]
    ) -> dict[str, Any]:
        if not self.settings.upstream_enabled:
            raise RuntimeError("TimeToScore credentials are not configured.")

        proxy_config = await self._get_proxy_config()
        if proxy_config is not None:
            proxy_base_url, proxy_session = proxy_config
            proxy_params = {
                "endpoint": endpoint,
                **{
                    key: str(value)
                    for key, value in params.items()
                    if value not in (None, "", -1)
                },
            }
            url = f"{proxy_base_url}?{urlencode(proxy_params)}"
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    url,
                    headers={"X-Proxy-Session": proxy_session},
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.json()

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

    async def _get_proxy_config(self) -> tuple[str, str] | None:
        if self._proxy_base_url and self._proxy_session:
            return (self._proxy_base_url, self._proxy_session)

        html = await self.fetch_public_page(
            f"test/standings.php?league={self.settings.league_id}"
        )
        proxy_base_match = re.search(r'data-proxy-base="([^"]+)"', html)
        proxy_session_match = re.search(r'data-proxy-session="([^"]+)"', html)
        if not proxy_base_match or not proxy_session_match:
            return None

        proxy_base = proxy_base_match.group(1).strip()
        proxy_session = proxy_session_match.group(1).strip()
        if not proxy_base or not proxy_session:
            return None

        self._proxy_base_url = urljoin(f"{self.settings.tts_site_base.rstrip('/')}/", proxy_base.lstrip("/"))
        self._proxy_session = proxy_session
        return (self._proxy_base_url, self._proxy_session)

    async def fetch_public_page(self, path: str) -> str:
        base = self.settings.tts_site_base.rstrip("/")
        url = f"{base}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.text
