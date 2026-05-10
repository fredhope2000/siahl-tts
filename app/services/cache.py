from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheItem:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheItem] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None:
            return None
        if item.expires_at < time.time():
            self._items.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> Any:
        self._items[key] = CacheItem(value=value, expires_at=time.time() + ttl_seconds)
        return value

    async def get_or_set(
        self, key: str, ttl_seconds: int, loader: Callable[[], Awaitable[Any]]
    ) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = await loader()
        return self.set(key, value, ttl_seconds)
