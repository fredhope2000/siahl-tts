import asyncio

from app.config import Settings
from app.models.domain import Game
from app.services.cache import TTLCache
from app.services.metadata import TimeToScoreService
from app.services.tts_client import TimeToScoreClient


def _service() -> TimeToScoreService:
    settings = Settings()
    return TimeToScoreService(
        settings=settings,
        cache=TTLCache(),
        client=TimeToScoreClient(settings),
    )


def _game(game_id: int, time_label: str) -> Game:
    return Game(
        id=game_id,
        season_id=74,
        date_label="2026-06-28",
        time_label=time_label,
        home_team_name=f"Home {game_id}",
        away_team_name=f"Away {game_id}",
    )


def test_normalize_officials_removes_blanks_and_duplicates() -> None:
    service = _service()

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


def test_game_sort_key_orders_noon_before_afternoon() -> None:
    service = _service()
    games = [_game(1, "1:30 PM"), _game(2, "12:30 PM")]

    games.sort(key=service._game_sort_key)

    assert [game.time_label for game in games] == ["12:30 PM", "1:30 PM"]


def test_game_sort_key_handles_midnight_and_unknown_times() -> None:
    service = _service()
    games = [_game(1, "TBD"), _game(2, "12:15 AM"), _game(3, "11:45 PM")]

    games.sort(key=service._game_sort_key)

    assert [game.time_label for game in games] == ["12:15 AM", "11:45 PM", "TBD"]


def test_configured_season_overrides_upstream_current_season() -> None:
    service = _service()

    season = service._normalize_current_season(
        {
            "leagues": [
                {
                    "current_season": 74,
                    "seasons": [
                        {"season_id": "74", "season_name": "Summer 2026"},
                        {"season_id": "77", "season_name": "Fall 2026"},
                    ],
                }
            ]
        }
    )

    assert season.id == 77
    assert season.label == "Fall 2026"


def test_normalize_seasons_includes_past_seasons() -> None:
    service = _service()

    seasons = service._normalize_seasons(
        {
            "leagues": [
                {
                    "seasons": [
                        {"season_id": "77", "season_name": "Fall 2026"},
                        {"season_id": "74", "season_name": "Summer 2026"},
                    ]
                }
            ]
        }
    )

    assert [(season.id, season.label) for season in seasons] == [
        (77, "Fall 2026"),
        (74, "Summer 2026"),
    ]
    assert seasons[0].is_current is True
    assert seasons[1].is_current is False


def test_past_season_standings_use_separate_cache_keys() -> None:
    class RecordingClient:
        def __init__(self) -> None:
            self.season_ids: list[int] = []

        async def request(self, endpoint: str, params: dict) -> dict:
            assert endpoint == "get_standings"
            self.season_ids.append(params["season_id"])
            return {
                "standings": {
                    "leagues": [
                        {
                            "levels": [
                                {
                                    "id": 221,
                                    "name": "Adult Division 4",
                                    "conferences": [],
                                }
                            ]
                        }
                    ]
                }
            }

    settings = Settings(tts_api_key="test", tts_api_secret="test")
    recording_client = RecordingClient()
    service = TimeToScoreService(
        settings=settings,
        cache=TTLCache(),
        client=recording_client,  # type: ignore[arg-type]
    )

    first = asyncio.run(service.get_all_standings(74))
    asyncio.run(service.get_all_standings(74))
    second_season = asyncio.run(service.get_all_standings(73))

    assert recording_client.season_ids == [74, 73]
    assert first[0].season_id == 74
    assert first[0].division.name == "Division 4"
    assert second_season[0].season_id == 73
