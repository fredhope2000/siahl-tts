import pytest

from app.services.cache import TTLCache


@pytest.mark.anyio
async def test_refresh_keeps_existing_value_when_loader_fails() -> None:
    cache = TTLCache()
    cache.set("hot-key", "old", 60)

    async def failing_loader() -> str:
        raise RuntimeError("upstream failed")

    with pytest.raises(RuntimeError):
        await cache.refresh("hot-key", 60, failing_loader)

    assert cache.get("hot-key") == "old"
