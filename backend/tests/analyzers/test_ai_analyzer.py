import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from analyzers.ai_analyzer import AIAnalyzer
from core.models import BiasResult, BiasLabel, Horizon


def _make_settings(anthropic_key="sk-test"):
    settings = MagicMock()
    settings.anthropic_api_key.get_secret_value.return_value = anthropic_key
    settings.fred_api_key.get_secret_value.return_value = "fred-test"
    settings.fmp_api_key.get_secret_value.return_value = "fmp-test"
    settings.alpha_vantage_api_key.get_secret_value.return_value = "av-test"
    settings.coingecko_api_key.get_secret_value.return_value = ""
    return settings


def _make_message(payload: dict, model: str = "claude-opus-4-6", cache_read: int = 0):
    """Build a mock Anthropic Message object from a payload dict."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(payload)

    thinking_block = MagicMock()
    thinking_block.type = "thinking"

    usage = MagicMock()
    usage.cache_read_input_tokens = cache_read

    msg = MagicMock()
    msg.content = [thinking_block, text_block]
    msg.model = model
    msg.usage = usage
    return msg


_BULLISH_PAYLOAD = {
    "bias": "BULLISH",
    "conviction": 72,
    "reasoning": "USD weakens on dovish Fed signals; EUR supported by ECB hawkishness.",
    "factors": [
        {"label": "Fed pivot signal", "weight": 0.4, "direction": "bullish"},
        {"label": "ECB rate hold", "weight": 0.3, "direction": "bullish"},
    ],
    "risks_to_thesis": ["Surprise US CPI print", "ECB policy reversal"],
}

_BEARISH_PAYLOAD = {
    "bias": "BEARISH",
    "conviction": 55,
    "reasoning": "DXY strengthens on hot NFP data.",
    "factors": [{"label": "Strong NFP", "weight": 0.5, "direction": "bearish"}],
    "risks_to_thesis": ["Fed pause"],
}


@pytest.fixture
def analyzer():
    settings = _make_settings()
    with patch("analyzers.ai_analyzer.ContextAggregator") as MockAgg:
        MockAgg.return_value.fetch_for_pair = AsyncMock(return_value="## Macro Context\nSample data.")
        analyzer = AIAnalyzer(settings)
        yield analyzer, MockAgg.return_value


async def test_analyze_pair_returns_bias_result(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BULLISH_PAYLOAD)
    ai._client.messages.create = AsyncMock(return_value=msg)

    result = await ai.analyze_pair("EUR/USD", Horizon.WEEKLY)

    assert isinstance(result, BiasResult)
    assert result.pair == "EUR/USD"
    assert result.horizon == Horizon.WEEKLY
    assert result.bias == BiasLabel.BULLISH
    assert result.conviction == 72
    assert result.model == "claude-opus-4-6"


async def test_analyze_pair_factors_parsed(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BULLISH_PAYLOAD)
    ai._client.messages.create = AsyncMock(return_value=msg)

    result = await ai.analyze_pair("EUR/USD")

    assert len(result.factors) == 2
    assert result.factors[0].label == "Fed pivot signal"
    assert result.factors[0].weight == pytest.approx(0.4)
    assert result.factors[0].direction == "bullish"


async def test_analyze_pair_risks_parsed(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BULLISH_PAYLOAD)
    ai._client.messages.create = AsyncMock(return_value=msg)

    result = await ai.analyze_pair("EUR/USD")

    assert "Surprise US CPI print" in result.risks_to_thesis


async def test_analyze_pair_bearish(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BEARISH_PAYLOAD)
    ai._client.messages.create = AsyncMock(return_value=msg)

    result = await ai.analyze_pair("XAU/USD", Horizon.INTRADAY)

    assert result.bias == BiasLabel.BEARISH
    assert result.conviction == 55
    assert result.horizon == Horizon.INTRADAY


async def test_analyze_pair_cache_hit_detected(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BULLISH_PAYLOAD, cache_read=1024)
    ai._client.messages.create = AsyncMock(return_value=msg)

    result = await ai.analyze_pair("EUR/USD")

    assert result.prompt_cache_hit is True


async def test_analyze_pair_no_cache_hit(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BULLISH_PAYLOAD, cache_read=0)
    ai._client.messages.create = AsyncMock(return_value=msg)

    result = await ai.analyze_pair("EUR/USD")

    assert result.prompt_cache_hit is False


async def test_analyze_pair_calls_aggregator(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BULLISH_PAYLOAD)
    ai._client.messages.create = AsyncMock(return_value=msg)

    await ai.analyze_pair("GBP/USD", Horizon.MACRO)

    agg.fetch_for_pair.assert_awaited_once_with("GBP/USD")


async def test_analyze_pair_default_horizon_is_weekly(analyzer):
    ai, agg = analyzer
    msg = _make_message(_BULLISH_PAYLOAD)
    ai._client.messages.create = AsyncMock(return_value=msg)

    result = await ai.analyze_pair("USD/JPY")

    assert result.horizon == Horizon.WEEKLY
