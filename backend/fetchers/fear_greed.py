import httpx
from fetchers.base import BaseFetcher

_URL = "https://api.alternative.me/fng/"


class FearGreedFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        resp = await self._client.get(_URL, params={"limit": 1})
        resp.raise_for_status()
        data = resp.json()
        try:
            entry = data["data"][0]
            value = int(entry["value"])
            classification = entry["value_classification"]
        except (KeyError, IndexError, ValueError):
            return []
        signal = "RISK-ON" if value >= 55 else "RISK-OFF" if value <= 45 else "NEUTRAL"
        return ["\n".join([
            "## Crypto Fear & Greed Index",
            f"- Value: {value}/100",
            f"- Classification: {classification}",
            f"- Signal: {signal}",
        ])]
