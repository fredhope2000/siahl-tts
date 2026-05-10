from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.config import Settings
from app.models.domain import (
    Division,
    Game,
    MetaPayload,
    RosterPlayer,
    ScheduleFilters,
    SchedulePayload,
    Season,
    StandingRow,
    StandingsPayload,
    Team,
    TeamPageData,
)
from app.services.cache import TTLCache
from app.services.tts_client import TimeToScoreClient


class TimeToScoreService:
    def __init__(self, settings: Settings, cache: TTLCache, client: TimeToScoreClient):
        self.settings = settings
        self.cache = cache
        self.client = client

    @property
    def uses_mock_data(self) -> bool:
        return self.settings.use_mock_data or not self.settings.upstream_enabled

    async def get_meta(self) -> MetaPayload:
        async def loader() -> MetaPayload:
            if self.uses_mock_data:
                return self._mock_meta()

            raw = await self.client.request(
                "get_divisions",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                },
            )
            return self._normalize_meta(raw)

        return await self.cache.get_or_set(
            "meta", self.settings.cache_ttl_meta, loader
        )

    async def get_standings(self, division_id: int) -> StandingsPayload:
        async def loader() -> StandingsPayload:
            if self.uses_mock_data:
                return self._mock_standings(division_id)

            raw = await self.client.request(
                "get_standings",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                    "level_id": division_id,
                },
            )
            return await self._normalize_standings(raw, division_id)

        return await self.cache.get_or_set(
            f"standings:{division_id}", self.settings.cache_ttl_standings, loader
        )

    async def get_schedule(
        self,
        division_id: int | None = None,
        team_id: int | None = None,
        view: str = "upcoming",
    ) -> SchedulePayload:
        async def loader() -> SchedulePayload:
            if self.uses_mock_data:
                return self._mock_schedule(division_id, team_id, view)

            raw = await self.client.request(
                "get_schedule_lite",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                    "level_id": division_id,
                    "team_id": team_id,
                },
            )
            return self._normalize_schedule(raw, division_id, team_id, view)

        cache_key = f"schedule:{division_id}:{team_id}:{view}"
        return await self.cache.get_or_set(
            cache_key, self.settings.cache_ttl_schedule, loader
        )

    async def get_team_page(self, team_id: int) -> TeamPageData:
        async def loader() -> TeamPageData:
            if self.uses_mock_data:
                return self._mock_team_page(team_id)

            team_raw = await self.client.request("get_team_info", {"team_id": team_id})
            roster_raw = await self.client.request(
                "get_roster",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                    "team_id": team_id,
                },
            )
            schedule_raw = await self.client.request(
                "get_schedule",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                    "team_id": team_id,
                },
            )
            return self._normalize_team_page(team_raw, roster_raw, schedule_raw, team_id)

        return await self.cache.get_or_set(
            f"team:{team_id}", self.settings.cache_ttl_team, loader
        )

    def group_games_by_date(self, games: list[Game]) -> list[tuple[str, list[Game]]]:
        grouped: dict[str, list[Game]] = defaultdict(list)
        for game in games:
            label = game.date_label or "TBD"
            grouped[label].append(game)
        return sorted(grouped.items(), key=lambda item: item[0])

    def _normalize_meta(self, raw: dict[str, Any]) -> MetaPayload:
        season = Season(
            id=self.settings.current_season_id,
            label=f"Season {self.settings.current_season_id}",
            is_current=True,
        )
        divisions: list[Division] = []
        teams: list[Team] = []

        raw_divisions = self._extract_list(raw)
        for item in raw_divisions:
            division_id = self._int_from(item, ["level_id", "id"])
            if division_id is None:
                continue
            division = Division(
                id=division_id,
                name=self._str_from(item, ["level_name", "name"], f"Division {division_id}"),
                season_id=self.settings.current_season_id,
            )
            divisions.append(division)
            for team_item in item.get("teams", []):
                team_id = self._int_from(team_item, ["team_id", "id"])
                if team_id is None:
                    continue
                teams.append(
                    Team(
                        id=team_id,
                        name=self._str_from(team_item, ["team_name", "name"], f"Team {team_id}"),
                        season_id=self.settings.current_season_id,
                        division_id=division.id,
                        division_name=division.name,
                    )
                )

        return MetaPayload(current_season=season, divisions=divisions, teams=teams)

    async def _normalize_standings(
        self, raw: dict[str, Any], division_id: int
    ) -> StandingsPayload:
        meta = await self.get_meta()
        division = next(
            (item for item in meta.divisions if item.id == division_id),
            Division(
                id=division_id,
                name=f"Division {division_id}",
                season_id=self.settings.current_season_id,
            ),
        )
        standings = [
            StandingRow(
                team_id=self._int_from(item, ["team_id", "id"], 0),
                team_name=self._str_from(item, ["team_name", "name"], "Unknown Team"),
                division_id=division_id,
                gp=self._int_from(item, ["gp", "games_played"]),
                w=self._int_from(item, ["w", "wins"]),
                l=self._int_from(item, ["l", "losses"]),
                t=self._int_from(item, ["t", "ties"]),
                otl=self._int_from(item, ["otl", "ot_losses"]),
                gf=self._int_from(item, ["gf", "goals_for"]),
                ga=self._int_from(item, ["ga", "goals_against"]),
                gd=self._int_from(item, ["gd", "goal_diff"]),
                pts=self._int_from(item, ["pts", "points"]),
            )
            for item in self._extract_list(raw)
        ]
        return StandingsPayload(
            season_id=self.settings.current_season_id,
            division=division,
            standings=standings,
        )

    def _normalize_schedule(
        self,
        raw: dict[str, Any],
        division_id: int | None,
        team_id: int | None,
        view: str,
    ) -> SchedulePayload:
        games = [self._normalize_game(item) for item in self._extract_list(raw)]
        if view == "upcoming":
            games = [game for game in games if game.status != "final"]
        return SchedulePayload(
            season_id=self.settings.current_season_id,
            filters=ScheduleFilters(division=division_id, team=team_id, view=view),
            games=games,
        )

    def _normalize_team_page(
        self,
        team_raw: dict[str, Any],
        roster_raw: dict[str, Any],
        schedule_raw: dict[str, Any],
        team_id: int,
    ) -> TeamPageData:
        team_item = self._extract_first(team_raw)
        team = Team(
            id=team_id,
            name=self._str_from(team_item, ["team_name", "name"], f"Team {team_id}"),
            season_id=self.settings.current_season_id,
            division_id=self._int_from(team_item, ["level_id"]),
            division_name=self._str_from(team_item, ["level_name"]),
        )
        roster = [
            RosterPlayer(
                id=self._int_from(item, ["player_id", "id"]),
                name=self._str_from(item, ["player_name", "name"], "Unknown Player"),
                jersey_number=self._str_from(item, ["jersey_number", "number"]),
                position=self._str_from(item, ["position"]),
            )
            for item in self._extract_list(roster_raw)
        ]
        games = [self._normalize_game(item) for item in self._extract_list(schedule_raw)]
        return TeamPageData(team=team, roster=roster, games=games)

    def _normalize_game(self, item: dict[str, Any]) -> Game:
        game_id = self._int_from(item, ["game_id", "id"], 0)
        status = self._normalize_status(item)
        return Game(
            id=game_id,
            season_id=self.settings.current_season_id,
            division_id=self._int_from(item, ["level_id"]),
            venue=self._str_from(item, ["rink", "venue", "location"]),
            starts_at=self._str_from(item, ["starts_at", "game_date", "date_time"]),
            date_label=self._str_from(item, ["date_label", "game_date", "date"], "TBD"),
            time_label=self._str_from(item, ["time_label", "game_time", "time"]),
            status=status,
            home_team_id=self._int_from(item, ["home_team_id"]),
            home_team_name=self._str_from(item, ["home_team_name", "home"], "Home"),
            away_team_id=self._int_from(item, ["away_team_id"]),
            away_team_name=self._str_from(item, ["away_team_name", "away"], "Away"),
            home_score=self._int_from(item, ["home_score"]),
            away_score=self._int_from(item, ["away_score"]),
            external_game_url=f"{self.settings.tts_site_base.rstrip('/')}/test/game.php?game={game_id}",
            external_scorecard_url=(
                f"{self.settings.tts_site_base.rstrip('/')}/generate-scorecard.php?game_id={game_id}"
            ),
        )

    def _normalize_status(self, item: dict[str, Any]) -> str | None:
        raw = self._str_from(item, ["status", "game_status"], "").lower()
        if raw in {"final", "completed", "closed"}:
            return "final"
        if raw in {"live", "in progress"}:
            return "live"
        if raw in {"postponed"}:
            return "postponed"
        if raw:
            return "scheduled"
        if self._int_from(item, ["home_score"]) is not None or self._int_from(
            item, ["away_score"]
        ) is not None:
            return "final"
        return "scheduled"

    def _extract_list(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        for key in ["data", "results", "rows", "games", "teams", "levels", "divisions", "schedule"]:
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def _extract_first(self, raw: dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw, dict) and any(not isinstance(v, list) for v in raw.values()):
            return raw
        items = self._extract_list(raw)
        return items[0] if items else {}

    def _str_from(
        self, item: dict[str, Any], keys: list[str], default: str | None = None
    ) -> str | None:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return str(value)
        return default

    def _int_from(
        self, item: dict[str, Any], keys: list[str], default: int | None = None
    ) -> int | None:
        for key in keys:
            value = item.get(key)
            if value in (None, ""):
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return default

    def _mock_meta(self) -> MetaPayload:
        season = Season(
            id=self.settings.current_season_id,
            label=f"Season {self.settings.current_season_id}",
            is_current=True,
        )
        divisions = [
            Division(id=4, name="Division 4", season_id=season.id),
            Division(id=5, name="Division 5", season_id=season.id),
        ]
        teams = [
            Team(id=323, name="Ice Otters", season_id=season.id, division_id=4, division_name="Division 4"),
            Team(id=324, name="Blue Liners", season_id=season.id, division_id=4, division_name="Division 4"),
            Team(id=401, name="Night Shift", season_id=season.id, division_id=5, division_name="Division 5"),
        ]
        return MetaPayload(current_season=season, divisions=divisions, teams=teams)

    def _mock_standings(self, division_id: int) -> StandingsPayload:
        meta = self._mock_meta()
        division = next((item for item in meta.divisions if item.id == division_id), meta.divisions[0])
        rows = [
            StandingRow(team_id=323, team_name="Ice Otters", division_id=division.id, gp=10, w=7, l=2, t=1, gf=40, ga=24, gd=16, pts=15),
            StandingRow(team_id=324, team_name="Blue Liners", division_id=division.id, gp=10, w=6, l=3, t=1, gf=31, ga=27, gd=4, pts=13),
        ]
        return StandingsPayload(
            season_id=self.settings.current_season_id,
            division=division,
            standings=rows,
        )

    def _mock_schedule(
        self, division_id: int | None, team_id: int | None, view: str
    ) -> SchedulePayload:
        season_id = self.settings.current_season_id
        today = datetime.utcnow().date()
        games = [
            Game(
                id=576970,
                season_id=season_id,
                division_id=4,
                venue="Sharks Ice San Jose",
                starts_at=str(today + timedelta(days=1)),
                date_label=str(today + timedelta(days=1)),
                time_label="8:15 PM",
                status="scheduled",
                home_team_id=323,
                home_team_name="Ice Otters",
                away_team_id=324,
                away_team_name="Blue Liners",
                external_game_url=f"{self.settings.tts_site_base.rstrip('/')}/test/game.php?game=576970",
                external_scorecard_url=f"{self.settings.tts_site_base.rstrip('/')}/generate-scorecard.php?game_id=576970",
            ),
            Game(
                id=576900,
                season_id=season_id,
                division_id=4,
                venue="Sharks Ice Oakland",
                starts_at=str(today - timedelta(days=7)),
                date_label=str(today - timedelta(days=7)),
                time_label="7:00 PM",
                status="final",
                home_team_id=324,
                home_team_name="Blue Liners",
                away_team_id=323,
                away_team_name="Ice Otters",
                home_score=2,
                away_score=5,
                external_game_url=f"{self.settings.tts_site_base.rstrip('/')}/test/game.php?game=576900",
                external_scorecard_url=f"{self.settings.tts_site_base.rstrip('/')}/generate-scorecard.php?game_id=576900",
            ),
        ]
        if division_id is not None:
            games = [game for game in games if game.division_id == division_id]
        if team_id is not None:
            games = [
                game
                for game in games
                if game.home_team_id == team_id or game.away_team_id == team_id
            ]
        if view == "upcoming":
            games = [game for game in games if game.status != "final"]
        return SchedulePayload(
            season_id=season_id,
            filters=ScheduleFilters(division=division_id, team=team_id, view=view),
            games=games,
        )

    def _mock_team_page(self, team_id: int) -> TeamPageData:
        meta = self._mock_meta()
        team = next((item for item in meta.teams if item.id == team_id), meta.teams[0])
        roster = [
            RosterPlayer(id=1, name="Alex Chen", jersey_number="19", position="C"),
            RosterPlayer(id=2, name="Matt Rivera", jersey_number="4", position="D"),
            RosterPlayer(id=3, name="Nina Patel", jersey_number="31", position="G"),
        ]
        games = self._mock_schedule(team.division_id, team.id, "all").games
        return TeamPageData(team=team, roster=roster, games=games)
