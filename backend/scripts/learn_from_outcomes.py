"""Analyze past bias outcomes and extract edge.

Reads the most recent bias markdown files from vault/biases,
extracts outcome data, and prints accuracy breakdowns,
factor analysis, and concrete improvement suggestions.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import frontmatter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VAULT_PATH = Path(__file__).resolve().parent.parent.parent / "vault"
MAX_FILES = 50


# ── Parsing ──────────────────────────────────────────────────────────

def _collect_bias_files(biases_dir: Path, limit: int) -> list[Path]:
    """Return up to `limit` bias .md files, newest first."""
    all_files = []
    for date_dir in sorted(biases_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        for md in sorted(date_dir.glob("*.md"), reverse=True):
            all_files.append(md)
            if len(all_files) >= limit:
                return all_files
    return all_files


def _extract_outcome(content: str) -> dict | None:
    """Pull the JSON outcome block from the markdown body."""
    if "## Outcome" not in content:
        return None
    after = content.split("## Outcome", 1)[1]
    match = re.search(r"\{[^}]+\}", after, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_reasoning(content: str) -> str:
    """Pull the Reasoning section text."""
    if "## Reasoning" not in content:
        return ""
    after = content.split("## Reasoning", 1)[1]
    end = after.find("\n## ")
    return after[:end].strip() if end != -1 else after.strip()


def _parse_record(path: Path) -> dict | None:
    """Parse a bias file into a flat analysis record."""
    try:
        post = frontmatter.load(path)
    except Exception:
        return None

    meta = post.metadata
    pair = meta.get("pair")
    bias = meta.get("bias")
    conviction = meta.get("conviction")

    if not all([pair, bias, conviction is not None]):
        return None

    outcome = _extract_outcome(post.content or "")
    if not outcome or "result" not in outcome:
        return None

    factors = meta.get("factors", [])
    factor_labels = [f.get("label", "") for f in factors if isinstance(f, dict)]

    reasoning = _extract_reasoning(post.content or "")

    return {
        "pair": pair,
        "bias": str(bias).upper(),
        "conviction": int(conviction),
        "factors": factor_labels,
        "reasoning": reasoning,
        "result": outcome["result"],
        "move_pct": outcome.get("move_pct", 0.0),
        "timeframe_days": outcome.get("timeframe_days", 0),
        "horizon": meta.get("horizon", "unknown"),
        "path": path,
    }


# ── Analysis helpers ─────────────────────────────────────────────────

def _conviction_bucket(c: int) -> str:
    if c < 40:
        return "0-39"
    if c < 60:
        return "40-59"
    if c < 80:
        return "60-79"
    return "80+"


def _extract_keywords(text: str) -> list[str]:
    """Simple keyword extraction from factor labels or reasoning."""
    noise = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "of", "in", "to", "for", "with", "on", "at", "from", "by",
        "as", "into", "through", "during", "before", "after", "and",
        "but", "or", "nor", "not", "no", "so", "yet", "both", "than",
        "that", "this", "these", "those", "it", "its", "all", "any",
        "more", "most", "other", "some", "such", "only", "own", "same",
        "very", "just", "also", "still", "while", "about", "between",
        "each", "which", "their", "if", "when", "up", "out", "over",
    }
    words = re.findall(r"[a-z]{3,}", text.lower())
    return [w for w in words if w not in noise]


# ── Main ─────────────────────────────────────────────────────────────

def learn():
    biases_dir = VAULT_PATH / "biases"
    if not biases_dir.exists():
        print("No vault/biases directory found.")
        return

    files = _collect_bias_files(biases_dir, MAX_FILES)
    records = []
    for f in files:
        r = _parse_record(f)
        if r:
            records.append(r)

    if not records:
        print("No evaluated biases found.")
        return

    correct = [r for r in records if r["result"] == "correct"]
    incorrect = [r for r in records if r["result"] == "incorrect"]

    print(f"Loaded {len(records)} evaluated biases "
          f"({len(correct)} correct, {len(incorrect)} incorrect)\n")

    # ── 1. Accuracy by bias direction ────────────────────────────────
    print("=" * 60)
    print("ACCURACY BY BIAS DIRECTION")
    print("=" * 60)
    by_bias = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in records:
        by_bias[r["bias"]]["total"] += 1
        if r["result"] == "correct":
            by_bias[r["bias"]]["correct"] += 1

    for bias in sorted(by_bias):
        d = by_bias[bias]
        acc = d["correct"] / d["total"] * 100 if d["total"] else 0
        bar = "#" * int(acc / 5)
        print(f"  {bias:8s}  {d['correct']:2d}/{d['total']:2d}  {acc:5.1f}%  {bar}")

    # ── 2. Accuracy by conviction bucket ─────────────────────────────
    print()
    print("=" * 60)
    print("ACCURACY BY CONVICTION BUCKET")
    print("=" * 60)
    by_conv = defaultdict(lambda: {"correct": 0, "total": 0, "moves": []})
    for r in records:
        bucket = _conviction_bucket(r["conviction"])
        by_conv[bucket]["total"] += 1
        by_conv[bucket]["moves"].append(abs(r["move_pct"]))
        if r["result"] == "correct":
            by_conv[bucket]["correct"] += 1

    for bucket in ["0-39", "40-59", "60-79", "80+"]:
        d = by_conv.get(bucket, {"correct": 0, "total": 0, "moves": []})
        if d["total"] == 0:
            print(f"  {bucket:6s}  -- no data --")
            continue
        acc = d["correct"] / d["total"] * 100
        avg_move = sum(d["moves"]) / len(d["moves"]) if d["moves"] else 0
        bar = "#" * int(acc / 5)
        print(f"  {bucket:6s}  {d['correct']:2d}/{d['total']:2d}  "
              f"{acc:5.1f}%  avg|move|={avg_move:.3f}%  {bar}")

    # ── 3. Factor keyword analysis ───────────────────────────────────
    print()
    print("=" * 60)
    print("FACTOR KEYWORDS: CORRECT vs INCORRECT")
    print("=" * 60)
    kw_correct = Counter()
    kw_incorrect = Counter()
    for r in records:
        kws = []
        for label in r["factors"]:
            kws.extend(_extract_keywords(label))
        counter = kw_correct if r["result"] == "correct" else kw_incorrect
        counter.update(kws)

    all_kws = set(kw_correct) | set(kw_incorrect)
    kw_edge = []
    for kw in all_kws:
        c = kw_correct.get(kw, 0)
        ic = kw_incorrect.get(kw, 0)
        total = c + ic
        if total < 2:
            continue
        rate = c / total
        kw_edge.append((kw, rate, c, ic, total))

    kw_edge.sort(key=lambda x: x[1], reverse=True)

    print("  Most predictive (high accuracy):")
    for kw, rate, c, ic, total in kw_edge[:8]:
        print(f"    {kw:25s}  {c}/{total}  ({rate*100:.0f}% correct)")

    print("  Least predictive (low accuracy):")
    for kw, rate, c, ic, total in kw_edge[-8:]:
        print(f"    {kw:25s}  {c}/{total}  ({rate*100:.0f}% correct)")

    # ── 4. Reasoning patterns → biggest moves ───────────────────────
    print()
    print("=" * 60)
    print("REASONING KEYWORDS → BIGGEST MOVES")
    print("=" * 60)
    kw_moves = defaultdict(list)
    for r in records:
        kws = _extract_keywords(r["reasoning"])
        for kw in set(kws):
            kw_moves[kw].append((r["move_pct"], r["result"]))

    kw_impact = []
    for kw, entries in kw_moves.items():
        if len(entries) < 2:
            continue
        avg_abs = sum(abs(m) for m, _ in entries) / len(entries)
        acc = sum(1 for _, res in entries if res == "correct") / len(entries)
        kw_impact.append((kw, avg_abs, acc, len(entries)))

    kw_impact.sort(key=lambda x: x[1], reverse=True)
    print("  Keywords in reasoning tied to largest avg |move|:")
    for kw, avg_abs, acc, n in kw_impact[:10]:
        print(f"    {kw:25s}  avg|move|={avg_abs:.3f}%  "
              f"acc={acc*100:.0f}%  n={n}")

    # ── 5. Top patterns that worked / failed ─────────────────────────
    print()
    print("=" * 60)
    print("TOP 5 PATTERNS THAT WORKED")
    print("=" * 60)
    correct_sorted = sorted(correct, key=lambda r: abs(r["move_pct"]), reverse=True)
    for r in correct_sorted[:5]:
        top_factor = r["factors"][0] if r["factors"] else "—"
        print(f"  {r['pair']:10s}  {r['bias']:8s}  conv={r['conviction']:2d}  "
              f"move={r['move_pct']:+.4f}%  factor: {top_factor}")

    print()
    print("=" * 60)
    print("TOP 5 PATTERNS THAT FAILED")
    print("=" * 60)
    incorrect_sorted = sorted(incorrect, key=lambda r: abs(r["move_pct"]), reverse=True)
    for r in incorrect_sorted[:5]:
        top_factor = r["factors"][0] if r["factors"] else "—"
        print(f"  {r['pair']:10s}  {r['bias']:8s}  conv={r['conviction']:2d}  "
              f"move={r['move_pct']:+.4f}%  factor: {top_factor}")

    # ── 6. Conviction calibration ────────────────────────────────────
    print()
    print("=" * 60)
    print("CONVICTION CALIBRATION INSIGHT")
    print("=" * 60)
    avg_conv_correct = (sum(r["conviction"] for r in correct) / len(correct)
                        if correct else 0)
    avg_conv_incorrect = (sum(r["conviction"] for r in incorrect) / len(incorrect)
                          if incorrect else 0)
    overall_acc = len(correct) / len(records) * 100

    print(f"  Avg conviction (correct):   {avg_conv_correct:.1f}")
    print(f"  Avg conviction (incorrect): {avg_conv_incorrect:.1f}")
    print(f"  Overall accuracy:           {overall_acc:.1f}%")

    high = [r for r in records if r["conviction"] >= 70]
    low = [r for r in records if r["conviction"] < 70]
    high_acc = (sum(1 for r in high if r["result"] == "correct") / len(high) * 100
                if high else 0)
    low_acc = (sum(1 for r in low if r["result"] == "correct") / len(low) * 100
               if low else 0)

    if avg_conv_incorrect > avg_conv_correct + 5:
        print("  → System is OVERCONFIDENT on wrong calls. "
              "High conviction ≠ accuracy.")
    elif avg_conv_correct > avg_conv_incorrect + 5:
        print("  → Conviction tracks accuracy well — "
              "trust higher-conviction calls more.")
    else:
        print("  → Conviction shows little discriminating power. "
              "Calibration needs work.")

    print(f"  Accuracy (conviction ≥70): {high_acc:.1f}% (n={len(high)})")
    print(f"  Accuracy (conviction <70): {low_acc:.1f}% (n={len(low)})")

    # ── 7. Concrete suggestions ──────────────────────────────────────
    print()
    print("=" * 60)
    print("SUGGESTIONS FOR SYSTEM PROMPT")
    print("=" * 60)

    suggestions = []

    # Suggestion 1: bias direction performance
    bull = by_bias.get("BULLISH", {"correct": 0, "total": 0})
    bear = by_bias.get("BEARISH", {"correct": 0, "total": 0})
    bull_acc = bull["correct"] / bull["total"] * 100 if bull["total"] else 0
    bear_acc = bear["correct"] / bear["total"] * 100 if bear["total"] else 0

    if bull_acc > bear_acc + 15 and bear["total"] >= 3:
        suggestions.append(
            f"BEARISH calls underperform ({bear_acc:.0f}% vs {bull_acc:.0f}% bullish). "
            "Raise the evidence bar for bearish biases — require at least 2 confirming "
            "factors before issuing a bearish call."
        )
    elif bear_acc > bull_acc + 15 and bull["total"] >= 3:
        suggestions.append(
            f"BULLISH calls underperform ({bull_acc:.0f}% vs {bear_acc:.0f}% bearish). "
            "Tighten bullish conviction — require stronger positioning or momentum "
            "confirmation before calling bullish."
        )
    else:
        suggestions.append(
            f"Both directions perform similarly ({bull_acc:.0f}% bull / "
            f"{bear_acc:.0f}% bear). Consider defaulting to NEUTRAL more often "
            f"when evidence is ambiguous rather than forcing a directional call."
        )

    # Suggestion 2: conviction calibration
    if high_acc < low_acc and len(high) >= 3:
        suggestions.append(
            f"High-conviction calls (≥70) hit only {high_acc:.0f}% vs "
            f"{low_acc:.0f}% for lower conviction. The model is overconfident — "
            "add a prompt rule: 'Conviction above 70 requires at least 3 aligned "
            "factors with no contradicting factor above weight 0.2.'"
        )
    elif high_acc > low_acc + 10 and len(high) >= 3:
        suggestions.append(
            f"High-conviction calls outperform ({high_acc:.0f}% vs {low_acc:.0f}%). "
            "Consider filtering out low-conviction (<50) biases from trading signals "
            "— they add noise without edge."
        )
    else:
        suggestions.append(
            "Conviction score doesn't reliably separate winners from losers. "
            "Restructure the conviction rubric: tie conviction directly to the "
            "number of aligned factors and the size of the dominant factor's weight."
        )

    # Suggestion 3: factor-based
    if kw_edge:
        best_kw = kw_edge[0]
        worst_kw = kw_edge[-1]
        suggestions.append(
            f"Factor keyword '{best_kw[0]}' appears in {best_kw[1]*100:.0f}% "
            f"correct calls (n={best_kw[4]}), while '{worst_kw[0]}' appears in "
            f"only {worst_kw[1]*100:.0f}% correct calls (n={worst_kw[4]}). "
            f"Weight factors containing '{best_kw[0]}' higher and treat "
            f"'{worst_kw[0]}'-based factors with more skepticism in the prompt."
        )

    for i, s in enumerate(suggestions, 1):
        print(f"\n  {i}. {s}")

    print()


if __name__ == "__main__":
    learn()
