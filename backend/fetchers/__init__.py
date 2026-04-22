from fetchers.fred import FREDFetcher
from fetchers.ecb import ECBFetcher
from fetchers.boe import BoEFetcher
from fetchers.coingecko import CoinGeckoFetcher
from fetchers.fear_greed import FearGreedFetcher
from fetchers.cftc import CftcFetcher
from fetchers.fmp import FMPFetcher
from fetchers.alpha_vantage import AlphaVantageFetcher
from fetchers.aggregator import ContextAggregator

__all__ = [
    "FREDFetcher",
    "ECBFetcher",
    "BoEFetcher",
    "CoinGeckoFetcher",
    "FearGreedFetcher",
    "CftcFetcher",
    "FMPFetcher",
    "AlphaVantageFetcher",
    "ContextAggregator",
]
