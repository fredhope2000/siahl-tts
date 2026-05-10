from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_page_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "League info that gets out of the way." in response.text


def test_api_meta_renders() -> None:
    response = client.get("/api/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["current_season"]["id"] == 74
