from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request


router = APIRouter(prefix="/api", tags=["api"])


def _optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_int_list(values: list[str] | None) -> list[int]:
    return [int(value) for value in (values or []) if value != ""]


@router.get("/meta")
async def meta(request: Request):
    service = request.app.state.tts_service
    return await service.get_meta()


@router.get("/standings")
async def standings(
    request: Request,
    division: int = Query(..., description="Division ID (upstream level_id)"),
):
    service = request.app.state.tts_service
    return await service.get_standings(division)


@router.get("/schedule")
async def schedule(
    request: Request,
    division: list[str] | None = Query(default=None),
    team: list[str] | None = Query(default=None),
    view: str = Query(default="upcoming", pattern="^(upcoming|to-date|all)$"),
):
    service = request.app.state.tts_service
    meta = await service.get_meta()
    payload = await service.get_schedule(view="all")
    selected_divisions = set(_optional_int_list(division))
    selected_teams = set(_optional_int_list(team))
    team_division_map = {team_item.id: team_item.division_id for team_item in meta.teams}
    games = payload.games

    if selected_divisions:
        games = [
            game
            for game in games
            if (
                game.division_id in selected_divisions
                or team_division_map.get(game.home_team_id or -1) in selected_divisions
                or team_division_map.get(game.away_team_id or -1) in selected_divisions
            )
        ]
    if selected_teams:
        games = [
            game
            for game in games
            if game.home_team_id in selected_teams or game.away_team_id in selected_teams
        ]
    today = date.today()
    if view == "upcoming":
        games = [game for game in games if not game.date_label or game.date_label >= today.isoformat()]
    elif view == "to-date":
        games = [game for game in games if not game.date_label or game.date_label <= today.isoformat()]

    return {
        "season_id": payload.season_id,
        "filters": {
            "division": sorted(selected_divisions),
            "team": sorted(selected_teams),
            "view": view,
        },
        "games": games,
    }


@router.get("/team/{team_id}")
async def team(request: Request, team_id: int):
    service = request.app.state.tts_service
    try:
        return await service.get_team_page(team_id)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Team not found") from exc


@router.get("/team/{team_id}/roster")
async def team_roster(request: Request, team_id: int):
    team_data = await request.app.state.tts_service.get_team_page(team_id)
    return {"team_id": team_id, "season_id": team_data.team.season_id, "roster": team_data.roster}


@router.get("/team/{team_id}/schedule")
async def team_schedule(request: Request, team_id: int):
    team_data = await request.app.state.tts_service.get_team_page(team_id)
    return {"team_id": team_id, "season_id": team_data.team.season_id, "games": team_data.games}
