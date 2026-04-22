import httpx
from fetchers.base import BaseFetcher

_BASE = "https://data-api.ecb.europa.eu/service/data"
_DEPOSIT_RATE_KEY = "FM/M.U2.EUR.IR.MR.LEV"
_HICP_KEY = "ICP/M.U2.N.000000.4.ANR"


class ECBFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        snippets = [
            await self._fetch_series(_DEPOSIT_RATE_KEY, "ECB Deposit Facility Rate", "%"),
            await self._fetch_series(_HICP_KEY, "Eurozone HICP Inflation", "%"),
        ]
        return [s for s in snippets if s]

    async def _fetch_series(self, key: str, label: str, unit: str) -> str:
        url = f"{_BASE}/{key}"
        params = {"format": "jsondata", "lastNObservations": 2}
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        try:
            series = data["dataSets"][0]["series"]["0:0:0:0:0"]["observations"]
            values = [series[k][0] for k in sorted(series.keys(), key=int)]
        except (KeyError, IndexError):
            return ""
        if not values:
            return ""
        current = values[-1]
        lines = [f"## {label}", f"- Current: {current}{unit}"]
        if len(values) >= 2:
            lines.append(f"- Previous: {values[-2]}{unit}")
        return "\n".join(lines)
