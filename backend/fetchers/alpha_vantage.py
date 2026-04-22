import httpx
from fetchers.base import BaseFetcher

_URL = "https://www.alphavantage.co/query"
_TICKERS = "FOREX:EURUSD,FOREX:GBPUSD,FOREX:USDJPY,COMMODITY:XAU,CRYPTO:BTC,CRYPTO:ETH"


class AlphaVantageFetcher(BaseFetcher):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        if not self._api_key:
            return []
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": _TICKERS,
            "sort": "LATEST",
            "limit": 20,
            "apikey": self._api_key,
        }
        resp = await self._client.get(_URL, params=params)
        resp.raise_for_status()
        feed = resp.json().get("feed", [])
        if not feed:
            return []
        lines = ["## News Sentiment (Alpha Vantage)"]
        for item in feed[:10]:
            date_str = item.get("time_published", "")[:8]
            title = item.get("title", "")
            source = item.get("source", "")
            sentiment = item.get("overall_sentiment_label", "Neutral")
            score = float(item.get("overall_sentiment_score", 0))
            lines.append(f"- [{date_str}] [{sentiment} {score:+.2f}] {title} ({source})")
        return ["\n".join(lines)]
