from core.models import BiasResult, Factor, NewsItem, CalendarEvent, Horizon, BiasLabel, SignalDirection
from pydantic import ValidationError
import pytest
from datetime import datetime, timezone


def test_bias_result_valid():
    result = BiasResult(
        pair="XAU/USD",
        horizon=Horizon.INTRADAY,
        timestamp=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
        bias=BiasLabel.BULLISH,
        conviction=78,
        factors=[
            Factor(label="US10Y Real yield daalt", weight=0.35, direction="bullish"),
            Factor(label="DXY zwakt", weight=0.28, direction="bullish"),
            Factor(label="Geopolitieke premie", weight=0.22, direction="bullish"),
        ],
        risks_to_thesis=["Verrassing CPI print"],
        reasoning="Goud stijgt als reele rente daalt...",
        model="claude-opus-4-7",
    )
    assert result.bias == BiasLabel.BULLISH
    assert result.conviction == 78
    assert len(result.factors) == 3


def test_bias_result_conviction_out_of_range():
    with pytest.raises(ValidationError):
        BiasResult(
            pair="XAU/USD",
            horizon=Horizon.INTRADAY,
            timestamp=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
            bias=BiasLabel.BULLISH,
            conviction=150,  # ongeldig: max is 100
            factors=[],
            risks_to_thesis=[],
            reasoning="",
            model="claude-opus-4-7",
        )


def test_news_item_valid():
    item = NewsItem(
        title="Fed hints at rate cut",
        source="Reuters",
        url="https://reuters.com/article/123",
        published_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
        sentiment="bullish",
        relevant_pairs=["XAU/USD", "EUR/USD"],
        summary="Fed geeft hint over renteverlaging...",
    )
    assert item.source == "Reuters"


def test_calendar_event_valid():
    event = CalendarEvent(
        datetime_utc=datetime(2026, 4, 21, 12, 30, tzinfo=timezone.utc),
        country="US",
        name="CPI m/m",
        impact="high",
        previous="0.3%",
        forecast="0.2%",
        actual=None,
    )
    assert event.impact == "high"
    assert event.actual is None


import tempfile
from pathlib import Path
from core.vault import VaultWriter
from datetime import timezone


def test_vault_writer_creates_bias_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(vault_path=Path(tmpdir))
        result = BiasResult(
            pair="XAU/USD",
            horizon=Horizon.INTRADAY,
            timestamp=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
            bias=BiasLabel.BULLISH,
            conviction=78,
            factors=[Factor(label="Real yield daalt", weight=0.35, direction="bullish")],
            risks_to_thesis=["CPI verrassing"],
            reasoning="Goud profiteert van dalende reele rente.",
            model="claude-opus-4-7",
        )
        path = writer.write_bias(result)

        assert path.exists()
        content = path.read_text()
        assert "pair: XAU/USD" in content
        assert "bias: BULLISH" in content
        assert "conviction: 78" in content


def test_vault_writer_creates_correct_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(vault_path=Path(tmpdir))
        result = BiasResult(
            pair="EUR/USD",
            horizon=Horizon.MACRO,
            timestamp=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
            bias=BiasLabel.BEARISH,
            conviction=60,
            factors=[],
            risks_to_thesis=[],
            reasoning="EUR structureel zwak.",
            model="claude-opus-4-7",
        )
        path = writer.write_bias(result)
        assert "2026-04-21" in str(path)
        assert "eur-usd-macro" in str(path)


def test_vault_writer_feedback_update():
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(vault_path=Path(tmpdir))
        result = BiasResult(
            pair="XAU/USD",
            horizon=Horizon.INTRADAY,
            timestamp=datetime(2026, 4, 21, 8, 0, tzinfo=timezone.utc),
            bias=BiasLabel.BULLISH,
            conviction=70,
            factors=[],
            risks_to_thesis=[],
            reasoning="Test.",
            model="claude-opus-4-7",
        )
        writer.write_bias(result)
        writer.update_bias_feedback(
            pair="XAU/USD",
            horizon="intraday",
            date_str="2026-04-21",
            feedback="negative",
            note="DXY bleef sterk",
        )
        path = (
            Path(tmpdir) / "biases" / "2026-04-21" / "xau-usd-intraday.md"
        )
        content = path.read_text()
        assert "negative" in content
        assert "DXY bleef sterk" in content
