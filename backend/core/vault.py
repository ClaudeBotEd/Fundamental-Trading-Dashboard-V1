from pathlib import Path
from datetime import datetime
import logging
import frontmatter
from core.models import BiasResult, NewsItem, CalendarEvent

logger = logging.getLogger(__name__)


class VaultWriter:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    def write_bias(self, result: BiasResult) -> Path:
        date_str = result.timestamp.strftime("%Y-%m-%d")
        pair_slug = result.pair.replace("/", "-").lower()
        filename = f"{pair_slug}-{result.horizon.value}.md"

        dir_path = self.vault_path / "biases" / date_str
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / filename

        metadata = {
            "pair": result.pair,
            "horizon": result.horizon.value,
            "timestamp": result.timestamp.isoformat(),
            "bias": result.bias.value,
            "conviction": result.conviction,
            "factors": [
                {"label": f.label, "weight": f.weight, "direction": f.direction.value}
                for f in result.factors
            ],
            "conflict_with": [h.value for h in result.conflict_with],
            "model": result.model,
            "prompt_cache_hit": result.prompt_cache_hit,
            "news_refs": result.news_refs,
            "feedback": result.feedback,
            "feedback_note": result.feedback_note,
        }

        risks_md = "\n".join(f"- {r}" for r in result.risks_to_thesis)
        body = (
            f"# {result.pair} — {result.horizon.value.capitalize()} Bias"
            f" — {result.timestamp.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
            f"**Bias:** {result.bias.value} ({result.conviction}% conviction)\n\n"
            f"## Reasoning\n{result.reasoning}\n\n"
            f"## Risks to thesis\n{risks_md}\n"
        )

        post = frontmatter.Post(body, **metadata)
        file_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        return file_path

    def write_news_digest(self, date: datetime, items: list[NewsItem]) -> Path:
        date_str = date.strftime("%Y-%m-%d")
        dir_path = self.vault_path / "news"
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{date_str}-digest.md"

        lines = [f"# News Digest — {date_str}\n"]
        for item in items:
            lines.append(
                f"## {item.title}\n"
                f"- **Source:** {item.source}\n"
                f"- **Published:** {item.published_at.isoformat()}\n"
                f"- **Sentiment:** {item.sentiment.value}\n"
                f"- **Pairs:** {', '.join(item.relevant_pairs)}\n"
                f"- **URL:** {item.url}\n\n"
                f"{item.summary}\n"
            )
        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path

    def write_events(self, date: datetime, events: list[CalendarEvent]) -> Path:
        date_str = date.strftime("%Y-%m-%d")
        dir_path = self.vault_path / "events"
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{date_str}-calendar.md"

        lines = [
            f"# Economic Calendar — {date_str}\n",
            "| Time UTC | Country | Event | Impact | Previous | Forecast | Actual |",
            "|---|---|---|---|---|---|---|",
        ]
        for e in events:
            lines.append(
                f"| {e.datetime_utc.strftime('%H:%M')} "
                f"| {e.country} | {e.name} | {e.impact} "
                f"| {e.previous or ''} | {e.forecast or ''} | {e.actual or ''} |"
            )
        file_path.write_text("\n".join(lines), encoding="utf-8")
        return file_path

    def read_memory(self, pair: str) -> str:
        pair_slug = pair.replace("/", "-").lower()
        memory_path = self.vault_path / "memory" / f"{pair_slug}.md"
        if memory_path.exists():
            return memory_path.read_text(encoding="utf-8")
        return ""

    def update_bias_feedback(
        self,
        pair: str,
        horizon: str,
        date_str: str,
        feedback: str,
        note: str | None = None,
    ) -> None:
        _VALID_FEEDBACK = {"positive", "negative"}
        if feedback not in _VALID_FEEDBACK:
            raise ValueError(f"Invalid feedback value '{feedback}'. Must be one of {_VALID_FEEDBACK}")

        pair_slug = pair.replace("/", "-").lower()
        file_path = (
            self.vault_path / "biases" / date_str / f"{pair_slug}-{horizon}.md"
        ).resolve()
        vault_biases = (self.vault_path / "biases").resolve()
        if not str(file_path).startswith(str(vault_biases)):
            raise ValueError(f"Resolved path escapes vault: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"Bias file not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            post = frontmatter.load(f)
        post.metadata["feedback"] = feedback
        post.metadata["feedback_note"] = note if note else None
        file_path.write_text(frontmatter.dumps(post), encoding="utf-8")

    # ── Obsidian learning-loop methods ─────────────────────────────

    def save_bias_result(self, result: BiasResult) -> Path | None:
        """Save a BiasResult as a human-readable Obsidian markdown file.

        Returns the file path on success, None if the write fails.
        """
        date_str = result.timestamp.strftime("%Y-%m-%d")
        pair_slug = result.pair.replace("/", "-").lower()
        pair_display = result.pair.replace("/", "")
        filename = f"{pair_slug}-{result.horizon.value}.md"

        dir_path = self.vault_path / "biases" / date_str
        factors_md = "\n".join(
            f"* {f.label} ({f.direction.value}, {f.weight})" for f in result.factors
        )
        regime_phase = result.regime_phase.value if result.regime_phase else "—"
        regime = result.regime.value if result.regime else "—"
        time_horizon = result.time_horizon.value if result.time_horizon else "—"

        body = (
            f"# {pair_display} — {date_str}\n\n"
            f"Bias: {result.bias.value.capitalize()}\n"
            f"Conviction: {result.conviction}\n"
            f"Regime: {regime_phase}\n\n"
            f"## Why now\n\n{result.why_now or '—'}\n\n"
            f"## Key Driver\n\n{result.key_driver or '—'}\n\n"
            f"## Factors\n\n{factors_md}\n\n"
            f"## Market Context\n\n"
            f"* Regime: {regime}\n"
            f"* Time Horizon: {time_horizon}\n\n"
            f"## Outcome\n\n"
        )

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            file_path = dir_path / filename
            file_path.write_text(body, encoding="utf-8")
            logger.info("Saved bias result to %s", file_path)
            return file_path
        except OSError:
            logger.exception("Failed to save bias result for %s", result.pair)
            return None

    def update_outcome(self, pair: str, date: str, outcome: str) -> bool:
        """Append outcome to an existing bias markdown file.

        Returns True on success, False if the file doesn't exist or write fails.
        """
        pair_slug = pair.replace("/", "-").lower()

        # Find matching files for this pair on this date (any horizon)
        date_dir = self.vault_path / "biases" / date
        if not date_dir.exists():
            logger.warning("No bias directory for date %s", date)
            return False

        updated = False
        for file_path in date_dir.glob(f"{pair_slug}-*.md"):
            try:
                content = file_path.read_text(encoding="utf-8")
                # Replace the empty Outcome section with the actual outcome
                if "## Outcome\n\n" in content:
                    content = content.replace(
                        "## Outcome\n\n",
                        f"## Outcome\n\n{outcome}\n",
                    )
                elif "## Outcome" in content:
                    # Outcome section exists with prior content — append
                    content = content.rstrip() + f"\n{outcome}\n"
                else:
                    content = content.rstrip() + f"\n\n## Outcome\n\n{outcome}\n"
                file_path.write_text(content, encoding="utf-8")
                logger.info("Updated outcome in %s", file_path)
                updated = True
            except OSError:
                logger.exception("Failed to update outcome in %s", file_path)
        return updated
