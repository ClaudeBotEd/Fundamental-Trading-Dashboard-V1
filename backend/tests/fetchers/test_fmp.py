import pytest
from unittest.mock import MagicMock
from fetchers.fmp import FMPFetcher

_CALENDAR = [
    {"date": "2026-04-23 12:30:00", "country": "US", "event": "Initial Jobless Claims",    "impact": "High",   "previous": "215K", "estimate": "210K", "actual": None},
    {"date": "2026-04-24 14:00:00", "country": "US", "event": "Core PCE Price Index m/m",  "impact": "High",   "previous": "0.3%", "estimate": "0.3%", "actual": None},
    {"date": "2026-04-23 10:00:00", "country": "EU", "event": "Flash Manufacturing PMI",   "impact": "Medium", "previous": "46.5", "estimate": "47.0", "actual": None},
]
_NEWS = [
    {"title": "Fed holds rates steady amid inflation concerns", "publishedDate": "2026-04-22 08:00:00", "site": "Reuters",   "url": "https://reuters.com/1"},
    {"title": "ECB signals possible June cut",                  "publishedDate": "2026-04-22 07:30:00", "site": "Bloomberg", "url": "https://bloomberg.com/2"},
]


def _mock_client(calendar: list, news: list) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = calendar if "economic_calendar" in url else news
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_fmp_returns_empty_when_no_key():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="", client=client)
    snippets = await fetcher.fetch()
    assert snippets == []


@pytest.mark.asyncio
async def test_fmp_returns_calendar_snippet():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    cal = next(s for s in snippets if "Economic Calendar" in s)
    assert "Jobless Claims" in cal
    assert "Core PCE" in cal


@pytest.mark.asyncio
async def test_fmp_high_impact_only_in_calendar():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    cal = next(s for s in snippets if "Economic Calendar" in s)
    assert "Flash Manufacturing PMI" not in cal


@pytest.mark.asyncio
async def test_fmp_news_snippet():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    news = next(s for s in snippets if "News" in s)
    assert "Fed holds rates" in news
    assert "ECB signals" in news
