import time
from threading import Lock
from core.models import BiasResult


class ResultCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[str, str], tuple[BiasResult, float]] = {}
        self._lock = Lock()

    def get(self, pair: str, horizon: str) -> BiasResult | None:
        with self._lock:
            entry = self._store.get((pair, horizon))
            if entry is None:
                return None
            result, stored_at = entry
            if time.time() - stored_at > self._ttl:
                del self._store[(pair, horizon)]
                return None
            return result

    def set(self, result: BiasResult) -> None:
        with self._lock:
            self._store[(result.pair, result.horizon.value)] = (result, time.time())

    def all(self) -> list[BiasResult]:
        now = time.time()
        with self._lock:
            return [
                r for (r, stored_at) in self._store.values()
                if now - stored_at <= self._ttl
            ]
