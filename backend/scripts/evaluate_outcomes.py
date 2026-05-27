"""Evaluate bias outcomes against actual price moves.

Reads bias markdown files from vault/biases (last 3 days), fetches
price data via yfinance, and writes outcome results back via VaultWriter.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import frontmatter
import yfinance as yf

# Allow imports from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.vault import VaultWriter

VAULT_PATH = Path(__file__).resolve().parent.parent.parent / "vault"

# yfinance ticker map — pairs use "EURUSD=X" format; crypto & gold differ
PAIR_TO_TICKER = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X",
    "NZD/USD": "NZDUSD=X",
    "USD/CAD": "USDCAD=X",
    "USD/CHF": "USDCHF=X",
    "XAU/USD": "GC=F",
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
}

LOOKBACK_DAYS = 3


def _parse_bias_file(path: Path) -> dict | None:
    """Extract pair, bias, and timestamp from a bias markdown file."""
    try:
        post = frontmatter.load(path)
    except Exception as exc:
        print(f"  SKIP  {path.name}: failed to parse frontmatter ({exc})")
        return None

    pair = post.metadata.get("pair")
    bias = post.metadata.get("bias")
    ts_raw = post.metadata.get("timestamp")

    if not all([pair, bias, ts_raw]):
        print(f"  SKIP  {path.name}: missing pair/bias/timestamp")
        return None

    # Check if outcome already written
    content = post.content or ""
    if "## Outcome" in content:
        after_outcome = content.split("## Outcome", 1)[1]
        if after_outcome.strip():
            return None  # already evaluated

    # Parse timestamp
    if isinstance(ts_raw, datetime):
        ts = ts_raw if ts_raw.tzinfo else ts_raw.replace(tzinfo=timezone.utc)
    else:
        ts_str = str(ts_raw)
        try:
            ts = datetime.fromisoformat(ts_str)
        except ValueError:
            print(f"  SKIP  {path.name}: unparseable timestamp '{ts_str}'")
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

    return {"pair": pair, "bias": str(bias).upper(), "timestamp": ts, "path": path}


def _fetch_price_move(pair: str, since: datetime) -> tuple[float, float, int] | None:
    """Fetch the % price move from `since` to now.

    Returns (price_at_bias, price_now, days) or None on failure.
    """
    ticker_symbol = PAIR_TO_TICKER.get(pair)
    if not ticker_symbol:
        print(f"  SKIP  {pair}: no yfinance ticker mapped")
        return None

    start_date = since.date()
    end_date = datetime.now(timezone.utc).date() + timedelta(days=1)

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(start=str(start_date), end=str(end_date))
    except Exception as exc:
        print(f"  SKIP  {pair}: yfinance error ({exc})")
        return None

    if hist.empty or len(hist) < 1:
        print(f"  SKIP  {pair}: no price data returned")
        return None

    price_at_bias = hist.iloc[0]["Close"]
    price_now = hist.iloc[-1]["Close"]
    days = (datetime.now(timezone.utc).date() - start_date).days

    return price_at_bias, price_now, max(days, 1)


def evaluate():
    """Main evaluation loop."""
    vault = VaultWriter(VAULT_PATH)
    biases_dir = VAULT_PATH / "biases"

    if not biases_dir.exists():
        print("No vault/biases directory found.")
        return

    today = datetime.now(timezone.utc).date()
    date_range = [today - timedelta(days=i) for i in range(LOOKBACK_DAYS)]

    results = {"correct": 0, "incorrect": 0, "skipped": 0}

    for date in date_range:
        date_str = date.strftime("%Y-%m-%d")
        date_dir = biases_dir / date_str
        if not date_dir.exists():
            continue

        print(f"\n── {date_str} ──")

        for md_file in sorted(date_dir.glob("*.md")):
            parsed = _parse_bias_file(md_file)
            if parsed is None:
                results["skipped"] += 1
                continue

            pair = parsed["pair"]
            bias = parsed["bias"]
            ts = parsed["timestamp"]

            price_data = _fetch_price_move(pair, ts)
            if price_data is None:
                results["skipped"] += 1
                continue

            price_at_bias, price_now, days = price_data
            move_pct = round(((price_now - price_at_bias) / price_at_bias) * 100, 4)

            # Determine correctness
            if bias == "NEUTRAL":
                outcome_result = "correct" if abs(move_pct) < 0.3 else "incorrect"
            elif bias == "BULLISH":
                outcome_result = "correct" if move_pct > 0 else "incorrect"
            else:  # BEARISH
                outcome_result = "correct" if move_pct < 0 else "incorrect"

            outcome = json.dumps(
                {
                    "result": outcome_result,
                    "move_pct": move_pct,
                    "timeframe_days": days,
                    "note": "auto-evaluated",
                },
                indent=2,
            )

            updated = vault.update_outcome(pair, date_str, outcome)
            results[outcome_result] += 1

            tag = "OK" if outcome_result == "correct" else "XX"
            status = "written" if updated else "write-failed"
            print(
                f"  [{tag}]  {pair:10s}  {bias:8s}  "
                f"move={move_pct:+.4f}%  days={days}  ({status})"
            )

    # Summary
    total = results["correct"] + results["incorrect"]
    print("\n── Summary ──")
    print(f"  Evaluated: {total}")
    print(f"  Correct:   {results['correct']}")
    print(f"  Incorrect: {results['incorrect']}")
    print(f"  Skipped:   {results['skipped']}")
    if total > 0:
        accuracy = results["correct"] / total * 100
        print(f"  Accuracy:  {accuracy:.1f}%")


if __name__ == "__main__":
    evaluate()
