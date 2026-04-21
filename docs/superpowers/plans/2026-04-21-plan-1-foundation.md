# Fundamental Bias Dashboard — Plan 1: Foundation + Config

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the full project skeleton so Plans 2-6 can be built without any structural decisions left open.

**Architecture:** Python backend lives in `backend/`, Next.js frontend in `frontend/`. Shared Python types are Pydantic dataclasses in `backend/core/models.py`. All secrets live in `.env` and are never committed. A single `Makefile` at the repo root provides developer shortcuts.

**Tech Stack:** Python 3.12, uv (package manager), Pydantic v2, pydantic-settings, python-dotenv, python-frontmatter, pytest, httpx.

---

## File Map

```
Fundamental Trading Dashboard V1/
├── .env.example                    # template voor secrets (gecommit)
├── .env                            # NOOIT committen (al in .gitignore)
├── Makefile                        # developer shortcuts
├── backend/
│   ├── pyproject.toml              # uv project file met alle dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py               # Pydantic: BiasResult, Factor, NewsItem, CalendarEvent, RegimeScore
│   │   ├── config.py               # laad .env, expose typed Settings object
│   │   └── vault.py                # schrijft/leest Obsidian vault bestanden
│   └── tests/
│       ├── __init__.py
│       └── test_models.py          # tests voor models + VaultWriter
└── vault/                          # Obsidian vault (data, meeste NIET in git)
    ├── biases/
    ├── memory/
    ├── news/
    ├── reflections/
    └── events/
```

---

## Task 1: Python-omgeving initialiseren met uv

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/core/__init__.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Controleer of uv geinstalleerd is**

```bash
uv --version
```

Verwacht: `uv 0.x.x` — als niet geinstalleerd, voer dit uit:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc
```

- [ ] **Step 2: Maak backend-map aan en initialiseer uv-project**

```bash
cd "/Users/claudebot/Fundamental Trading Dashboard V1"
mkdir -p backend/core backend/tests
cd backend
uv init --python 3.12 --no-workspace
```

- [ ] **Step 3: Vervang pyproject.toml met de correcte configuratie**

Overschrijf `backend/pyproject.toml` volledig met:

```toml
[project]
name = "ftd-backend"
version = "0.1.0"
description = "Fundamental Trading Dashboard — backend"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.40.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "apscheduler>=3.10.4",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "python-dotenv>=1.0.1",
    "httpx>=0.28.0",
    "pandas>=2.2.0",
    "python-frontmatter>=1.1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "vcrpy>=6.0.2",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 4: Installeer dependencies**

```bash
cd backend
uv sync
```

Verwacht: uv downloadt alle packages en maakt `.venv/` aan in `backend/`.

- [ ] **Step 5: Maak lege `__init__.py` files aan**

```bash
touch backend/core/__init__.py backend/tests/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/core/__init__.py backend/tests/__init__.py
git commit -m "feat: initialise Python backend with uv and dependencies"
```

---

## Task 2: Pydantic models (gedeelde types)

**Files:**
- Create: `backend/core/models.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Schrijf de failing test**

Maak `backend/tests/test_models.py` met deze exacte inhoud:

```python
from core.models import BiasResult, Factor, NewsItem, CalendarEvent, Horizon, BiasLabel
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
```

- [ ] **Step 2: Run de test — verwacht FAIL**

```bash
cd backend
uv run pytest tests/test_models.py -v
```

Verwacht: `ModuleNotFoundError: No module named 'core.models'`

- [ ] **Step 3: Schrijf de models**

Maak `backend/core/models.py` met deze exacte inhoud:

```python
from enum import Enum
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Horizon(str, Enum):
    INTRADAY = "intraday"
    WEEKLY = "weekly"
    MACRO = "macro"


