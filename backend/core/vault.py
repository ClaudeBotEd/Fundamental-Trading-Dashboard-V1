from pathlib import Path
from datetime import datetime
import frontmatter
from core.models import BiasResult, NewsItem, CalendarEvent


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
        pair_slug = pair.replace("/", "-").lower()
        file_path = (
            self.vault_path / "biases" / date_str / f"{pair_slug}-{horizon}.md"
        )
        if not file_path.exists():
            raise FileNotFoundError(f"Bias file not found: {file_path}")

        post = frontmatter.load(str(file_path))
        post.metadata["feedback"] = feedback
        if note:
            post.metadata["feedback_note"] = note
        file_path.write_text(frontmatter.dumps(post), encoding="utf-8")
