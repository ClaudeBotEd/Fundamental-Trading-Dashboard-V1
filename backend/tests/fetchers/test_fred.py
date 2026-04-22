import pytest
from unittest.mock import MagicMock
from fetchers.fred import FREDFetcher


def _mock_client(json_by_series: dict[str, dict]) -> MagicMock:
    """Return a mock AsyncClient whose .get() returns different JSON per series_id."""
    client = MagicMock()

    async def fake_get(url: str, params: dict | None = None, **kwargs):
        series_id = (params or {}).get("series_id", "")
        data = json_by_series.get(series_id, {"observations": []})
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client.get = fake_get
    return client


FRED_FIXTURES = {
    "DGS10": {"observations": [
        {"date": "2026-04-21", "value": "4.32"},
        {"date": "2026-04-18", "value": "4.40"},
        {"date": "2026-04-17", "value": "4.41"},
        {"date": "2026-04-16", "value": "4.45"},
        {"date": "2026-04-15", "value": "4.42"},
    ]},
    "DFII10": {"observations": [
        {"date": "2026-04-21", "value": "1.87"},
        {"date": "2026-04-18", "value": "1.95"},
        {"date": "2026-04-17", "value": "1.96"},
        {"date": "2026-04-16", "value": "1.98"},
        {"date": "2026-04-15", "value": "1.97"},
    ]},
    "FEDFUNDS": {"observations": [
        {"date": "2026-03-01", "value": "5.33"},
        {"date": "2026-02-01", "value": "5.33"},
    ]},
    "DTWEXBGS": {"observations": [
        {"date": "2026-04-21", "value": "103.42"},
        {"date": "2026-04-18", "value": "104.10"},
        {"date": "2026-04-17", "value": "104.20"},
        {"date": "2026-04-16", "value": "104.55"},
        {"date": "2026-04-15", "value": "104.30"},
    ]},
    "CPIAUCSL": {"observations": [
        {"date": "2026-03-01", "value": "315.2"},
        {"date": "2026-02-01", "value": "313.8"},
        {"date": "2026-01-01", "value": "312.1"},
        {"date": "2025-12-01", "value": "310.5"},
        {"date": "2025-11-01", "value": "309.2"},
        {"date": "2025-10-01", "value": "308.1"},
        {"date": "2025-09-01", "value": "307.5"},
        {"date": "2025-08-01", "value": "307.0"},
        {"date": "2025-07-01", "value": "306.5"},
        {"date": "2025-06-01", "value": "306.0"},
        {"date": "2025-05-01", "value": "305.9"},
        {"date": "2025-04-01", "value": "305.9"},
        {"date": "2025-03-01", "value": "305.8"},
    ]},
    "UNRATE": {"observations": [
        {"date": "2026-03-01", "value": "3.8"},
        {"date": "2026-02-01", "value": "3.9"},
    ]},
}


@pytest.mark.asyncio
async def test_fred_returns_six_snippets():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 6


@pytest.mark.asyncio
async def test_fred_us10y_snippet_format():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    us10y = next(s for s in snippets if "US 10Y Treasury Yield" in s)
    assert "4.32" in us10y
    assert "1d:" in us10y
    assert "5d:" in us10y


@pytest.mark.asyncio
async def test_fred_real_yield_snippet():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    real = next(s for s in snippets if "Real Yield" in s)
    assert "1.87" in real


@pytest.mark.asyncio
async def test_fred_cpi_yoy_calculated():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    cpi = next(s for s in snippets if "CPI" in s)
    # YoY: (315.2 - 305.8) / 305.8 * 100 ≈ 3.07%
    assert "3.0" in cpi or "3.1" in cpi