class BiasLabel(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Factor(BaseModel):
    label: str
    weight: float = Field(ge=0.0, le=1.0)
    direction: Literal["bullish", "bearish", "neutral"]


class BiasResult(BaseModel):
    pair: str
    horizon: Horizon
    timestamp: datetime
    bias: BiasLabel
    conviction: int = Field(ge=0, le=100)
    factors: list[Factor]
    risks_to_thesis: list[str]
    reasoning: str
    model: str
    prompt_cache_hit: bool = False
    conflict_with: list[Horizon] = Field(default_factory=list)
    news_refs: list[str] = Field(default_factory=list)
    feedback: Optional[Literal["positive", "negative"]] = None
    feedback_note: Optional[str] = None


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: datetime
    sentiment: Literal["bullish", "bearish", "neutral"]
    relevant_pairs: list[str]
    summary: str


class CalendarEvent(BaseModel):
    datetime_utc: datetime
    country: str
    name: str
    impact: Literal["high", "medium", "low"]
    previous: Optional[str] = None
    forecast: Optional[str] = None
    actual: Optional[str] = None


class RegimeScore(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    label: str
    vix_z: float
    audjpy_z: float
    hyg_lqd_z: float
    es_momentum_z: float
    computed_at: datetime
```

- [ ] **Step 4: Run de tests — verwacht PASS**

```bash
cd backend
uv run pytest tests/test_models.py -v
```

Verwacht:
```
tests/test_models.py::test_bias_result_valid PASSED
tests/test_models.py::test_bias_result_conviction_out_of_range PASSED
tests/test_models.py::test_news_item_valid PASSED
tests/test_models.py::test_calendar_event_valid PASSED
4 passed in 0.XXs
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/models.py backend/tests/test_models.py
git commit -m "feat: add core Pydantic models (BiasResult, NewsItem, CalendarEvent, RegimeScore)"
```

---

## Task 3: Config (secrets laden)

**Files:**
- Create: `.env.example`
- Create: `backend/core/config.py`

- [ ] **Step 1: Maak `.env.example` aan in de repo-root**

```bash
cat > .env.example << 'EOF'
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Financial Modeling Prep
FMP_API_KEY=your-fmp-key-here

# Alpha Vantage
ALPHA_VANTAGE_API_KEY=your-av-key-here

# FRED (St. Louis Fed) — gratis, registreer op fred.stlouisfed.org
FRED_API_KEY=your-fred-key-here

# Obsidian vault pad (absoluut pad naar jouw vault op de Mac)
OBSIDIAN_VAULT_PATH=/Users/yourname/ObsidianVault/trading

# CoinGecko (optioneel, werkt ook zonder key op demo tier)
COINGECKO_API_KEY=

# Budget alarm: dagelijks max in USD (0 = geen alarm)
DAILY_BUDGET_ALARM_USD=5.0
EOF
```

- [ ] **Step 2: Kopieer naar `.env` en vul jouw API keys in**

```bash
cp .env.example .env
```

Open `.env` in een teksteditor en vul in:
- `ANTHROPIC_API_KEY` — haal op via console.anthropic.com > API Keys
- `FMP_API_KEY` — na aanmelden op financialmodelingprep.com
- `ALPHA_VANTAGE_API_KEY` — na aanmelden op alphavantage.co
- `FRED_API_KEY` — na aanmelden op fred.stlouisfed.org/docs/api
- `OBSIDIAN_VAULT_PATH` — absoluut pad naar je Obsidian vault map op de Mac (bv. `/Users/claudebot/Fundamental Trading Dashboard V1/vault`)

Controleer dat `.env` in `.gitignore` staat:
```bash
grep "\.env" .gitignore
```
Verwacht: `.env` en `.env.local` in de output.

- [ ] **Step 3: Schrijf de config**

Maak `backend/core/config.py` met deze exacte inhoud:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str
    fmp_api_key: str
    alpha_vantage_api_key: str
    fred_api_key: str
    obsidian_vault_path: Path
    coingecko_api_key: str = ""
    daily_budget_alarm_usd: float = 5.0


settings = Settings()
```

- [ ] **Step 4: Test handmatig dat config laadt**

```bash
cd backend
uv run python -c "from core.config import settings; print('Vault path:', settings.obsidian_vault_path)"
```

Verwacht: `Vault path: /Users/claudebot/Fundamental Trading Dashboard V1/vault`

Als je een `ValidationError` ziet: open `.env` en controleer of alle verplichte velden ingevuld zijn.

- [ ] **Step 5: Commit**

```bash
git add .env.example backend/core/config.py
git commit -m "feat: add config with pydantic-settings loading .env secrets"
```

---

## Task 4: Obsidian Vault Writer

**Files:**
- Create: `backend/core/vault.py`
- Modify: `backend/tests/test_models.py` — voeg vault-tests toe onderaan

- [ ] **Step 1: Voeg vault-tests toe aan het bestaande test-bestand**

Voeg deze code toe **onderaan** `backend/tests/test_models.py` (na de bestaande tests):

```python
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
```

- [ ] **Step 2: Run — verwacht FAIL**

```bash
cd backend
uv run pytest tests/test_models.py::test_vault_writer_creates_bias_file -v
```

Verwacht: `ModuleNotFoundError: No module named 'core.vault'`

- [ ] **Step 3: Schrijf de vault writer**

Maak `backend/core/vault.py` met deze exacte inhoud:

```python
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
                {"label": f.label, "weight": f.weight, "direction": f.direction}
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
                f"- **Sentiment:** {item.sentiment}\n"
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
```

- [ ] **Step 4: Run alle tests — verwacht PASS**

```bash
cd backend
uv run pytest tests/test_models.py -v
```

Verwacht:
```
tests/test_models.py::test_bias_result_valid PASSED
tests/test_models.py::test_bias_result_conviction_out_of_range PASSED
tests/test_models.py::test_news_item_valid PASSED
tests/test_models.py::test_calendar_event_valid PASSED
tests/test_models.py::test_vault_writer_creates_bias_file PASSED
tests/test_models.py::test_vault_writer_creates_correct_path PASSED
tests/test_models.py::test_vault_writer_feedback_update PASSED
7 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/vault.py backend/tests/test_models.py
git commit -m "feat: add VaultWriter — writes Obsidian YAML frontmatter bias files"
```

---

## Task 5: Vault directories + gitignore regels

**Files:**
- Create: `vault/biases/.gitkeep`, `vault/memory/.gitkeep`, `vault/news/.gitkeep`, `vault/reflections/.gitkeep`, `vault/events/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Maak alle vault-subdirectories aan**

```bash
mkdir -p vault/biases vault/memory vault/news vault/reflections vault/events
touch vault/biases/.gitkeep vault/memory/.gitkeep vault/news/.gitkeep \
      vault/reflections/.gitkeep vault/events/.gitkeep
```

- [ ] **Step 2: Voeg vault-regels toe aan `.gitignore`**

Voeg deze regels toe aan het einde van `.gitignore`:

```
# Obsidian vault data (lokaal, niet in git)
vault/biases/
vault/news/
vault/reflections/
vault/events/
# Memory bank WEL committen — lessons blijven bewaard
!vault/memory/
!vault/memory/.gitkeep
```

- [ ] **Step 3: Kies welk vault-pad je wil gebruiken**

Open `.env` en zet `OBSIDIAN_VAULT_PATH`:

```
# Optie A — gebruik de vault/ in dit project (aanbevolen voor starters)
OBSIDIAN_VAULT_PATH=/Users/claudebot/Fundamental Trading Dashboard V1/vault

# Optie B — gebruik een bestaande Obsidian vault
OBSIDIAN_VAULT_PATH=/Users/claudebot/ObsidianVault/TradingDashboard
```

Als je Optie B kiest: maak de subdirectories ook aan in die vault.

- [ ] **Step 4: Test dat config correct naar vault wijst**

```bash
cd backend
uv run python -c "
from core.config import settings
from core.vault import VaultWriter
vw = VaultWriter(settings.obsidian_vault_path)
print('Vault writer OK:', vw.vault_path)
print('Exists:', vw.vault_path.exists())
"
```

Verwacht:
```
Vault writer OK: /Users/claudebot/Fundamental Trading Dashboard V1/vault
Exists: True
```

- [ ] **Step 5: Commit**

```bash
git add vault/ .gitignore
git commit -m "feat: add vault directory structure and gitignore rules"
```

---

## Task 6: Makefile voor developer shortcuts

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Maak Makefile aan in repo-root**

Maak het bestand `Makefile` met deze exacte inhoud (gebruik tabs, geen spaties voor inspringing):

```makefile
.PHONY: backend test install vault-check frontend

backend:
	cd backend && uv run uvicorn main:app --reload --port 8000

test:
	cd backend && uv run pytest -v

install:
	cd backend && uv sync

vault-check:
	cd backend && uv run python -c \
		"from core.config import settings; from core.vault import VaultWriter; \
		vw = VaultWriter(settings.obsidian_vault_path); \
		print('Vault OK:', vw.vault_path, '| Exists:', vw.vault_path.exists())"

frontend:
	cd frontend && npm run dev
```

- [ ] **Step 2: Test de Makefile**

```bash
make test
```

Verwacht: alle 7 tests PASS, 0 FAIL.

```bash
make vault-check
```

Verwacht: `Vault OK: /Users/claudebot/Fundamental Trading Dashboard V1/vault | Exists: True`

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: add Makefile with developer shortcuts"
```

---

## Task 7: Final check en push

- [ ] **Step 1: Voer alle tests uit**

```bash
make test
```

Verwacht: 7 tests PASS, 0 FAIL.

- [ ] **Step 2: Controleer git-status — geen `.env` gelekt**

```bash
git status
```

Verwacht: `.env` staat NIET in de output (zit in .gitignore).

```bash
git log --oneline
```

Verwacht: minimaal 6 commits zichtbaar.

- [ ] **Step 3: Push naar GitHub**

```bash
git push origin main
```

Verwacht: `main -> main` zonder fouten.

---

## Self-Review

**Spec coverage:**
- [x] §3.1 Pipeline-then-analyze — VaultWriter en BiasResult zijn de foundation
- [x] §5.1 Vault directory layout — vault/ aangemaakt met alle subdirs
- [x] §5.2 YAML frontmatter schema — VaultWriter implementeert alle velden exact
- [x] §6.3 Output-contract (BiasResult) — volledig gemodelleerd in models.py
- [x] §9.1 RegimeScore model — aanwezig in models.py, klaar voor Plan 4
- [x] §12.3 Data-integriteit — `feedback: null` default in frontmatter aanwezig

**Placeholder scan:** Geen TBD/TODO. Alle stappen bevatten volledige code.

**Type consistency:**
- `BiasResult` consistent in models.py, vault.py, en tests
- `VaultWriter.write_bias(result: BiasResult)` — signature matcht test-gebruik
- `Factor.direction` is `Literal["bullish", "bearish", "neutral"]` overal consistent
- `update_bias_feedback(pair, horizon, date_str, feedback, note)` — identiek in vault.py en de test
