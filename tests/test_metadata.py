from app.config import Settings
from app.services.cache import TTLCache
from app.services.metadata import TimeToScoreService
from app.services.tts_client import TimeToScoreClient


def test_normalize_officials_removes_blanks_and_duplicates() -> None:
    settings = Settings()
    service = TimeToScoreService(
        settings=settings,
        cache=TTLCache(),
        client=TimeToScoreClient(settings),
    )

    officials = service._normalize_officials(
        {
            "officials": {
                "1": "Terence Lim",
                "2": "Michael Harrison",
                "3": "",
            },
            "referee": "terence lim",
        }
    )

    assert officials == ["Terence Lim", "Michael Harrison"]
