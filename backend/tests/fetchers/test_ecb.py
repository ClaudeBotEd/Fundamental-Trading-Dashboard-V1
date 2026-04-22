import pytest
from unittest.mock import MagicMock
from fetchers.ecb import ECBFetcher


def _make_sdmx_response(values: list[float]) -> dict:
    """Minimal SDMX jsondata structure with N observations."""
    obs = {str(i): [v] for i, v in enumerate(values)}
    return {
        "dataSets": [{"series": {"0:0:0:0:0": {"observations": obs}}}],
    }


def _mock_client(deposit_rate_vals: list[float], hicp_vals: list[float]) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "IR.MR.LEV" in url:
            resp.json.return_value = _make_sdmx_response(deposit_rate_vals)
        else:
            resp.json.return_value = _make_sdmx_response(hicp_vals)
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_ecb_returns_two_snippets():
    client = _mock_client([4.0, 4.0], [2.3, 2.4])
    fetcher = ECBFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 2


@pytest.mark.asyncio
async def test_ecb_deposit_rate_snippet():
    client = _mock_client([4.0, 3.75], [2.3, 2.4])
    fetcher = ECBFetcher(client=client)
    snippets = await fetcher.fetch()
    dfr = next(s for s in snippets if "Deposit" in s)
    assert "4.0" in dfr


@pytest.mark.asyncio
async def test_ecb_hicp_snippet():
    client = _mock_client([4.0, 4.0], [2.3, 2.4])
    fetcher = ECBFetcher(client=client)
    snippets = await fetcher.fetch()
    hicp = next(s for s in snippets if "HICP" in s)
    assert "2.3" in hicp
