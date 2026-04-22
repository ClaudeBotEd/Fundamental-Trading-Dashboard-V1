import pytest
from unittest.mock import MagicMock
from fetchers.coingecko import CoinGeckoFetcher

_FIXTURE = {
    "bitcoin":  {"usd": 68500.0, "usd_24h_change": 2.34,  "usd_market_cap": 1350000000000},
    "ethereum": {"usd": 3420.0,  "usd_24h_change": -0.87, "usd_market_cap": 411000000000},
}


def _mock_client(data: dict) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_coingecko_returns_two_snippets():
    client = _mock_client(_FIXTURE)
    fetcher = CoinGeckoFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 2


@pytest.mark.asyncio
async def test_coingecko_btc_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = CoinGeckoFetcher(client=client)
    snippets = await fetcher.fetch()
    btc = next(s for s in snippets if "BTC" in s)
    assert "68,500" in btc or "68500" in btc
    assert "+2.34%" in btc


@pytest.mark.asyncio
async def test_coingecko_eth_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = CoinGeckoFetcher(client=client)
    snippets = await fetcher.fetch()
    eth = next(s for s in snippets if "ETH" in s)
    assert "3,420" in eth or "3420" in eth
    assert "-0.87%" in eth
