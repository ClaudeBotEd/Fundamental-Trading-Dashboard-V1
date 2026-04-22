import datetime
import httpx
from fetchers.base import BaseFetcher

_BASE = "https://financialmodelingprep.com/api"


class FMPFetcher(BaseFetcher):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        if not self._api_key:
            return []
        snippets = []
        cal = await self._fetch_calendar()
        if cal:
            snippets.append(cal)
        news = await self._fetch_news()
        if news:
            snippets.append(news)
        return snippets

    async def _fetch_calendar(self) -> str:
        today = datetime.date.today()
        params = {
            "from": today.isoformat(),
            "to": (today + datetime.timedelta(days=7)).isoformat(),
            "apikey": self._api_key,
        }
        resp = await self._client.get(f"{_BASE}/v3/economic_calendar", params=params)
        resp.raise_for_status()
        events = [e for e in resp.json() if (e.get("impact") or "").lower() == "high"]
        if not events:
            return ""
        lines = ["## Economic Calendar (High Impact, Next 7 Days)"]
        for e in events[:10]:
            date_str = e.get("date", "")[:10]
            country = e.get("country", "")
            name = e.get("event", "")
            prev = e.get("previous") or "—"
            est = e.get("estimate") or "—"
            lines.append(f"- [{date_str}] {country} — {name} | prev: {prev} | est: {est}")
        return "\n".join(lines)

    async def _fetch_news(self) -> str:
        resp = await self._client.get(f"{_BASE}/v4/general_news", params={"page": 0, "apikey": self._api_key})
        resp.raise_for_status()
        articles = resp.json()[:10]
        if not articles:
            return ""
        lines = ["## Recent Market News (FMP)"]
        for a in articles:
            date_str = a.get("publishedDate", "")[:10]
            title = a.get("title", "")
            site = a.get("site", "")
            lines.append(f"- [{date_str}] {title} ({site})")
        return "\n".join(lines)
