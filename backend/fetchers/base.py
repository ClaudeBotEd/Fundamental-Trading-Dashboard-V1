import httpx
from abc import ABC, abstractmethod


class BaseFetcher(ABC):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)

    @abstractmethod
    async def fetch(self) -> list[str]:
        """Return list of markdown snippet strings for Claude context."""
        ...
