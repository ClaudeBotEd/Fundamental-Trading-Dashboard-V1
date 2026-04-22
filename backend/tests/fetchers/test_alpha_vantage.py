import pytest
from unittest.mock import MagicMock
from fetchers.alpha_vantage import AlphaVantageFetcher

_FIXTURE = {
    "feed": [
        {"title": "Gold rallies on dollar weakness",  "source": "Reuters",   "time_published": "20260422T080000", "overall_sentiment_label": "Bullish", "overall_sentiment_score": "0.35"},
        {"title": "Fed holds rates, dollar steady",   "source": "Bloomberg", "time_published": "20260422T075000", "overall_sentiment_label": "Neutral",  "overall_sentiment_score": "0.05"},
        {"title": "EUR/USD breaks key resistance",    "source": "FXStreet",  "time_published": "20260422T074000", "overall_sentiment_label": "Bullish",  "overall_sentiment_score": "0.28"},
    ]
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
async def test_alphavantage_empty_when_no_key():
    client = _mock_client(_FIXTURE)
    fetcher = AlphaVantageFetcher(api_key="", client=client)
    snippets = await fetcher.fetch()
    assert snippets == []


@pytest.mark.asyncio
async def test_alphavantage_returns_one_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = AlphaVantageFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_alphavantage_snippet_contains_headlines():
    client = _mock_client(_FIXTURE)
    fetcher = AlphaVantageFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    assert "Gold rallies" in snippets[0]
    assert "Bullish" in snippets[0]
