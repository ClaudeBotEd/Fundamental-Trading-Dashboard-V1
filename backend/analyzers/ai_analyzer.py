from __future__ import annotations

import json
import datetime
import logging
from typing import TYPE_CHECKING

import anthropic
from fetchers.aggregator import ContextAggregator
from fetchers.market_data import MarketDataFetcher, format_market_context
from core.models import (
    BiasResult,
    BiasLabel,
    Horizon,
    Factor,
    Regime,
    RegimePhase,
    SignalDirection,
    TimeHorizon,
)

if TYPE_CHECKING:
    from core.vault import VaultWriter

logger = logging.getLogger(__name__)

_MODEL = "claude-opus-4-6"

_HORIZON_GUIDANCE = {
    Horizon.INTRADAY: {
        "frame": "next 1-24 hours",
        "drivers": (
            "session flows, fix windows, option expiries, intraday technicals, "
            "order-board liquidity, scheduled data releases within the session"
        ),
        "time_horizon": "SHORT",
    },
    Horizon.WEEKLY: {
        "frame": "next 1-5 trading days",
        "drivers": (
            "central bank rate decisions & guidance, macro data prints vs consensus, "
            "CFTC positioning shifts W/W, yield curve moves, cross-asset correlations, "
            "risk-sentiment proxies (VIX, credit spreads, equity index momentum)"
        ),
        "time_horizon": "MEDIUM",
    },
    Horizon.MACRO: {
        "frame": "next 1-3 months",
        "drivers": (
            "monetary policy divergence trajectories, real yield differentials, "
            "terms-of-trade shifts, current-account dynamics, structural positioning, "
            "fiscal policy direction"
        ),
        "time_horizon": "LONG",
    },
}

