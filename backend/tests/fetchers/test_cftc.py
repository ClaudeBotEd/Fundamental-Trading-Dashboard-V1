import pytest
from unittest.mock import MagicMock
from fetchers.cftc import CftcFetcher

_GOLD_ROWS = [
    {
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
        "report_date_as_yyyy_mm_dd": "2026-04-15",
        "noncomm_positions_long_all": "220000",
        "noncomm_positions_short_all": "80000",
    },
    {
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
        "report_date_as_yyyy_mm_dd": "2026-04-08",
        "noncomm_positions_long_all": "210000",
        "noncomm_positions_short_all": "85000",
    },
]


def _mock_client(rows_by_contract: dict[str, list]) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        name = (params or {}).get("market_and_exchange_names", "")
        data = rows_by_contract.get(name, [])
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_cftc_skips_contracts_with_no_data():
    gold_name = "GOLD - COMMODITY EXCHANGE INC."
    client = _mock_client({gold_name: _GOLD_ROWS})
    fetcher = CftcFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_cftc_gold_snippet_net_long():
    gold_name = "GOLD - COMMODITY EXCHANGE INC."
    client = _mock_client({gold_name: _GOLD_ROWS})
    fetcher = CftcFetcher(client=client)
    snippets = await fetcher.fetch()
    gold_snip = snippets[0]
    assert "140,000" in gold_snip or "140000" in gold_snip


@pytest.mark.asyncio
async def test_cftc_gold_snippet_weekly_change():
    gold_name = "GOLD - COMMODITY EXCHANGE INC."
    client = _mock_client({gold_name: _GOLD_ROWS})
    fetcher = CftcFetcher(client=client)
    snippets = await fetcher.fetch()
    gold_snip = snippets[0]
    assert "+15,000" in gold_snip or "+15000" in gold_snip
