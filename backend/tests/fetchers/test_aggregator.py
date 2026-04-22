import pytest
from fetchers.aggregator import ContextAggregator


class FakeSecret:
    def __init__(self, v: str):
        self._v = v
    def get_secret_value(self) -> str:
        return self._v


class FakeSettings:
    fred_api_key          = FakeSecret("fred_key")
    fmp_api_key           = FakeSecret("")
    alpha_vantage_api_key = FakeSecret("")
    coingecko_api_key     = FakeSecret("")


@pytest.mark.asyncio
async def test_aggregator_unknown_pair_raises():
    agg = ContextAggregator(FakeSettings())
    with pytest.raises(ValueError, match="Unknown pair"):
        await agg.fetch_for_pair("XXX/YYY")


@pytest.mark.asyncio
async def test_aggregator_xauusd_calls_fred_and_cftc(monkeypatch):
    from unittest.mock import AsyncMock
    agg = ContextAggregator(FakeSettings())

    monkeypatch.setattr(agg._fetchers["XAU/USD"]["fred"],          "fetch", AsyncMock(return_value=["## US 10Y\n- Current: 4.32%"]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["cftc"],          "fetch", AsyncMock(return_value=["## COT Gold\n- Net: +140,000"]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["fear_greed"],    "fetch", AsyncMock(return_value=["## Fear\n- Value: 72"]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["fmp"],           "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["alpha_vantage"], "fetch", AsyncMock(return_value=[]))

    context = await agg.fetch_for_pair("XAU/USD")
    assert "US 10Y" in context
    assert "COT Gold" in context
    assert "Fear" in context


@pytest.mark.asyncio
async def test_aggregator_btcusd_calls_coingecko_and_fear(monkeypatch):
    from unittest.mock import AsyncMock
    agg = ContextAggregator(FakeSettings())

    monkeypatch.setattr(agg._fetchers["BTC/USD"]["coingecko"],  "fetch", AsyncMock(return_value=["## BTC/USD\n- Price: $68,500"]))
    monkeypatch.setattr(agg._fetchers["BTC/USD"]["fear_greed"], "fetch", AsyncMock(return_value=["## Fear\n- Value: 72"]))
    monkeypatch.setattr(agg._fetchers["BTC/USD"]["fred"],       "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["BTC/USD"]["fmp"],        "fetch", AsyncMock(return_value=[]))

    context = await agg.fetch_for_pair("BTC/USD")
    assert "BTC/USD" in context
    assert "Fear" in context


@pytest.mark.asyncio
async def test_aggregator_eurusd_includes_ecb(monkeypatch):
    from unittest.mock import AsyncMock
    agg = ContextAggregator(FakeSettings())

    monkeypatch.setattr(agg._fetchers["EUR/USD"]["ecb"],           "fetch", AsyncMock(return_value=["## ECB Deposit\n- Current: 4.0%"]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["fred"],          "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["cftc"],          "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["fmp"],           "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["alpha_vantage"], "fetch", AsyncMock(return_value=[]))

    context = await agg.fetch_for_pair("EUR/USD")
    assert "ECB Deposit" in context
