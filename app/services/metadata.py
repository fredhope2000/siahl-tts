from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, datetime, timedelta
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

            leagues_raw, divisions_raw, standings_raw = await asyncio.gather(
                self.client.request(
                    "get_leagues",
                    {
                        "league_id": self.settings.league_id,
                    },
                ),
                self.client.request(
                    "get_divisions",
                    {
                        "league_id": self.settings.league_id,
                        "season_id": self.settings.current_season_id,
                    },
                ),
                self._get_all_standings_raw(),
            )
            return self._normalize_meta(leagues_raw, divisions_raw, standings_raw)

        return await self.cache.get_or_set(
            "meta", self.settings.cache_ttl_meta, loader
        )

    async def refresh_meta(self) -> MetaPayload:
        self.cache.delete("meta")
        return await self.get_meta()

    async def get_standings(self, division_id: int) -> StandingsPayload:
        async def loader() -> StandingsPayload:
            if self.uses_mock_data:
                return self._mock_standings(division_id)

            raw = await self.client.request(
                "get_standings",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                    "stat_class": self.settings.current_stat_class_id,
                    "level_id": division_id,
                },
            )
            return await self._normalize_standings(raw, division_id)

        return await self.cache.get_or_set(
            f"standings:{division_id}", self.settings.cache_ttl_standings, loader
        )

    async def get_all_standings(self) -> list[StandingsPayload]:
        if self.uses_mock_data:
            meta = self._mock_meta()
            return [self._mock_standings(division.id) for division in meta.divisions]

        raw = await self._get_all_standings_raw()
        meta = await self.get_meta()
        division_map = {division.id: division for division in meta.divisions}
        payloads: list[StandingsPayload] = []
        for level in self._extract_standings_levels(raw):
            level_id = self._int_from(level, ["id", "level_id"])
            if level_id is None:
                continue
            division = division_map.get(
                level_id,
                Division(
                    id=level_id,
                    name=self._normalize_division_name(
                        self._str_from(level, ["name", "level_name"], f"Division {level_id}")
                    )
                    or f"Division {level_id}",
                    season_id=self.settings.current_season_id,
                ),
            )
            standings: list[StandingRow] = []
            for conference in level.get("conferences", []):
                for item in conference.get("teams", []):
                    standings.append(
                        StandingRow(
                            team_id=self._int_from(item, ["id", "team_id"], 0),
                            team_name=self._clean_name(
                                self._str_from(item, ["team_name", "name"], "Unknown Team")
                            ),
                            division_id=level_id,
                            gp=self._int_from(item, ["games_played", "gp"]),
                            w=self._int_from(item, ["wins", "w"]),
                            l=self._int_from(item, ["losses", "l"]),
                            t=self._int_from(item, ["ties", "t"]),
                            otl=self._int_from(item, ["otlosses", "ot_losses", "otl"]),
                            gf=self._int_from(item, ["goals_for", "gf"]),
                            ga=self._int_from(item, ["goals_against", "ga"]),
                            gd=self._int_from(item, ["plusminus", "goal_diff", "gd"]),
                            pts=self._int_from(item, ["pts", "points"]),
                            streak=self._str_from(item, ["streak"]),
                        )
                    )
            standings.sort(key=lambda item: (-1 * (item.pts or 0), item.team_name))
            payloads.append(
                StandingsPayload(
                    season_id=self.settings.current_season_id,
                    division=division,
                    standings=standings,
                )
            )
        payloads.sort(key=lambda item: self._division_sort_key(item.division.name))
        return payloads

    async def refresh_all_standings(self) -> list[StandingsPayload]:
        self.cache.delete("standings:all")
        meta = await self.get_meta()
        for division in meta.divisions:
            self.cache.delete(f"standings:{division.id}")
        return await self.get_all_standings()

    async def get_schedule(
        self,
        division_id: int | None = None,
        team_id: int | None = None,
        view: str = "upcoming",
    ) -> SchedulePayload:
        async def loader() -> SchedulePayload:
            if self.uses_mock_data:
                return self._mock_schedule(division_id, team_id, view)

            raw = await self._fetch_schedule_raw(division_id, team_id, view)
            division_map = None
            if team_id is None and division_id is not None:
                meta = await self.get_meta()
                division_map = {team.id: team.division_id for team in meta.teams}
            return self._normalize_schedule(
                raw,
                division_id,
                team_id,
                view,
                team_division_map=division_map,
            )

        cache_key = f"schedule:{division_id}:{team_id}:{view}"
        return await self.cache.get_or_set(
            cache_key, self.settings.cache_ttl_schedule, loader
        )

    async def refresh_schedule(
        self,
        division_id: int | None = None,
        team_id: int | None = None,
        view: str = "upcoming",
    ) -> SchedulePayload:
        cache_key = f"schedule:{division_id}:{team_id}:{view}"
        self.cache.delete(cache_key)
        return await self.get_schedule(division_id=division_id, team_id=team_id, view=view)

    async def get_team_page(self, team_id: int) -> TeamPageData:
        async def loader() -> TeamPageData:
            if self.uses_mock_data:
                return self._mock_team_page(team_id)

            team_raw, roster_raw, schedule_raw = await asyncio.gather(
                self.client.request("get_team_info", {"team_id": team_id}),
                self.client.request(
                    "get_roster",
                    {
                        "league_id": self.settings.league_id,
                        "season_id": self.settings.current_season_id,
                        "stat_class": self.settings.current_stat_class_id,
                        "team_id": team_id,
                    },
                ),
                self.client.request(
                    "get_schedule",
                    {
                        "league_id": self.settings.league_id,
                        "season_id": self.settings.current_season_id,
                        "team_id": team_id,
                    },
                ),
            )
            return self._normalize_team_page(team_raw, roster_raw, schedule_raw, team_id)

        return await self.cache.get_or_set(
            f"team:{team_id}", self.settings.cache_ttl_team, loader
        )

    async def prewarm_hot_data(self) -> None:
        await self.refresh_meta()
        await asyncio.gather(
            self.refresh_all_standings(),
            self.refresh_schedule(view="upcoming"),
        )

    def group_games_by_date(self, games: list[Game]) -> list[tuple[str, list[Game]]]:
        grouped: dict[str, list[Game]] = defaultdict(list)
        for game in games:
            label = game.date_label or "TBD"
            grouped[label].append(game)
        return sorted(grouped.items(), key=lambda item: item[0])

    async def _fetch_schedule_raw(
        self, division_id: int | None, team_id: int | None, view: str
    ) -> dict[str, Any]:
        if team_id is not None:
            return await self.client.request(
                "get_schedule",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                    "stat_class": self.settings.current_stat_class_id,
                    "team_id": team_id,
                },
            )

        params: dict[str, str | int | None] = {
            "league_id": self.settings.league_id,
            "season_id": self.settings.current_season_id,
        }
        if view == "upcoming":
            params["date"] = date.today().isoformat()
            params["days"] = 20
        return await self.client.request("get_schedule_lite", params)

    async def _get_all_standings_raw(self) -> dict[str, Any]:
        async def loader() -> dict[str, Any]:
            return await self.client.request(
                "get_standings",
                {
                    "league_id": self.settings.league_id,
                    "season_id": self.settings.current_season_id,
                    "stat_class": self.settings.current_stat_class_id,
                },
            )

        return await self.cache.get_or_set(
            "standings:all", self.settings.cache_ttl_standings, loader
        )

    def _normalize_meta(
        self,
        leagues_raw: dict[str, Any],
        divisions_raw: dict[str, Any],
        standings_raw: dict[str, Any],
    ) -> MetaPayload:
        season = self._normalize_current_season(leagues_raw)
        divisions: list[Division] = []
        teams: list[Team] = []

        for item in divisions_raw.get("divisions", []):
            division_id = self._int_from(item, ["level_id", "id"])
            if division_id is None:
                continue
            division = Division(
                id=division_id,
                name=self._str_from(
                    item, ["level_name", "div_name", "name"], f"Division {division_id}"
                ),
                season_id=self.settings.current_season_id,
            )
            divisions.append(division)

        standings_levels = self._extract_standings_levels(standings_raw)
        division_name_map = {division.id: division.name for division in divisions}
        seen_team_ids: set[int] = set()
        for level in standings_levels:
            level_id = self._int_from(level, ["id", "level_id"])
            if level_id is None:
                continue
            level_name = self._str_from(
                level,
                ["name", "level_name"],
                division_name_map.get(level_id, f"Division {level_id}"),
            )
            level_name = division_name_map.get(level_id, self._normalize_division_name(level_name))
            division_name_map.setdefault(level_id, level_name)

            if level_id not in {division.id for division in divisions}:
                divisions.append(
                    Division(
                        id=level_id,
                        name=level_name,
                        season_id=self.settings.current_season_id,
                    )
                )

            for conference in level.get("conferences", []):
                for team_item in conference.get("teams", []):
                    team_id = self._int_from(team_item, ["id", "team_id"])
                    if team_id is None or team_id in seen_team_ids:
                        continue
                    seen_team_ids.add(team_id)
                    teams.append(
                        Team(
                            id=team_id,
                            name=self._clean_name(
                                self._str_from(
                                    team_item,
                                    ["team_name", "name"],
                                    f"Team {team_id}",
                                )
                            ),
                            season_id=self.settings.current_season_id,
                            division_id=level_id,
                            division_name=division_name_map.get(level_id, level_name),
                        )
                    )

        divisions.sort(key=lambda item: (self._division_sort_key(item.name), item.name))
        teams.sort(key=lambda item: (item.division_name or "", item.name))

        return MetaPayload(current_season=season, divisions=divisions, teams=teams)

    def _normalize_current_season(self, leagues_raw: dict[str, Any]) -> Season:
        league = (leagues_raw.get("leagues") or [{}])[0]
        season_id = self._int_from(league, ["current_season"], self.settings.current_season_id)
        label = None
        for item in league.get("seasons", []):
            if self._int_from(item, ["season_id"]) == season_id:
                label = self._str_from(item, ["season_name"])
                break
        return Season(
            id=season_id or self.settings.current_season_id,
            label=label or f"Season {self.settings.current_season_id}",
            is_current=True,
        )

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
        standings: list[StandingRow] = []
        for level in self._extract_standings_levels(raw):
            if self._int_from(level, ["id", "level_id"]) != division_id:
                continue
            for conference in level.get("conferences", []):
                for item in conference.get("teams", []):
                    standings.append(
                        StandingRow(
                            team_id=self._int_from(item, ["id", "team_id"], 0),
                            team_name=self._clean_name(
                                self._str_from(
                                    item,
                                    ["team_name", "name"],
                                    "Unknown Team",
                                )
                            ),
                            division_id=division_id,
                            gp=self._int_from(item, ["games_played", "gp"]),
                            w=self._int_from(item, ["wins", "w"]),
                            l=self._int_from(item, ["losses", "l"]),
                            t=self._int_from(item, ["ties", "t"]),
                            otl=self._int_from(item, ["otlosses", "ot_losses", "otl"]),
                            gf=self._int_from(item, ["goals_for", "gf"]),
                            ga=self._int_from(item, ["goals_against", "ga"]),
                            gd=self._int_from(item, ["plusminus", "goal_diff", "gd"]),
                            pts=self._int_from(item, ["pts", "points"]),
                            streak=self._str_from(item, ["streak"]),
                        )
                    )
        standings.sort(key=lambda item: (-1 * (item.pts or 0), item.team_name))
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
        team_division_map: dict[int, int | None] | None = None,
    ) -> SchedulePayload:
        games = [
            self._normalize_game(item, team_division_map=team_division_map)
            for item in raw.get("games", [])
        ]
        if division_id is not None and team_id is None:
            games = [game for game in games if game.division_id == division_id]
        if view == "upcoming":
            games = [game for game in games if game.status != "final"]
        games.sort(key=lambda item: ((item.date_label or ""), (item.time_label or "")))
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
        current_level = None
        for level in team_raw.get("levels", []):
            if self._int_from(level, ["season_id"]) == self.settings.current_season_id:
                current_level = level
                break
        team = Team(
            id=team_id,
            name=self._clean_name(
                self._str_from(team_item, ["team_name", "name"], f"Team {team_id}")
            ),
            season_id=self.settings.current_season_id,
            division_id=self._int_from(current_level or {}, ["level_id"]),
            division_name=self._normalize_division_name(
                self._str_from(current_level or {}, ["level_name"])
            ),
        )
        roster = [
            RosterPlayer(
                id=self._int_from(item, ["player_id", "id"]),
                name=self._clean_name(
                    self._str_from(item, ["player_name", "name"], "Unknown Player")
                ),
                jersey_number=self._str_from(item, ["jersey", "jersey_number", "number"]),
                position=self._str_from(item, ["position"]),
            )
            for item in roster_raw.get("players", [])
        ]
        games = [self._normalize_game(item) for item in schedule_raw.get("games", [])]
        games.sort(key=lambda item: ((item.date_label or ""), (item.time_label or "")))
        return TeamPageData(team=team, roster=roster, games=games)

    def _normalize_game(
        self,
        item: dict[str, Any],
        team_division_map: dict[int, int | None] | None = None,
    ) -> Game:
        game_id = self._int_from(item, ["game_id", "id"], 0)
        status = self._normalize_status(item)
        site_base = self.settings.tts_site_base.rstrip("/")
        external_scorecard_url = self._str_from(item, ["scoresheet_link"])
        if external_scorecard_url:
            external_scorecard_url = external_scorecard_url.replace("//generate-scorecard.php", "/generate-scorecard.php")
        else:
            external_scorecard_url = f"{site_base}/generate-scorecard.php?game_id={game_id}"
        home_team_id = self._int_from(item, ["home_id", "home_team_id"])
        away_team_id = self._int_from(item, ["away_id", "away_team_id"])
        division_id = self._int_from(item, ["level_id"])
        if division_id is None and team_division_map and home_team_id and away_team_id:
            home_division = team_division_map.get(home_team_id)
            away_division = team_division_map.get(away_team_id)
            if home_division is not None and home_division == away_division:
                division_id = home_division
        return Game(
            id=game_id,
            season_id=self._int_from(item, ["season_id"], self.settings.current_season_id)
            or self.settings.current_season_id,
            division_id=division_id,
            venue=self._str_from(item, ["location", "rink", "venue"]),
            starts_at=self._str_from(item, ["gmt_time"]),
            date_label=self._str_from(item, ["date", "game_date", "date_label"], "TBD"),
            time_label=self._str_from(item, ["formatted_time", "time_label", "game_time", "time"]),
            status=status,
            home_team_id=home_team_id,
            home_team_name=self._clean_name(
                self._str_from(item, ["home_team", "home_team_name", "home"], "Home")
            ),
            away_team_id=away_team_id,
            away_team_name=self._clean_name(
                self._str_from(item, ["away_team", "away_team_name", "away"], "Away")
            ),
            home_score=self._int_from(item, ["home_goals", "home_score"]),
            away_score=self._int_from(item, ["away_goals", "away_score"]),
            external_game_url=f"{site_base}/test/game.php?game={game_id}",
            external_scorecard_url=external_scorecard_url,
        )

    def _normalize_status(self, item: dict[str, Any]) -> str | None:
        raw = self._str_from(item, ["game_status", "status"], "").strip().lower()
        if raw in {"final", "completed", "closed"}:
            return "final"
        if raw in {"live", "in progress"}:
            return "live"
        if raw in {"postponed"}:
            return "postponed"
        if raw in {"not started", "open"}:
            return "scheduled"
        if raw:
            return "scheduled"
        if self._int_from(item, ["home_goals", "home_score"]) is not None or self._int_from(
            item, ["away_goals", "away_score"]
        ) is not None:
            return "final"
        return "scheduled"

    def _extract_standings_levels(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        standings = raw.get("standings")
        if not isinstance(standings, dict):
            return []
        leagues = standings.get("leagues") or []
        if not leagues:
            return []
        first_league = leagues[0]
        return [item for item in first_league.get("levels", []) if isinstance(item, dict)]

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

    def _clean_name(self, value: str | None) -> str:
        return (value or "").strip()

    def _division_sort_key(self, value: str) -> tuple[int, str]:
        digits = "".join(character for character in value if character.isdigit())
        return (int(digits) if digits else 999, value)

    def _normalize_division_name(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if normalized.startswith("Adult "):
            normalized = normalized.removeprefix("Adult ").strip()
        return normalized

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
            StandingRow(team_id=323, team_name="Ice Otters", division_id=division.id, gp=10, w=7, l=2, t=1, otl=0, pts=15, streak="Won 3"),
            StandingRow(team_id=324, team_name="Blue Liners", division_id=division.id, gp=10, w=6, l=3, t=1, otl=0, pts=13, streak="Won 1"),
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
