import time
import pytest
from api.cache import ResultCache
from core.models import BiasResult, BiasLabel, Horizon, Factor, SignalDirection
import datetime


def _make_result(pair: str = "EUR/USD") -> BiasResult:
    return BiasResult(
        pair=pair,
        horizon=Horizon.WEEKLY,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        bias=BiasLabel.BULLISH,
        conviction=72,
        factors=[Factor(label="test", weight=0.5, direction=SignalDirection.BULLISH)],
        risks_to_thesis=["risk one"],
        reasoning="test reasoning",
        model="claude-opus-4-6",
    )


def test_get_missing_returns_none():
    cache = ResultCache(ttl_seconds=60)
    assert cache.get("EUR/USD", "weekly") is None


def test_set_and_get():
    cache = ResultCache(ttl_seconds=60)
    result = _make_result()
    cache.set(result)
    assert cache.get("EUR/USD", "weekly") is result


def test_expired_returns_none():
    cache = ResultCache(ttl_seconds=0)
    result = _make_result()
    cache.set(result)
    time.sleep(0.01)
    assert cache.get("EUR/USD", "weekly") is None


def test_all_pairs_empty():
    cache = ResultCache(ttl_seconds=60)
    assert cache.all() == []


def test_all_pairs_returns_fresh():
    cache = ResultCache(ttl_seconds=60)
    cache.set(_make_result("EUR/USD"))
    cache.set(_make_result("GBP/USD"))
    results = cache.all()
    assert len(results) == 2
