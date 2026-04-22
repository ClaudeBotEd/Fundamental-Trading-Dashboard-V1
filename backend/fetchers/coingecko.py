import httpx
from fetchers.base import BaseFetcher

_URL = "https://api.coingecko.com/api/v3/simple/price"
_COINS = {"bitcoin": "BTC", "ethereum": "ETH"}


class CoinGeckoFetcher(BaseFetcher):
    def __init__(self, api_key: str = "", client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        params: dict = {
            "ids": ",".join(_COINS.keys()),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        }
        if self._api_key:
            params["x_cg_pro_api_key"] = self._api_key
        resp = await self._client.get(_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return [
            self._format(ticker, data[coin_id])
            for coin_id, ticker in _COINS.items()
            if coin_id in data
        ]

    @staticmethod
    def _format(ticker: str, d: dict) -> str:
        price = d.get("usd", 0)
        change = d.get("usd_24h_change", 0)
        mcap = d.get("usd_market_cap", 0)
        sign = "+" if change >= 0 else ""
        return "\n".join([
            f"## {ticker}/USD (CoinGecko)",
            f"- Price: ${price:,.0f}",
            f"- 24h Change: {sign}{change:.2f}%",
            f"- Market Cap: ${mcap / 1e9:.1f}B",
        ])
