from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "SIAHL")
    base_url: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    league_id: int = int(os.getenv("LEAGUE_ID", "1"))
    current_season_id: int = int(os.getenv("CURRENT_SEASON_ID", "74"))
    tts_api_base: str = os.getenv(
        "TTS_API_BASE", "https://api.sharksice.timetoscore.com"
    )
    tts_site_base: str = os.getenv(
        "TTS_SITE_BASE", "https://stats.sharksice.timetoscore.com"
    )
    tts_api_key: str = os.getenv("TTS_API_KEY", "")
    tts_api_secret: str = os.getenv("TTS_API_SECRET", "")
    cache_ttl_meta: int = int(os.getenv("CACHE_TTL_META", "43200"))
    cache_ttl_schedule: int = int(os.getenv("CACHE_TTL_SCHEDULE", "600"))
    cache_ttl_standings: int = int(os.getenv("CACHE_TTL_STANDINGS", "600"))
    cache_ttl_team: int = int(os.getenv("CACHE_TTL_TEAM", "3600"))
    use_mock_data: bool = _get_bool("USE_MOCK_DATA", False)

    @property
    def upstream_enabled(self) -> bool:
        return bool(self.tts_api_key and self.tts_api_secret)


settings = Settings()
