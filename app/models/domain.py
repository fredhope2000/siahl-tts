from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Season(BaseModel):
    id: int
    label: str
    is_current: bool = True


class Division(BaseModel):
    id: int
    name: str
    season_id: int


class Team(BaseModel):
    id: int
    name: str
    season_id: int
    division_id: int | None = None
    division_name: str | None = None


class StandingRow(BaseModel):
    team_id: int
    team_name: str
    division_id: int | None = None
    gp: int | None = None
    w: int | None = None
    l: int | None = None
    t: int | None = None
    otl: int | None = None
    gf: int | None = None
    ga: int | None = None
    gd: int | None = None
    pts: int | None = None
    streak: str | None = None


class RosterPlayer(BaseModel):
    id: int | None = None
    name: str
    jersey_number: str | None = None
    position: str | None = None


class Game(BaseModel):
    id: int
    season_id: int
    division_id: int | None = None
    venue: str | None = None
    starts_at: str | None = None
    date_label: str | None = None
    time_label: str | None = None
    status: Literal["scheduled", "live", "final", "postponed"] | None = None
    home_team_id: int | None = None
    home_team_name: str
    away_team_id: int | None = None
    away_team_name: str
    home_score: int | None = None
    away_score: int | None = None
    external_game_url: str | None = None
    external_scorecard_url: str | None = None


class MetaPayload(BaseModel):
    current_season: Season
    divisions: list[Division]
    teams: list[Team]


class StandingsPayload(BaseModel):
    season_id: int
    division: Division
    standings: list[StandingRow]


class ScheduleFilters(BaseModel):
    division: int | None = None
    team: int | None = None
    view: Literal["upcoming", "all"] = "upcoming"


class SchedulePayload(BaseModel):
    season_id: int
    filters: ScheduleFilters
    games: list[Game]


class TeamPageData(BaseModel):
    team: Team
    roster: list[RosterPlayer]
    games: list[Game]
