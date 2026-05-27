"""Seed the vault with sample bias, news, and calendar data for Obsidian testing."""

from datetime import datetime, timezone
from pathlib import Path
from core.models import (
    BiasResult, Factor, Horizon, BiasLabel, SignalDirection,
    NewsItem, CalendarEvent,
)
from core.vault import VaultWriter

VAULT = Path(__file__).resolve().parent.parent / "vault"


def seed():
    writer = VaultWriter(VAULT)

    # --- Bias: EUR/USD intraday ---
    bias_eurusd = BiasResult(
        pair="EUR/USD",
        horizon=Horizon.INTRADAY,
        timestamp=datetime(2026, 4, 22, 8, 0, tzinfo=timezone.utc),
        bias=BiasLabel.BEARISH,
        conviction=72,
        factors=[
            Factor(label="DXY momentum", weight=0.4, direction=SignalDirection.BEARISH),
            Factor(label="ECB rate expectations", weight=0.35, direction=SignalDirection.BEARISH),
            Factor(label="Risk sentiment", weight=0.25, direction=SignalDirection.NEUTRAL),
        ],
        risks_to_thesis=[
            "Unexpected dovish Fed commentary",
            "Eurozone PMI surprise to the upside",
        ],
        reasoning=(
            "Dollar strength continues on hawkish Fed minutes. ECB cutting cycle "
            "expectations are weighing on EUR. Risk sentiment is mixed, providing no "
            "clear offset to USD demand."
        ),
        model="claude-opus-4-6",
        prompt_cache_hit=True,
        conflict_with=[],
        news_refs=["fed-minutes-april", "ecb-rate-cut"],
    )
    p = writer.write_bias(bias_eurusd)
    print(f"  Written: {p}")

    # --- Bias: GBP/USD weekly ---
    bias_gbpusd = BiasResult(
        pair="GBP/USD",
        horizon=Horizon.WEEKLY,
        timestamp=datetime(2026, 4, 22, 8, 0, tzinfo=timezone.utc),
        bias=BiasLabel.BULLISH,
        conviction=61,
        factors=[
            Factor(label="BoE hold expectations", weight=0.5, direction=SignalDirection.BULLISH),
            Factor(label="UK employment data", weight=0.3, direction=SignalDirection.BULLISH),
            Factor(label="US yields retreating", weight=0.2, direction=SignalDirection.BULLISH),
        ],
        risks_to_thesis=[
            "UK CPI miss could shift BoE expectations",
            "Geopolitical escalation driving USD safe-haven bid",
        ],
        reasoning=(
            "BoE is expected to hold rates while Fed rhetoric remains mixed. "
            "UK labor market is showing resilience, supporting GBP. US yields "
            "pulling back reduces USD tailwind."
        ),
        model="claude-opus-4-6",
        prompt_cache_hit=False,
        conflict_with=[Horizon.MACRO],
        news_refs=["boe-hold", "uk-employment"],
    )
    p = writer.write_bias(bias_gbpusd)
    print(f"  Written: {p}")

    # --- Bias: USD/JPY macro ---
    bias_usdjpy = BiasResult(
        pair="USD/JPY",
        horizon=Horizon.MACRO,
        timestamp=datetime(2026, 4, 22, 8, 0, tzinfo=timezone.utc),
        bias=BiasLabel.NEUTRAL,
        conviction=45,
        factors=[
            Factor(label="BoJ policy shift", weight=0.4, direction=SignalDirection.BEARISH),
            Factor(label="US-JP rate differential", weight=0.4, direction=SignalDirection.BULLISH),
            Factor(label="Intervention risk", weight=0.2, direction=SignalDirection.BEARISH),
        ],
        risks_to_thesis=[
            "Sudden BoJ rate hike",
            "MoF intervention at 160+ levels",
        ],
        reasoning=(
            "Conflicting forces: BoJ is slowly normalizing while the US-JP rate "
            "differential remains wide. MoF intervention risk caps upside. "
            "Net result is a range-bound view."
        ),
        model="claude-opus-4-6",
        prompt_cache_hit=True,
        conflict_with=[Horizon.INTRADAY],
        news_refs=["boj-policy", "mof-intervention"],
    )
    p = writer.write_bias(bias_usdjpy)
    print(f"  Written: {p}")

    # --- News digest ---
    news_items = [
        NewsItem(
            title="Fed Minutes Show Officials Divided on Rate Path",
            source="Reuters",
            url="https://example.com/fed-minutes",
            published_at=datetime(2026, 4, 21, 18, 30, tzinfo=timezone.utc),
            sentiment=SignalDirection.BEARISH,
            relevant_pairs=["EUR/USD", "GBP/USD", "USD/JPY"],
            summary="Federal Reserve minutes revealed a split among policymakers on the pace of rate adjustments, with several members favoring a longer pause.",
        ),
        NewsItem(
            title="ECB Signals Further Easing in H2 2026",
            source="Bloomberg",
            url="https://example.com/ecb-easing",
            published_at=datetime(2026, 4, 22, 7, 0, tzinfo=timezone.utc),
            sentiment=SignalDirection.BEARISH,
            relevant_pairs=["EUR/USD", "EUR/GBP"],
            summary="ECB governing council members indicated additional rate cuts may come in the second half of 2026 if inflation continues to moderate.",
        ),
        NewsItem(
            title="UK Employment Holds Steady, Wage Growth Accelerates",
            source="Financial Times",
            url="https://example.com/uk-jobs",
            published_at=datetime(2026, 4, 22, 6, 0, tzinfo=timezone.utc),
            sentiment=SignalDirection.BULLISH,
            relevant_pairs=["GBP/USD", "EUR/GBP"],
            summary="UK unemployment remained at 4.0% while average earnings growth picked up to 5.8%, reinforcing expectations the BoE will hold rates.",
        ),
    ]
    today = datetime(2026, 4, 22, tzinfo=timezone.utc)
    p = writer.write_news_digest(today, news_items)
    print(f"  Written: {p}")

    # --- Calendar events ---
    events = [
        CalendarEvent(
            datetime_utc=datetime(2026, 4, 22, 12, 30, tzinfo=timezone.utc),
            country="US",
            name="Existing Home Sales",
            impact="medium",
            previous="4.26M",
            forecast="4.15M",
        ),
        CalendarEvent(
            datetime_utc=datetime(2026, 4, 22, 14, 0, tzinfo=timezone.utc),
            country="US",
            name="Richmond Fed Manufacturing Index",
            impact="medium",
            previous="-4",
            forecast="-2",
        ),
        CalendarEvent(
            datetime_utc=datetime(2026, 4, 23, 8, 30, tzinfo=timezone.utc),
            country="UK",
            name="CPI y/y",
            impact="high",
            previous="3.4%",
            forecast="3.1%",
        ),
        CalendarEvent(
            datetime_utc=datetime(2026, 4, 23, 12, 15, tzinfo=timezone.utc),
            country="EU",
            name="ECB Main Refinancing Rate",
            impact="high",
            previous="3.65%",
            forecast="3.40%",
        ),
    ]
    p = writer.write_events(today, events)
    print(f"  Written: {p}")

    # --- Memory file for EUR/USD ---
    memory_path = VAULT / "memory" / "eur-usd.md"
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(
        "# EUR/USD — Trading Memory\n\n"
        "## Patterns\n"
        "- Tends to sell off into ECB meetings when rate cuts are expected\n"
        "- DXY above 105 has historically capped EUR/USD rebounds\n"
        "- NFP days: avoid new positions 2h before release\n\n"
        "## Past Mistakes\n"
        "- 2026-03-15: Went long against DXY momentum — stopped out\n"
        "- 2026-04-01: Ignored ECB forward guidance — missed bearish follow-through\n\n"
        "## Key Levels\n"
        "- Support: 1.0650, 1.0580\n"
        "- Resistance: 1.0800, 1.0870\n",
        encoding="utf-8",
    )
    print(f"  Written: {memory_path}")

    # --- Reflection file ---
    reflection_path = VAULT / "reflections" / "2026-04-22.md"
    reflection_path.parent.mkdir(parents=True, exist_ok=True)
    reflection_path.write_text(
        "# Daily Reflection — 2026-04-22\n\n"
        "## What went well\n"
        "- Correctly identified EUR/USD bearish bias from DXY strength\n"
        "- Avoided trading into NFP noise\n\n"
        "## What to improve\n"
        "- Waited too long to enter GBP/USD long — missed 30 pips\n"
        "- Need to review conviction threshold — 61% felt too low for sizing\n\n"
        "## Tomorrow's focus\n"
        "- UK CPI at 08:30 UTC — key for GBP positioning\n"
        "- ECB rate decision — watch for forward guidance language\n",
        encoding="utf-8",
    )
    print(f"  Written: {reflection_path}")


if __name__ == "__main__":
    print("Seeding vault with sample data...")
    seed()
    print("\nDone! Open Obsidian to see the files.")
