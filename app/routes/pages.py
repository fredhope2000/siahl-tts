from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


def _optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_int_list(values: list[str] | None) -> list[int]:
    return [int(value) for value in (values or []) if value != ""]


def _base_context(request: Request) -> dict:
    service = request.app.state.tts_service
    settings = request.app.state.settings
    return {
        "request": request,
        "app_name": settings.app_name,
        "uses_mock_data": service.uses_mock_data,
    }


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    service = request.app.state.tts_service
    meta, schedule = await asyncio.gather(
        service.get_meta(),
        service.get_schedule(view="upcoming"),
    )
    context = _base_context(request) | {
        "page_title": "Home",
        "current_season": meta.current_season,
        "divisions": meta.divisions,
        "teams": meta.teams,
        "games_grouped": service.group_games_by_date(schedule.games),
    }
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/standings", response_class=HTMLResponse)
async def standings(
    request: Request,
    division: str | None = Query(default=None),
):
    service = request.app.state.tts_service
    meta = await service.get_meta()
    selected_division = division or "all"
    standings_payload = None
    all_standings = []
    if selected_division == "all":
        all_standings = await service.get_all_standings()
    else:
        standings_payload = await service.get_standings(int(selected_division))
    context = _base_context(request) | {
        "page_title": "Standings",
        "current_season": meta.current_season,
        "divisions": meta.divisions,
        "selected_division": selected_division,
        "standings_payload": standings_payload,
        "all_standings": all_standings,
    }
    return templates.TemplateResponse(request, "standings.html", context)


@router.get("/schedule", response_class=HTMLResponse)
async def schedule(
    request: Request,
    division: list[str] | None = Query(default=None),
    team: list[str] | None = Query(default=None),
    view: str = Query(default="upcoming", pattern="^(upcoming|to-date|all)$"),
):
    service = request.app.state.tts_service
    meta, schedule_payload = await asyncio.gather(
        service.get_meta(),
        service.get_schedule(view="all"),
    )
    selected_divisions = _optional_int_list(division)
    selected_teams = _optional_int_list(team)

    teams = sorted(meta.teams, key=lambda team_item: team_item.name.lower())
    context = _base_context(request) | {
        "page_title": "Schedule",
        "current_season": meta.current_season,
        "divisions": meta.divisions,
        "teams": teams,
        "selected_divisions": selected_divisions,
        "selected_teams": selected_teams,
        "selected_view": view,
        "games_grouped": service.group_games_by_date(schedule_payload.games),
    }
    return templates.TemplateResponse(request, "schedule.html", context)


@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_page(request: Request, team_id: int):
    service = request.app.state.tts_service
    team_data = await service.get_team_page(team_id)
    context = _base_context(request) | {
        "page_title": team_data.team.name,
        "team": team_data.team,
        "roster": team_data.roster,
        "games_grouped": service.group_games_by_date(team_data.games),
    }
    return templates.TemplateResponse(request, "team.html", context)
