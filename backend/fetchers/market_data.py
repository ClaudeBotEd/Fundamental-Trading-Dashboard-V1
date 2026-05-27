"""Live market data fetcher for macro dashboard metrics.

Fetches DXY, US10Y, 10Y real yield, and VIX from Yahoo Finance and FRED.
Returns structured dicts with value + change for each metric.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Yahoo Finance ────────────────────────────────────────────────

_YF_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
_YF_PARAMS = {"range": "5d", "interval": "1d"}
_YF_HEADERS = {"User-Agent": "Mozilla/5.0"}

_YF_TICKERS = {
    "dxy": "DX-Y.NYB",
    "vix": "^VIX",
    "us10y": "^TNX",
}

# ── FRED ─────────────────────────────────────────────────────────

_FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


@dataclass
class MarketSnapshot:
    """Single metric snapshot with current value and W/W change."""

    value: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    prev: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "change": round(self.change, 4) if self.change is not None else None,
            "change_pct": round(self.change_pct, 2) if self.change_pct is not None else None,
        }


class MarketDataFetcher:
    """Fetches live macro metrics from Yahoo Finance + FRED."""

    def __init__(self, fred_api_key: str) -> None:
        self._fred_key = fred_api_key

    async def fetch_all(self) -> dict[str, MarketSnapshot]:
        """Return all four metrics concurrently. Failed fetches return empty snapshots."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            dxy, vix, us10y, real_yield = await asyncio.gather(
                self._fetch_yf(client, "dxy"),
                self._fetch_yf(client, "vix"),
                self._fetch_yf(client, "us10y"),
                self._fetch_fred(client, "DFII10"),
                return_exceptions=True,
            )

        return {
            "dxy": dxy if isinstance(dxy, MarketSnapshot) else MarketSnapshot(),
            "vix": vix if isinstance(vix, MarketSnapshot) else MarketSnapshot(),
            "us10y": us10y if isinstance(us10y, MarketSnapshot) else MarketSnapshot(),
            "real_yield": real_yield if isinstance(real_yield, MarketSnapshot) else MarketSnapshot(),
        }

    # ── Yahoo Finance fetcher ────────────────────────────────────

    async def _fetch_yf(self, client: httpx.AsyncClient, key: str) -> MarketSnapshot:
        ticker = _YF_TICKERS[key]
        resp = await client.get(
            _YF_URL.format(ticker=ticker),
            params=_YF_PARAMS,
            headers=_YF_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]

        price = meta["regularMarketPrice"]

        # Get the close from ~5 trading days ago for W/W change
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        valid_closes = [c for c in closes if c is not None]

        if valid_closes and len(valid_closes) >= 2:
            prev = valid_closes[0]  # oldest close in 5d window
        else:
            prev = meta.get("chartPreviousClose") or meta.get("previousClose") or price

        change = price - prev
        # US10Y from Yahoo is already in percentage points (e.g. 4.52 = 4.52%)
        # For yields, report change in bps; for indices, report change in %
        if key == "us10y":
            change_bps = round(change * 100, 1)  # convert pp to bps
            return MarketSnapshot(
                value=round(price, 3),
                change=change_bps,
                change_pct=round(change_bps, 1),  # bps for yields
                prev=round(prev, 3),
            )
        else:
            change_pct = (change / prev * 100) if prev else 0.0
            return MarketSnapshot(
                value=round(price, 2),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                prev=round(prev, 2),
            )

    # ── FRED fetcher ─────────────────────────────────────────────

    async def _fetch_fred(self, client: httpx.AsyncClient, series_id: str) -> MarketSnapshot:
        params = {
            "series_id": series_id,
            "api_key": self._fred_key,
            "limit": 10,
            "sort_order": "desc",
            "file_type": "json",
        }
        resp = await client.get(_FRED_URL, params=params)
        resp.raise_for_status()
        obs = [o for o in resp.json()["observations"] if o["value"] != "."]

        if not obs:
            return MarketSnapshot()

        current = float(obs[0]["value"])

        # Find observation ~5 business days ago for W/W
        prev_idx = min(4, len(obs) - 1)
        prev = float(obs[prev_idx]["value"])

        change_bps = round((current - prev) * 100, 1)  # bps
        return MarketSnapshot(
            value=round(current, 3),
            change=change_bps,
            change_pct=round(change_bps, 1),  # bps for yields
            prev=round(prev, 3),
        )


def format_market_context(snapshots: dict[str, MarketSnapshot]) -> str:
    """Format market snapshots into a text block for the analyzer prompt."""
    lines = ["## Live Market Data (snapshot)"]

    dxy = snapshots.get("dxy", MarketSnapshot())
    if dxy.value is not None:
        sign = "+" if dxy.change_pct >= 0 else ""
        lines.append(f"- DXY: {dxy.value} ({sign}{dxy.change_pct}% W/W)")
    else:
        lines.append("- DXY: unavailable")

    us10y = snapshots.get("us10y", MarketSnapshot())
    if us10y.value is not None:
        sign = "+" if us10y.change >= 0 else ""
        lines.append(f"- US 10Y yield: {us10y.value}% ({sign}{us10y.change}bps W/W)")
    else:
        lines.append("- US 10Y yield: unavailable")

    ry = snapshots.get("real_yield", MarketSnapshot())
    if ry.value is not None:
        sign = "+" if ry.change >= 0 else ""
        lines.append(f"- US 10Y real yield (TIPS): {ry.value}% ({sign}{ry.change}bps W/W)")
    else:
        lines.append("- US 10Y real yield: unavailable")

    vix = snapshots.get("vix", MarketSnapshot())
    if vix.value is not None:
        sign = "+" if vix.change_pct >= 0 else ""
        lines.append(f"- VIX: {vix.value} ({sign}{vix.change_pct}% W/W)")
    else:
        lines.append("- VIX: unavailable")

    return "\n".join(lines)
