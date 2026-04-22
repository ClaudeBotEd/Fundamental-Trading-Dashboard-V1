import httpx
from fetchers.base import BaseFetcher

_BASE = "https://api.stlouisfed.org/fred/series/observations"

_SERIES = {
    "DGS10":    ("US 10Y Treasury Yield",          "%", 5),
    "DFII10":   ("US 10Y Real Yield (TIPS)",        "%", 5),
    "FEDFUNDS": ("Fed Funds Rate",                  "%", 2),
    "DTWEXBGS": ("USD Nominal Broad Index",         "",  5),
    "CPIAUCSL": ("CPI All Urban Consumers",         "",  13),  # 13 for YoY
    "UNRATE":   ("Unemployment Rate",              "%", 2),
}


class FREDFetcher(BaseFetcher):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        snippets = []
        for series_id, (label, unit, limit) in _SERIES.items():
            params = {
                "series_id": series_id,
                "api_key": self._api_key,
                "limit": limit,
                "sort_order": "desc",
                "file_type": "json",
            }
            resp = await self._client.get(_BASE, params=params)
            resp.raise_for_status()
            obs = [o for o in resp.json()["observations"] if o["value"] != "."]
            if not obs:
                continue
            snippets.append(self._format(series_id, label, unit, obs))
        return snippets

    @staticmethod
    def _format(series_id: str, label: str, unit: str, obs: list[dict]) -> str:
        current = float(obs[0]["value"])
        lines = [f"## {label}", f"- Current: {current}{unit}"]
        if len(obs) >= 2:
            prev1d = float(obs[1]["value"])
            lines.append(f"- Change 1d: {current - prev1d:+.2f}{unit}")
        if len(obs) >= 5:
            prev5d = float(obs[4]["value"])
            lines.append(f"- Change 5d: {current - prev5d:+.2f}{unit}")
        if series_id == "CPIAUCSL" and len(obs) >= 13:
            yoy_base = float(obs[12]["value"])
            yoy = (current - yoy_base) / yoy_base * 100
            lines.append(f"- YoY: {yoy:.1f}%")
        return "\n".join(lines)
