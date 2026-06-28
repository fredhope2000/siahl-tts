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
