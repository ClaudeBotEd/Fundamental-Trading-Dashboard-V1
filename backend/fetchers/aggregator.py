import asyncio
import httpx
from fetchers.fred import FREDFetcher
from fetchers.ecb import ECBFetcher
from fetchers.boe import BoEFetcher
from fetchers.coingecko import CoinGeckoFetcher
from fetchers.fear_greed import FearGreedFetcher
from fetchers.cftc import CftcFetcher
from fetchers.fmp import FMPFetcher
from fetchers.alpha_vantage import AlphaVantageFetcher


class ContextAggregator:
    def __init__(self, settings) -> None:
        client = httpx.AsyncClient(timeout=30.0)
        fred         = FREDFetcher(api_key=settings.fred_api_key.get_secret_value(), client=client)
        ecb          = ECBFetcher(client=client)
        boe          = BoEFetcher(client=client)
        coingecko    = CoinGeckoFetcher(api_key=settings.coingecko_api_key.get_secret_value(), client=client)
        fear_greed   = FearGreedFetcher(client=client)
        cftc         = CftcFetcher(client=client)
        fmp          = FMPFetcher(api_key=settings.fmp_api_key.get_secret_value(), client=client)
        alpha_vantage = AlphaVantageFetcher(api_key=settings.alpha_vantage_api_key.get_secret_value(), client=client)

        # Fetcher instances are shared across pairs — one HTTP client, no duplicate calls.
        self._fetchers: dict[str, dict] = {
            "XAU/USD": {"fred": fred, "cftc": cftc, "fear_greed": fear_greed, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "EUR/USD": {"fred": fred, "ecb": ecb, "cftc": cftc, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "GBP/USD": {"fred": fred, "boe": boe, "cftc": cftc, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "USD/JPY": {"fred": fred, "cftc": cftc, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "AUD/USD": {"fred": fred, "coingecko": coingecko, "cftc": cftc, "fmp": fmp},
            "USD/CAD": {"fred": fred, "cftc": cftc, "fmp": fmp},
            "USD/CHF": {"fred": fred, "cftc": cftc, "fmp": fmp},
            "NZD/USD": {"fred": fred, "cftc": cftc, "fmp": fmp},
            "BTC/USD": {"coingecko": coingecko, "fear_greed": fear_greed, "fred": fred, "fmp": fmp},
            "ETH/USD": {"coingecko": coingecko, "fear_greed": fear_greed, "fmp": fmp},
        }

    async def fetch_for_pair(self, pair: str) -> str:
        if pair not in self._fetchers:
            raise ValueError(f"Unknown pair: {pair}. Valid: {list(self._fetchers.keys())}")
        results = await asyncio.gather(
            *[f.fetch() for f in self._fetchers[pair].values()],
            return_exceptions=True,
        )
        snippets: list[str] = []
        for r in results:
            if isinstance(r, list):
                snippets.extend(r)
        return "\n\n".join(snippets)