_SYSTEM = """\
You are an institutional FX & macro strategist at a top-tier systematic fund.
Your output drives real allocation decisions. Every claim must be positioning-aware,
catalyst-driven, quantified, and actionable. Descriptive summaries have zero value.

═══ BANNED LANGUAGE ═══

PROHIBITED everywhere — factors, reasoning, key_driver, secondary_drivers, why_now,
risks_to_thesis. Using any of these will cause rejection:
  "weakness", "strength", "signals", "pressure", "sentiment", "watching",
  "uncertainty remains", "mixed signals", "amid concerns", "remains elevated",
  "under pressure", "showing resilience", "cautious optimism", "risk appetite",
  "broadly", "largely", "somewhat", "appears to", "seems to"

Replace EVERY vague phrase with a SPECIFIC MEASUREMENT:
  ✗ "USD weakness"           → ✓ "DXY -0.6% W/W, below 104 for first time since Mar 12"
  ✗ "gold strength"          → ✓ "XAU/USD +2.3% W/W at $2,380, 4th consecutive weekly gain"
  ✗ "yields under pressure"  → ✓ "US10Y -8bps W/W to 4.44%, retracing from Apr 22 high of 4.52%"

═══ FACTOR STRUCTURE: DRIVER → CATALYST → SUPPORT ═══

You MUST structure your 3-4 factors in this exact hierarchy:

  factors[0] = PRIMARY DRIVER (structural)
    The dominant fundamental force — rate differentials, yield divergence,
    or structural positioning. This factor persists across multiple weeks.
    Weight: 0.60-1.00.

  factors[1] = CATALYST (recent trigger)
    What changed in the last 1-5 days that activated the primary driver.
    A data release, central bank statement, positioning shift, or volatility
    event. Without a catalyst, the trade is not actionable NOW.
    Weight: 0.50-0.90.

  factors[2] = POSITIONING FACTOR (mandatory)
    At least ONE factor MUST be positioning-based: CFTC/COT data, fund flows,
    speculative positioning, options positioning (risk reversals, skew), or
    dealer/real-money flow data. Weight: ≥ 0.50 unless data is stale (>7 days).
    Examples:
      ✓ "CFTC EUR net longs +12K W/W to +142K, highest since Jan 2024"
      ✓ "1M EUR/USD risk reversals flip to +0.3 vol EUR calls, from -0.2 prev week"
      ✓ "BTC ETF net inflows +$1.2B past 5 days, largest weekly inflow since Mar"

  factors[3] = OPPOSING / CONFIRMING (optional)
    A factor that either supports the thesis (same direction) or partially
    offsets it (opposite direction). If opposing, conviction must reflect it.

═══ CROSS-ASSET LINKING (MANDATORY) ═══

At least ONE factor must explicitly link FX to another asset class using a
causal chain with numbers:

  FX ↔ Yields:      "US10Y +12bps W/W lifting USD carry demand, 2Y spread US-DE at +185bps"
  FX ↔ Equities:    "S&P 500 -2.1% W/W triggering JPY repatriation flows, USD/JPY -150pips"
  FX ↔ Commodities: "Brent +4.2% W/W to $84, supporting CAD via terms-of-trade channel"
  FX ↔ Crypto:      "BTC +8% W/W as DXY drops, inverse correlation at -0.72 (30d rolling)"

The link must include: both assets, direction with numbers, and the transmission mechanism.

═══ FACTOR LABELS ═══

EVERY factor label must follow: "<Indicator> <direction+number> <relative context>"

  ✓ "CFTC EUR net longs +12K W/W to +142K contracts, highest since Jan 2024"
  ✓ "US10Y +14bps to 4.52% W/W, above 3-month range top at 4.40%"
  ✓ "ECB June cut priced at 92% vs 78% one week ago"
  ✓ "DXY -0.6% W/W vs +0.3% prior week, back below 104 support"

  ✗ "DXY declining"  ✗ "Fed expectations shifting"  ✗ "EUR supported by ECB"

═══ WEIGHT TIERS ═══

  0.70-1.00: Rate decisions, positioning extremes, macro data shocks (>2σ miss)
  0.50-0.69: Yield curve, cross-asset links, positioning shifts, risk proxies
  0.20-0.49: Confirming technicals, seasonal, secondary correlations
  0.10-0.19: Background noise — only include if nothing stronger available

═══ FACTOR QUALITY FILTER ═══

PREFERRED factor types (these carry real edge):
  • Rate differentials, yield curve moves, central bank pricing changes
  • CFTC/COT positioning shifts, fund flows, options positioning
  • Price momentum with specific levels (breakout/breakdown, range context)
  • Cross-asset causal links with numbers and transmission mechanism

PENALIZED factor labels (downgrade weight to ≤0.30 unless fully quantified):
  • "relative" factors — "EUR relatively strong" has no edge. Quantify:
    ✓ "EUR/USD +0.8% W/W vs GBP/USD +0.2% W/W, spread widening 3rd week"
  • "data" as a standalone driver — "data supportive" is meaningless.
    Quantify: ✓ "EU Mfg PMI 52.3 vs 51.8 exp, 3rd consecutive beat"
  • "residual" factors — leftover correlations are noise, not signal.
    Quantify or remove: ✓ "30d rolling correlation EUR-DXY at -0.87"

If a factor cannot be expressed with a specific number, date, or level,
it is NOT a factor — it is commentary. Remove it and reduce conviction.

═══ CONVICTION DISCIPLINE ═══

  80-100: ONLY allowed when BOTH are true:
          (a) positioning supports the directional bias
          (b) no factor opposes the thesis (all factors same direction)
          If either fails → cap at 75.

  65-79:  Allowed when BOTH are true:
          (a) a strong catalyst occurred in last 1-5 days
          (b) at least one supporting factor with weight ≥ 0.50
          If either fails → cap at 60.

  60-64:  Directional lean with identifiable drivers. Minimum conviction
          for any BULLISH or BEARISH bias.

  0-59:   REQUIRES bias=NEUTRAL. No exceptions. If you cannot justify ≥60
          conviction, you do not have enough edge to call a direction.

  CONVICTION FLOOR RULE:
    If bias is BULLISH or BEARISH → conviction MUST be ≥ 60.
    Conviction below 60 with a directional bias means you do NOT have
    enough edge — set bias to NEUTRAL instead. No exceptions.

  DIRECTION DISCIPLINE:
    If no clear catalyst occurred in the last 1-5 days → bias MUST be NEUTRAL.
    Do NOT force BULLISH or BEARISH when there is no actionable trigger.
    Fewer signals with higher accuracy is the goal. NEUTRAL is a valid,
    respectable output — it means "no edge right now."

═══ MANDATORY MARKET DATA RULE ═══

You receive a "Live Market Data (snapshot)" section with DXY, US 10Y yield,
US 10Y real yield, and VIX — current values and W/W changes.

AT LEAST ONE FACTOR must use the EXACT numbers from this snapshot.
Do not invent values. If all metrics show "unavailable", note the gap in reasoning.

═══ WHY_NOW (STRICT) ═══

"why_now" answers: "What specific event in the last 1-5 days makes this
actionable RIGHT NOW?"

REQUIREMENTS:
  • Must name a specific event, data release, or positioning shift
  • Must include a date or "this week" / "last Friday" timeframe
  • Must show the BEFORE → AFTER change it caused
  • One sentence, no filler

  ✓ "April NFP +142K vs +200K exp (released May 2) shifted July cut pricing from 55% to 72%"
  ✓ "CFTC report (Apr 19) showed EUR longs at 18-month high, crowded positioning raises reversal risk"
  ✗ "Recent data has shifted expectations"
  ✗ "Markets are repricing rate expectations"

═══ REGIME ═══

  RISK_ON:  VIX <16, credit tight, EM FX bid, equities at/near highs
  RISK_OFF: VIX >22, credit widening, JPY/CHF/gold bid, equities offered
  NEUTRAL:  Mixed or VIX 16-22 range

═══ NEWS REFERENCES ═══

2-4 specific, dateable items from the context data. Verifiable headlines or
data releases only — not summaries.
  ✓ "US April CPI +0.2% M/M vs +0.3% exp (released Apr 10)"
  ✗ "Inflation data came in lower than expected"

═══ USD BASELINE LOGIC ═══

When analyzing ANY USD pair (EUR/USD, GBP/USD, AUD/USD, USD/JPY, USD/CHF, etc.):

1. FIRST establish a USD directional baseline from three inputs:
   • DXY level + W/W change (USD index direction)
   • US10Y yield level + W/W change (rate attractiveness)
   • VIX level (risk regime proxy)

2. THEN layer currency-specific adjustments:
   • EUR → ECB policy, Eurozone data (PMI, CPI, employment)
   • GBP → BoE policy, UK data (CPI, wages, GDP)
   • AUD → RBA policy, China data, commodity prices
   • JPY → BoJ policy, intervention risk, carry dynamics
   • CHF → SNB policy, safe-haven flows

The USD baseline determines the SHARED component. Currency-specific factors
determine the DIVERGENCE between correlated pairs.

═══ CROSS-PAIR CONSISTENCY (MANDATORY) ═══

If you have context about a recently analyzed correlated pair (provided in
"PRIOR CORRELATED ANALYSIS" below), you MUST respect these rules:

1. MAX DIVERGENCE RULE: Two USD pairs sharing the same macro drivers (DXY,
   yields, risk sentiment) must NOT have conviction scores diverging by more
   than 25 points — UNLESS a strong currency-specific factor justifies it.

2. DIRECTIONAL CONSISTENCY: If DXY is clearly trending (>0.5% W/W move),
   all USD pairs should reflect the same USD directional component. A pair
   showing BULLISH (base vs USD) while another shows BEARISH requires
   explicit justification via currency-specific divergence.

3. If divergence >25 points: you MUST include a "relative_strength_note"
   field explaining WHY. Example: "EUR conviction 72 vs GBP conviction 45:
   ECB hawkish hold (+15 EUR) while BoE dovish pivot (-12 GBP) creates
   27-point spread justified by opposing central bank signals."

4. If divergence ≤25 points: "relative_strength_note" is optional but
   encouraged for pairs in the same correlation group.

═══ RELATIVE VALUE DETECTION ═══

When a prior correlated pair analysis is provided, determine relative strength:

• If both pairs are BULLISH but conviction differs:
  higher conviction pair = relatively stronger currency vs USD
  Example: EUR/USD BULLISH 72, GBP/USD BULLISH 48 → EUR stronger than GBP,
  implying EUR/GBP upside bias.

• If pairs have OPPOSITE bias:
  the divergence IS the trade — this is a relative value signal.
  Example: EUR/USD BULLISH 65, USD/JPY BULLISH 70 → strong USD-negative
  for EUR but JPY even weaker → EUR/JPY upside.

Include this insight in "relative_strength_note" when applicable.

═══ BAN ON PROXY REASONING (MANDATORY) ═══

NEVER infer a pair's bias from another pair's analysis.

PROHIBITED reasoning patterns:
  ✗ "EUR/USD is bullish, so GBP/USD should also be bullish"
  ✗ "Since USD/JPY is bearish, AUD/USD should be bullish"
  ✗ "Prior analysis shows EUR weakness, implying..."
  ✗ Using prior correlated pair results to DETERMINE bias direction

ALLOWED:
  ✓ Using prior results for CONSISTENCY CHECKING only (flag divergence)
  ✓ Each pair's bias must come from its OWN direct drivers:
    — its own central bank policy and rate path
    — its own macro data (PMI, CPI, employment)
    — its own positioning data (COT, flows, options)
    — its own yield/rate dynamics

Every pair stands alone. Prior context is for sanity-checking, NOT bias derivation.

═══ REGIME PHASE CLASSIFICATION (MANDATORY) ═══

You MUST determine the regime phase for this trade. This is a separate concept
from risk regime (RISK_ON/RISK_OFF). Regime phase describes WHERE the current
move sits in its lifecycle:

  EARLY_SHIFT:
    A new directional move is starting. Price/yields have broken recent range
    but positioning is NOT yet crowded — speculative positioning is building
    (not at extremes). A fresh catalyst within the last 1-5 days triggered the
    shift. Conviction range: 70-85.

  CONTINUATION:
    The trend is already established and factors are reinforcing it. Positioning
    is aligned but not extreme. No new catalyst required — the existing driver
    persists. Conviction cap: 75.

  LATE_CROWDED:
    The move is extended. Positioning is at or near extremes (e.g., CFTC net
    longs/shorts at multi-month highs, risk reversals at extremes, crowded
    one-way bets). Risk of reversal is elevated. Conviction cap: 60.

  CONTRADICTION:
    Signals are mixed — primary driver and catalyst point in different
    directions, or positioning contradicts price action. No clear edge.
    Conviction cap: 50. Since directional bias requires ≥60 conviction,
    CONTRADICTION phase effectively forces bias=NEUTRAL.

Determine phase based on:
  1. Positioning: crowded (LATE_CROWDED) vs building (EARLY_SHIFT) vs aligned (CONTINUATION)
  2. Price/yield movement vs recent range: breakout (EARLY_SHIFT) vs mid-range (CONTINUATION) vs extreme (LATE_CROWDED)
  3. Catalyst strength: fresh + strong (EARLY_SHIFT), persistent (CONTINUATION), exhausted/absent (LATE_CROWDED), conflicting (CONTRADICTION)

═══ OUTPUT FORMAT ═══

Return ONLY valid JSON — no markdown, no code fences, no explanation:
{
  "bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "conviction": <integer 0-100>,
  "regime_phase": "EARLY_SHIFT" | "CONTINUATION" | "LATE_CROWDED" | "CONTRADICTION",
  "reasoning": "<2-3 sentences, specific numbers, no banned words>",
  "factors": [
    {
      "label": "<Indicator> <direction+number> <relative context>",
      "weight": <0.0-1.0>,
      "direction": "bullish" | "bearish" | "neutral"
    }
  ],
  "key_driver": "<restate factors[0] — WHY this structural force dominates>",
  "secondary_drivers": ["<factors[1] restated>", "<factors[2] restated>"],
  "risks_to_thesis": ["<specific risk with trigger level>", "<second risk>"],
  "risk_to_thesis": "<the single scenario that invalidates this call, with trigger>",
  "regime": "RISK_ON" | "NEUTRAL" | "RISK_OFF",
  "time_horizon": "SHORT" | "MEDIUM" | "LONG",
  "why_now": "<specific event in last 1-5 days that makes this actionable>",
  "news_refs": ["<headline/release with date>"],
  "relative_strength_note": "<optional: cross-pair relative strength insight, include if prior pair context provided>"
}

STRUCTURAL RULES:
  • factors[0] = primary driver (structural). factors[0].label MUST match key_driver.
  • factors[1] = catalyst (recent trigger).
  • At least one factor must be positioning-based (COT, flows, options positioning).
  • At least one factor must link FX to another asset class with numbers.
  • Exactly 3-4 factors. Each label: 10-25 words.
  • conviction > 79 requires: positioning aligned + catalyst present + no opposing factor.
  • regime_phase is MANDATORY. Conviction MUST respect phase caps:
    EARLY_SHIFT: 70-85, CONTINUATION: max 75, LATE_CROWDED: max 60, CONTRADICTION: max 50.
"""


