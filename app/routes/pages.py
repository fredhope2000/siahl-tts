from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.domain import Division


router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


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
    meta = await service.get_meta()
    schedule = await service.get_schedule(view="upcoming")
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
    division: int | None = Query(default=None),
):
    service = request.app.state.tts_service
    meta = await service.get_meta()
    selected_division = division or (meta.divisions[0].id if meta.divisions else None)
    standings_payload = (
        await service.get_standings(selected_division)
        if selected_division is not None
        else None
    )
    context = _base_context(request) | {
        "page_title": "Standings",
        "current_season": meta.current_season,
        "divisions": meta.divisions,
        "selected_division": selected_division,
        "standings_payload": standings_payload,
    }
    return templates.TemplateResponse(request, "standings.html", context)


@router.get("/schedule", response_class=HTMLResponse)
async def schedule(
    request: Request,
    division: int | None = Query(default=None),
    team: int | None = Query(default=None),
    view: str = Query(default="upcoming", pattern="^(upcoming|all)$"),
):
    service = request.app.state.tts_service
    meta = await service.get_meta()
    schedule_payload = await service.get_schedule(
        division_id=division, team_id=team, view=view
    )
    filtered_teams = meta.teams
    if division is not None:
        filtered_teams = [team_item for team_item in meta.teams if team_item.division_id == division]
    context = _base_context(request) | {
        "page_title": "Schedule",
        "current_season": meta.current_season,
        "divisions": meta.divisions,
        "teams": filtered_teams,
        "selected_division": division,
        "selected_team": team,
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
