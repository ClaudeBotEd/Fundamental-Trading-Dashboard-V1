import json
import datetime
import anthropic
from fetchers.aggregator import ContextAggregator
from core.models import BiasResult, BiasLabel, Horizon, Factor, SignalDirection

_MODEL = "claude-opus-4-6"

_SYSTEM = """You are a professional macro and FX fundamental analyst.
Analyze the provided fundamental data and return a structured JSON assessment.
Return ONLY valid JSON — no markdown, no explanation, no code fences:
{
  "bias": "BULLISH" | "BEARISH" | "NEUTRAL",
  "conviction": <integer 0-100>,
  "reasoning": "<2-3 sentence explanation>",
  "factors": [{"label": "...", "weight": <0.0-1.0>, "direction": "bullish"|"bearish"|"neutral"}],
  "risks_to_thesis": ["<risk 1>", "<risk 2>"]
}"""


class AIAnalyzer:
    def __init__(self, settings) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        self._aggregator = ContextAggregator(settings)

    async def analyze_pair(self, pair: str, horizon: Horizon = Horizon.WEEKLY) -> BiasResult:
        context = await self._aggregator.fetch_for_pair(pair)

        message = await self._client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[
                {
                    "role": "user",
                    "content": f"Pair: {pair}\nHorizon: {horizon.value}\n\nFundamental Context:\n{context}",
                }
            ],
        )

        raw = next(b.text for b in message.content if b.type == "text")
        data = json.loads(raw)

        factors = [
            Factor(
                label=f["label"],
                weight=float(f["weight"]),
                direction=SignalDirection(f["direction"]),
            )
            for f in data.get("factors", [])
        ]

        return BiasResult(
            pair=pair,
            horizon=horizon,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            bias=BiasLabel(data["bias"]),
            conviction=int(data["conviction"]),
            factors=factors,
            risks_to_thesis=data.get("risks_to_thesis", []),
            reasoning=data["reasoning"],
            model=message.model,
            prompt_cache_hit=message.usage.cache_read_input_tokens > 0,
        )