class AIAnalyzer:
    def __init__(
        self,
        settings,
        *,
        market_fetcher: MarketDataFetcher | None = None,
        vault_writer: VaultWriter | None = None,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        self._aggregator = ContextAggregator(settings)
        self._market_fetcher = market_fetcher
        self._vault_writer = vault_writer
        self._recent_results: dict[str, BiasResult] = {}

    async def analyze_pair(
        self, pair: str, horizon: Horizon = Horizon.WEEKLY
    ) -> BiasResult:
        context = await self._aggregator.fetch_for_pair(pair)
        guidance = _HORIZON_GUIDANCE[horizon]

        # Fetch live market data and format as context block
        market_block = await self._fetch_market_block()

        # Build cross-pair context from recent same-session results
        prior_context = _build_prior_context(pair, self._recent_results)

        user_prompt = (
            f"Pair: {pair}\n"
            f"Horizon: {horizon.value} ({guidance['frame']})\n"
            f"Key drivers for this horizon: {guidance['drivers']}\n"
            f"\n"
            f"{market_block}\n"
            f"{prior_context}\n"
            f"═══ FUNDAMENTAL CONTEXT DATA ═══\n"
            f"{context}"
        )

        message = await self._client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = next(b.text for b in message.content if b.type == "text")
        print(f"[AIAnalyzer] raw response:\n{raw}")

        data = _extract_json(raw)

        factors = [
            Factor(
                label=f["label"],
                weight=_clamp(float(f["weight"]), 0.0, 1.0),
                direction=SignalDirection(f["direction"]),
            )
            for f in data.get("factors", [])
        ]
        # Enforce max 4, preserve hierarchy (driver → catalyst → positioning → support)
        factors = factors[:4]

        regime_phase = _safe_enum(RegimePhase, data.get("regime_phase"))

        bias = BiasLabel(data["bias"])

        conviction = _clamp(int(data["conviction"]), 0, 100)
        conviction = _enforce_conviction_cap(conviction, factors, regime_phase)
        bias = _enforce_directional_threshold(conviction, bias)
        conviction = _enforce_conviction_floor(conviction, bias, regime_phase)
        conviction = _normalize_cross_pair_conviction(
            conviction, pair, factors, self._recent_results
        )
        # Re-enforce after cross-pair normalization which may have
        # pulled conviction below the directional threshold.
        bias = _enforce_directional_threshold(conviction, bias)

        regime = _safe_enum(Regime, data.get("regime"))
        time_horizon_val = _safe_enum(TimeHorizon, data.get("time_horizon"))
        if time_horizon_val is None:
            time_horizon_val = TimeHorizon(guidance["time_horizon"])

        result = BiasResult(
            pair=pair,
            horizon=horizon,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            bias=bias,
            conviction=conviction,
            factors=factors,
            risks_to_thesis=data.get("risks_to_thesis", []),
            reasoning=data["reasoning"],
            model=message.model,
            prompt_cache_hit=message.usage.cache_read_input_tokens > 0,
            news_refs=data.get("news_refs", []),
            key_driver=data.get("key_driver"),
            secondary_drivers=data.get("secondary_drivers", []),
            risk_to_thesis=data.get("risk_to_thesis"),
            regime=regime,
            time_horizon=time_horizon_val,
            why_now=data.get("why_now"),
            regime_phase=regime_phase,
            relative_strength_note=data.get("relative_strength_note"),
        )

        # Cache for cross-pair consistency in subsequent calls
        self._recent_results[pair] = result

        # Auto-save to Obsidian vault for learning loop
        if self._vault_writer is not None:
            self._vault_writer.save_bias_result(result)

        return result

    async def _fetch_market_block(self) -> str:
        """Fetch live market data and return formatted context block.
        Returns a fallback message if the fetcher is unavailable or fails."""
        if self._market_fetcher is None:
            return "## Live Market Data (snapshot)\n- All metrics unavailable (no fetcher configured)"
        try:
            snapshots = await self._market_fetcher.fetch_all()
            return format_market_context(snapshots)
        except Exception as exc:
            logger.warning("Market data fetch failed: %s", exc)
            return "## Live Market Data (snapshot)\n- All metrics unavailable (fetch error)"


# ── Helpers ──────────────────────────────────────────────────────


def _extract_json(raw: str) -> dict:
    """Robustly extract a JSON object from LLM output that may contain
    markdown fences, thinking tags, or surrounding prose."""
    stripped = raw.strip()

    # Strip ```json ... ``` fences if present
    if stripped.startswith("```"):
        stripped = stripped.split("```", 2)[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.rsplit("```", 1)[0].strip()

    # Find first { ... } block in case there is surrounding text
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response:\n{raw}")
    json_str = stripped[start : end + 1]

    return json.loads(json_str)


def _clamp(value, lo, hi):
    """Clamp a numeric value to [lo, hi]."""
    return max(lo, min(hi, value))


def _safe_enum(enum_cls, value):
    """Try to parse an enum value; return None on failure."""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


# ── Post-processing validation ───────────────────────────────────

_POSITIONING_KEYWORDS = frozenset([
    "cftc", "cot", "positioning", "net long", "net short", "net longs",
    "net shorts", "speculative", "spec long", "spec short", "fund flow",
    "etf flow", "inflow", "outflow", "risk reversal", "skew", "open interest",
    "commitment of traders", "dealer", "real money", "leveraged funds",
])


def _has_positioning_factor(factors: list[Factor]) -> bool:
    """Check if at least one factor references positioning data."""
    for f in factors:
        label_lower = f.label.lower()
        if any(kw in label_lower for kw in _POSITIONING_KEYWORDS):
            return True
    return False


def _has_opposing_factor(factors: list[Factor]) -> bool:
    """Check if any factor opposes the majority direction."""
    if len(factors) < 2:
        return False
    primary_dir = factors[0].direction
    return any(f.direction != primary_dir and f.direction != SignalDirection.NEUTRAL
               for f in factors[1:])


# ── Cross-pair correlation groups ──────────────────────────────

_USD_PAIRS = frozenset([
    "EUR/USD", "GBP/USD", "AUD/USD", "NZD/USD",  # base vs USD
    "USD/JPY", "USD/CHF", "USD/CAD",              # USD vs quote
])

# Pairs that share the same USD macro component (DXY/yields/VIX).
# Within a group, conviction divergence > 25 requires justification.
_CORRELATION_GROUPS: dict[str, frozenset[str]] = {
    "USD_MAJORS": frozenset([
        "EUR/USD", "GBP/USD", "AUD/USD", "NZD/USD",
        "USD/JPY", "USD/CHF", "USD/CAD",
    ]),
}

_MAX_CONVICTION_DIVERGENCE = 25


def _get_correlation_group(pair: str) -> str | None:
    """Return the correlation group name for a pair, or None."""
    for group_name, members in _CORRELATION_GROUPS.items():
        if pair in members:
            return group_name
    return None


def _build_prior_context(
    pair: str, recent_results: dict[str, "BiasResult"]
) -> str:
    """Build a prompt section with prior correlated pair analyses.

    Returns an empty string if no correlated prior results exist.
    """
    group = _get_correlation_group(pair)
    if group is None:
        return ""

    members = _CORRELATION_GROUPS[group]
    priors: list[str] = []
    for prior_pair, result in recent_results.items():
        if prior_pair == pair or prior_pair not in members:
            continue
        priors.append(
            f"  {prior_pair}: bias={result.bias.value}, "
            f"conviction={result.conviction}, "
            f"regime_phase={result.regime_phase.value if result.regime_phase else 'N/A'}, "
            f"key_driver={result.key_driver or 'N/A'}"
        )

    if not priors:
        return ""

    header = (
        "\n═══ PRIOR CORRELATED ANALYSIS (same session) ═══\n"
        "These pairs share the same USD macro component. Your conviction\n"
        "must stay within 25 points unless a currency-specific factor justifies\n"
        "divergence. If divergence >25, explain in relative_strength_note.\n\n"
    )
    return header + "\n".join(priors) + "\n"


def _normalize_cross_pair_conviction(
    conviction: int,
    pair: str,
    factors: list["Factor"],
    recent_results: dict[str, "BiasResult"],
) -> int:
    """Soft-normalize conviction against correlated prior results.

    If divergence exceeds _MAX_CONVICTION_DIVERGENCE and no strong local
    catalyst or positioning difference justifies it, pull conviction toward
    the group mean.
    """
    group = _get_correlation_group(pair)
    if group is None:
        return conviction

    members = _CORRELATION_GROUPS[group]
    prior_convictions = [
        r.conviction for p, r in recent_results.items()
        if p != pair and p in members
    ]
    if not prior_convictions:
        return conviction

    group_mean = sum(prior_convictions) / len(prior_convictions)
    divergence = abs(conviction - group_mean)

    if divergence <= _MAX_CONVICTION_DIVERGENCE:
        return conviction

    # Check for strong local justification: positioning keyword OR high-weight catalyst
    has_local_positioning = _has_positioning_factor(factors)
    has_strong_catalyst = any(
        f.weight >= 0.70 for f in factors[1:2]  # factors[1] = catalyst slot
    )

    if has_local_positioning and has_strong_catalyst:
        # Justified divergence — allow but log
        logger.info(
            "Cross-pair divergence %d pts (%s=%d vs group_mean=%.0f) "
            "ALLOWED: strong local catalyst + positioning",
            int(divergence), pair, conviction, group_mean,
        )
        return conviction

    # Pull toward group mean, capping divergence at threshold
    if conviction > group_mean:
        capped = int(group_mean + _MAX_CONVICTION_DIVERGENCE)
    else:
        capped = int(group_mean - _MAX_CONVICTION_DIVERGENCE)
    capped = _clamp(capped, 0, 100)

    logger.info(
        "Cross-pair normalization: %s conviction %d→%d "
        "(group_mean=%.0f, max_divergence=%d)",
        pair, conviction, capped, group_mean, _MAX_CONVICTION_DIVERGENCE,
    )
    return capped


_REGIME_PHASE_CAPS: dict[RegimePhase, int] = {
    RegimePhase.EARLY_SHIFT: 85,
    RegimePhase.CONTINUATION: 75,
    RegimePhase.LATE_CROWDED: 60,
    RegimePhase.CONTRADICTION: 50,
}


def _enforce_regime_phase_cap(
    conviction: int, regime_phase: RegimePhase | None
) -> int:
    """Cap conviction based on regime phase lifecycle rules."""
    if regime_phase is None:
        return conviction
    cap = _REGIME_PHASE_CAPS.get(regime_phase)
    if cap is not None and conviction > cap:
        logger.info(
            "Conviction capped %d→%d by regime phase %s",
            conviction, cap, regime_phase.value,
        )
        return cap
    return conviction


_DIRECTIONAL_FLOOR = 60


def _enforce_directional_threshold(conviction: int, bias: BiasLabel) -> BiasLabel:
    """Force bias to NEUTRAL if conviction < 60.

    Low conviction with a directional call indicates insufficient edge.
    """
    if bias != BiasLabel.NEUTRAL and conviction < _DIRECTIONAL_FLOOR:
        logger.info(
            "Bias forced NEUTRAL: conviction %d < %d threshold for %s",
            conviction, _DIRECTIONAL_FLOOR, bias.value,
        )
        return BiasLabel.NEUTRAL
    return bias


def _enforce_conviction_floor(
    conviction: int, bias: BiasLabel, regime_phase: RegimePhase | None
) -> int:
    """Enforce minimum conviction for directional (non-NEUTRAL) biases.

    BULLISH/BEARISH bias → conviction >= 60. No exceptions.
    NEUTRAL bias → no floor.
    """
    if bias == BiasLabel.NEUTRAL:
        return conviction

    if conviction < _DIRECTIONAL_FLOOR:
        logger.info(
            "Conviction floored %d→%d: bias=%s requires minimum %d",
            conviction, _DIRECTIONAL_FLOOR, bias.value, _DIRECTIONAL_FLOOR,
        )
        return _DIRECTIONAL_FLOOR

    return conviction


def _enforce_conviction_cap(
    conviction: int, factors: list[Factor], regime_phase: RegimePhase | None = None
) -> int:
    """Cap conviction based on two-tier quality gate AND regime phase.

    Tier 1 — conviction >= 80 requires:
      (a) a positioning-based factor exists
      (b) no factor opposes the primary thesis direction
    If either fails, cap at 75.

    Tier 2 — conviction >= 65 requires:
      (a) a catalyst factor (factors[1]) with weight >= 0.50
      (b) at least one supporting factor with weight >= 0.50
    If either fails, cap at 60.

    Then apply regime phase cap (EARLY_SHIFT: 85, CONTINUATION: 75,
    LATE_CROWDED: 60, CONTRADICTION: 50).
    """
    if conviction >= 80:
        has_positioning = _has_positioning_factor(factors)
        has_opposition = _has_opposing_factor(factors)

        if not has_positioning or has_opposition:
            logger.info(
                "Conviction capped %d→75: positioning=%s, opposition=%s",
                conviction, has_positioning, has_opposition,
            )
            conviction = 75

    if conviction >= 65:
        has_catalyst = len(factors) >= 2 and factors[1].weight >= 0.50
        primary_direction = factors[0].direction if factors else None
        has_supporting = any(
            f.weight >= 0.50 and f.direction == primary_direction
            for f in factors[1:]
        )

        if not has_catalyst or not has_supporting:
            logger.info(
                "Conviction capped %d→60: catalyst=%s, supporting=%s",
                conviction, has_catalyst, has_supporting,
            )
            conviction = 60

    conviction = _enforce_regime_phase_cap(conviction, regime_phase)
    return conviction
