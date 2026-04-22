import pytest
from unittest.mock import MagicMock
from fetchers.fear_greed import FearGreedFetcher

_FIXTURE = {"data": [{"value": "72", "value_classification": "Greed", "timestamp": "1713700800"}]}


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
async def test_fear_greed_returns_one_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = FearGreedFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_fear_greed_snippet_content():
    client = _mock_client(_FIXTURE)
    fetcher = FearGreedFetcher(client=client)
    snippets = await fetcher.fetch()
    assert "72" in snippets[0]
    assert "Greed" in snippets[0]
    assert "Fear" in snippets[0]
