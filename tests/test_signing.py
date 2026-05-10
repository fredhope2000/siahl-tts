from app.services.tts_signing import EMPTY_BODY_MD5, build_signed_query


def test_signing_includes_expected_fields() -> None:
    query = build_signed_query(
        endpoint="get_schedule",
        api_key="web",
        api_secret="secret",
        params={"league_id": 1, "season_id": 74},
        timestamp=1700000000,
    )
    assert "auth_key=web" in query
    assert f"body_md5={EMPTY_BODY_MD5}" in query
    assert "league_id=1" in query
    assert "season_id=74" in query
    assert "auth_signature=" in query
