from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Recent Games" in response.text
    assert "Season 74" in response.text


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
    assert payload["current_season"]["id"] == 74
