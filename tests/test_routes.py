from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import StandingRow
from app.routes.pages import templates


client = TestClient(app)


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Recent Games" in response.text
    assert "Season 77" in response.text


def test_locker_rooms_page_renders() -> None:
    response = client.get("/locker-rooms")
    assert response.status_code == 200
    assert "Locker Room Assignments" in response.text
    assert "Ice Otters" in response.text
    assert "B4" in response.text


def test_api_meta_renders() -> None:
    response = client.get("/api/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_season"]["id"] == 77


def test_standings_page_can_select_a_past_season() -> None:
    response = client.get("/standings?season=74")

    assert response.status_code == 200
    assert '<option value="74" selected>' in response.text
    assert "Summer 2026" in response.text
    assert "Ice Otters" in response.text


def test_standings_table_uses_dashes_for_missing_streak_and_tiebreaker() -> None:
    rendered = templates.get_template("partials/standings_table.html").render(
        standings=[
            StandingRow(
                team_id=1,
                team_name="New Team",
                division_id=1,
                gp=0,
                w=0,
                l=0,
                t=0,
                otl=0,
                pts=0,
            )
        ]
    )

    assert rendered.count("<td>-</td>") == 2
