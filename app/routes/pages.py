from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


def _format_refresh_timestamp(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    dt = datetime.fromtimestamp(timestamp, ZoneInfo("America/Los_Angeles"))
    return dt.strftime("%b %-d, %Y %-I:%M %p PT")


def _redirect_without_refresh(request: Request) -> RedirectResponse:
    kept_items = [
        (key, value)
        for key, value in request.query_params.multi_items()
        if key != "refresh"
    ]
    url = str(request.url.replace(query=""))
    if kept_items:
        query = "&".join(f"{key}={value}" for key, value in kept_items)
        url = f"{url}?{query}"
    return RedirectResponse(url=url, status_code=303)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    service = request.app.state.tts_service
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    start_date = today - timedelta(days=2)
    meta, schedule = await asyncio.gather(
        service.get_meta(),
        service.get_schedule(view="all"),
    )
    teams = sorted(meta.teams, key=lambda team_item: team_item.name.lower())
    recent_games = [
        game
        for game in schedule.games
        if game.date_label
        and start_date.isoformat() <= game.date_label <= today.isoformat()
    ]
    recent_games = await service.apply_locker_rooms(recent_games)
    recent_games_grouped = [
        (date_label, list(reversed(grouped_games)))
        for date_label, grouped_games in reversed(service.group_games_by_date(recent_games))
    ]
    context = _base_context(request) | {
        "page_title": "Home",
        "current_season": meta.current_season,
        "divisions": meta.divisions,
        "teams": teams,
        "games_grouped": recent_games_grouped,
    }
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/standings", response_class=HTMLResponse)
async def standings(
    request: Request,
    division: str | None = Query(default=None),
    refresh: int | None = Query(default=None),
):
    service = request.app.state.tts_service
    if refresh:
        if (division or "all") == "all":
            await service.refresh_all_standings()
        else:
            await service.refresh_standings(int(division or "0"))
        return _redirect_without_refresh(request)
    meta = await service.get_meta()
    selected_division = division or "all"
    standings_payload = None
    all_standings = []
    if selected_division == "all":
        all_standings = await service.get_all_standings()
        refreshed_at = service.last_refreshed_at("standings:all")
    else:
        division_id = int(selected_division)
        standings_payload = await service.get_standings(division_id)
        refreshed_at = service.last_refreshed_at(f"standings:{division_id}")
    context = _base_context(request) | {
        "page_title": "Standings",
        "current_season": meta.current_season,
        "divisions": meta.divisions,
        "selected_division": selected_division,
        "standings_payload": standings_payload,
        "all_standings": all_standings,
        "last_refreshed_at": _format_refresh_timestamp(refreshed_at),
    }
    return templates.TemplateResponse(request, "standings.html", context)


@router.get("/schedule", response_class=HTMLResponse)
async def schedule(
    request: Request,
    division: list[str] | None = Query(default=None),
    team: list[str] | None = Query(default=None),
    view: str = Query(default="upcoming", pattern="^(upcoming|last-3|to-date|all)$"),
    order: str = Query(default="oldest", pattern="^(oldest|newest)$"),
    refresh: int | None = Query(default=None),
):
    service = request.app.state.tts_service
    if refresh:
        await service.refresh_schedule(view="all")
        return _redirect_without_refresh(request)
    today_iso = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
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
        "selected_order": order,
        "today_iso": today_iso,
        "games_grouped": service.group_games_by_date(schedule_payload.games),
        "last_refreshed_at": _format_refresh_timestamp(
            service.last_refreshed_at("schedule:None:None:all")
        ),
    }
    return templates.TemplateResponse(request, "schedule.html", context)


@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def team_page(
    request: Request,
    team_id: int,
    view: str = Query(default="all", pattern="^(upcoming|last-3|to-date|all)$"),
    order: str = Query(default="oldest", pattern="^(oldest|newest)$"),
    refresh: int | None = Query(default=None),
):
    service = request.app.state.tts_service
    if refresh:
        await service.refresh_team_page(team_id)
        return _redirect_without_refresh(request)
    today_iso = datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
    team_data = await service.get_team_page(team_id)
    games_with_lockers = await service.apply_locker_rooms(team_data.games)
    gameday_games = [
        game.model_copy(update={"date_label": "TODAY"})
        for game in games_with_lockers
        if game.date_label == today_iso
    ]
    context = _base_context(request) | {
        "page_title": team_data.team.name,
        "team": team_data.team,
        "roster": team_data.roster,
        "selected_view": view,
        "selected_order": order,
        "today_iso": today_iso,
        "gameday_games": gameday_games,
        "gameday_games_grouped": service.group_games_by_date(gameday_games),
        "games_grouped": service.group_games_by_date(games_with_lockers),
        "last_refreshed_at": _format_refresh_timestamp(
            service.last_refreshed_at(f"team:{team_id}")
        ),
    }
    return templates.TemplateResponse(request, "team.html", context)
