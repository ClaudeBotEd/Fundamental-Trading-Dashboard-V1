import pytest
from unittest.mock import MagicMock
from fetchers.boe import BoEFetcher

_CSV = "DATE,IUDBEDR\n01 Jan 2024,5.25\n01 Aug 2024,5.00\n01 Nov 2024,4.75\n01 Feb 2025,4.50\n20 Mar 2025,4.25\n"


def _mock_client(csv_text: str) -> MagicMock:
    async def fake_get(url: str, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = csv_text
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_boe_returns_one_snippet():
    client = _mock_client(_CSV)
    fetcher = BoEFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_boe_snippet_contains_rate():
    client = _mock_client(_CSV)
    fetcher = BoEFetcher(client=client)
    snippets = await fetcher.fetch()
    assert "4.25" in snippets[0]
    assert "Bank Rate" in snippets[0]
