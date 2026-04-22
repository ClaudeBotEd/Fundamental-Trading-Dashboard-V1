import pytest
from fetchers.base import BaseFetcher


class ConcreteFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        return ["## Test\n- value: 1"]


@pytest.mark.asyncio
async def test_base_fetcher_returns_list():
    f = ConcreteFetcher()
    result = await f.fetch()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].startswith("## Test")


def test_base_fetcher_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseFetcher()  # type: ignore
