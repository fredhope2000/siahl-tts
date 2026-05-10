from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request


router = APIRouter(prefix="/api", tags=["api"])


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
    division: int | None = Query(default=None),
    team: int | None = Query(default=None),
    view: str = Query(default="upcoming", pattern="^(upcoming|all)$"),
):
    service = request.app.state.tts_service
    return await service.get_schedule(division_id=division, team_id=team, view=view)


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
