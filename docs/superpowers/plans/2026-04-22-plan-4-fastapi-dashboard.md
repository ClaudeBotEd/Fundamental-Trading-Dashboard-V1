# FastAPI Server + Frontend Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the AI Analyzer via a FastAPI REST API and serve a zero-dependency HTML/JS dashboard from the same process.

**Architecture:** FastAPI app with an in-memory TTL cache, APScheduler background refresh for all 10 pairs, static file serving for the frontend. The frontend is a single `index.html` with embedded CSS/JS — no build tools, no npm. Everything runs with `uv run uvicorn main:app`.

**Tech Stack:** FastAPI, uvicorn, APScheduler 3.x, Python 3.12, Vanilla JS + CSS (no framework), served as `StaticFiles` from FastAPI.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/main.py` | Create | Uvicorn entrypoint |
| `backend/api/__init__.py` | Create | Package marker |
| `backend/api/app.py` | Create | FastAPI app factory, lifespan, static mount |
| `backend/api/cache.py` | Create | In-memory dict cache with TTL |
| `backend/api/scheduler.py` | Create | APScheduler background refresh job |
| `backend/api/routes/__init__.py` | Create | Package marker |
| `backend/api/routes/pairs.py` | Create | `GET /pairs` |
| `backend/api/routes/analyze.py` | Create | `GET /analyze/{pair}`, `POST /analyze/{pair}/feedback` |
| `backend/static/index.html` | Create | Single-page dashboard, no build step |
| `backend/tests/api/__init__.py` | Create | Package marker |
| `backend/tests/api/test_cache.py` | Create | Unit tests for cache TTL logic |
| `backend/tests/api/test_routes_pairs.py` | Create | Unit test for /pairs endpoint |

---

## Task 1: In-memory TTL cache

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/cache.py`
- Create: `backend/tests/api/__init__.py`
- Create: `backend/tests/api/test_cache.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/api/test_cache.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/api/test_cache.py -v
```
Expected: `ModuleNotFoundError: No module named 'api'`

- [ ] **Step 3: Create package markers**

```python
# backend/api/__init__.py
# (empty)
```

```python
# backend/tests/api/__init__.py
# (empty)
```

- [ ] **Step 4: Implement ResultCache**

```python
# backend/api/cache.py
import time
from threading import Lock
from core.models import BiasResult


class ResultCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[str, str], tuple[BiasResult, float]] = {}
        self._lock = Lock()

    def get(self, pair: str, horizon: str) -> BiasResult | None:
        with self._lock:
            entry = self._store.get((pair, horizon))
            if entry is None:
                return None
            result, stored_at = entry
            if time.time() - stored_at > self._ttl:
                del self._store[(pair, horizon)]
                return None
            return result

    def set(self, result: BiasResult) -> None:
        with self._lock:
            self._store[(result.pair, result.horizon.value)] = (result, time.time())

    def all(self) -> list[BiasResult]:
        now = time.time()
        with self._lock:
            return [
                r for (r, stored_at) in self._store.values()
                if now - stored_at <= self._ttl
            ]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/api/test_cache.py -v
```
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
cd backend && git add api/__init__.py api/cache.py tests/api/__init__.py tests/api/test_cache.py
git commit -m "feat: add in-memory TTL cache for BiasResult"
```

---

## Task 2: GET /pairs route

**Files:**
- Create: `backend/api/routes/__init__.py`
- Create: `backend/api/routes/pairs.py`
- Create: `backend/tests/api/test_routes_pairs.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_routes_pairs.py
import pytest
from fastapi.testclient import TestClient
from api.routes.pairs import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_get_pairs_returns_list():
    response = client.get("/pairs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "EUR/USD" in data
    assert "BTC/USD" in data
    assert len(data) == 10
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/api/test_routes_pairs.py -v
```
Expected: `ModuleNotFoundError: No module named 'api.routes'`

- [ ] **Step 3: Create package marker and implement route**

```python
# backend/api/routes/__init__.py
# (empty)
```

```python
# backend/api/routes/pairs.py
from fastapi import APIRouter

SUPPORTED_PAIRS = [
    "XAU/USD",
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "AUD/USD",
    "USD/CAD",
    "USD/CHF",
    "NZD/USD",
    "BTC/USD",
    "ETH/USD",
]

router = APIRouter()


@router.get("/pairs")
def get_pairs() -> list[str]:
    return SUPPORTED_PAIRS
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/api/test_routes_pairs.py -v
```
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
cd backend && git add api/routes/__init__.py api/routes/pairs.py tests/api/test_routes_pairs.py
git commit -m "feat: add GET /pairs route"
```

---

## Task 3: GET /analyze/{pair} + POST /analyze/{pair}/feedback routes

**Files:**
- Create: `backend/api/routes/analyze.py`

No unit tests here — the analyze route calls the live AI; integration is tested manually.

- [ ] **Step 1: Implement the analyze router**

```python
# backend/api/routes/analyze.py
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from core.models import BiasResult, Horizon
from api.cache import ResultCache

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_cache(request: Request) -> ResultCache:
    return request.app.state.cache


def _get_analyzer(request: Request):
    return request.app.state.analyzer


class FeedbackPayload(BaseModel):
    feedback: str
    note: str | None = None


@router.get("/analyze/{pair:path}", response_model=BiasResult)
async def analyze_pair(
    pair: str,
    request: Request,
    horizon: Horizon = Horizon.WEEKLY,
    refresh: bool = False,
    cache: ResultCache = Depends(_get_cache),
    analyzer=Depends(_get_analyzer),
) -> BiasResult:
    pair = pair.replace("-", "/").upper()
    cached = cache.get(pair, horizon.value)
    if cached and not refresh:
        return cached
    try:
        result = await analyzer.analyze_pair(pair, horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    cache.set(result)
    try:
        request.app.state.vault_writer.write_bias(result)
    except Exception as exc:
        logger.warning("Vault write failed: %s", exc)
    return result


@router.get("/analyze", response_model=list[BiasResult])
def list_cached(cache: ResultCache = Depends(_get_cache)) -> list[BiasResult]:
    return cache.all()


@router.post("/analyze/{pair:path}/feedback", status_code=204)
async def post_feedback(
    pair: str,
    payload: FeedbackPayload,
    request: Request,
    cache: ResultCache = Depends(_get_cache),
) -> None:
    pair = pair.replace("-", "/").upper()
    cached = cache.get(pair, Horizon.WEEKLY.value)
    if cached is None:
        raise HTTPException(status_code=404, detail="No cached result for this pair")
    vault_writer = request.app.state.vault_writer
    date_str = cached.timestamp.strftime("%Y-%m-%d")
    try:
        vault_writer.update_bias_feedback(
            pair=pair,
            horizon=Horizon.WEEKLY.value,
            date_str=date_str,
            feedback=payload.feedback,
            note=payload.note,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add api/routes/analyze.py
git commit -m "feat: add GET /analyze and POST feedback routes"
```

---

## Task 4: APScheduler background refresh

**Files:**
- Create: `backend/api/scheduler.py`

- [ ] **Step 1: Implement the scheduler**

```python
# backend/api/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.models import Horizon
from api.routes.pairs import SUPPORTED_PAIRS

logger = logging.getLogger(__name__)


def build_scheduler(analyzer, cache) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    async def _refresh_all() -> None:
        logger.info("Scheduler: refreshing all pairs")
        for pair in SUPPORTED_PAIRS:
            try:
                result = await analyzer.analyze_pair(pair, Horizon.WEEKLY)
                cache.set(result)
                logger.info("Refreshed %s → %s (%s%%)", pair, result.bias.value, result.conviction)
            except Exception as exc:
                logger.error("Failed to refresh %s: %s", pair, exc)

    scheduler.add_job(_refresh_all, "interval", hours=4, id="refresh_all")
    return scheduler
```

- [ ] **Step 2: Commit**

```bash
cd backend && git add api/scheduler.py
git commit -m "feat: add APScheduler background refresh (4h interval)"
```

---

## Task 5: FastAPI app factory + main entrypoint

**Files:**
- Create: `backend/api/app.py`
- Create: `backend/main.py`

- [ ] **Step 1: Implement app factory**

```python
# backend/api/app.py
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core.config import settings
from core.vault import VaultWriter
from analyzers.ai_analyzer import AIAnalyzer
from api.cache import ResultCache
from api.scheduler import build_scheduler
from api.routes.pairs import router as pairs_router
from api.routes.analyze import router as analyze_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = ResultCache(ttl_seconds=4 * 3600)
    analyzer = AIAnalyzer(settings)
    vault_writer = VaultWriter(settings.obsidian_vault_path)
    scheduler = build_scheduler(analyzer, cache)

    app.state.cache = cache
    app.state.analyzer = analyzer
    app.state.vault_writer = vault_writer
    app.state.scheduler = scheduler

    scheduler.start()
    yield

    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fundamental Trading Dashboard",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(pairs_router)
    app.include_router(analyze_router)

    static_dir = Path(__file__).resolve().parent.parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
```

- [ ] **Step 2: Implement main entrypoint**

```python
# backend/main.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=False)
```

- [ ] **Step 3: Smoke-test startup (no frontend yet)**

```bash
cd backend && uv run python main.py &
sleep 3
curl -s http://localhost:8000/pairs | python3 -m json.tool
kill %1
```
Expected: JSON array of 10 pairs

- [ ] **Step 4: Commit**

```bash
cd backend && git add api/app.py main.py
git commit -m "feat: FastAPI app factory with lifespan, scheduler, and static mount"
```

---

## Task 6: Frontend dashboard (single HTML file)

**Files:**
- Create: `backend/static/index.html`

Self-contained single-page app. No npm. No build step. Tailwind via CDN (free). Vanilla JS.

- [ ] **Step 1: Create the dashboard HTML**

```html
<!-- backend/static/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Fundamental Trading Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background: #0f1117; color: #e2e8f0; font-family: 'Inter', sans-serif; }
    .card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px; }
    .bullish  { color: #4ade80; }
    .bearish  { color: #f87171; }
    .neutral  { color: #94a3b8; }
    .bar-bullish  { background: #4ade80; }
    .bar-bearish  { background: #f87171; }
    .bar-neutral  { background: #94a3b8; }
    .tab-active   { background: #3b82f6; color: #fff; }
    .tab-inactive { background: #1e2130; color: #94a3b8; }
    .tab-inactive:hover { background: #252840; }
    .spinner { border: 3px solid #2d3148; border-top-color: #3b82f6;
               border-radius: 50%; width: 32px; height: 32px;
               animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .conviction-ring { position: relative; width: 120px; height: 120px; }
    .conviction-ring svg { transform: rotate(-90deg); }
    .conviction-label { position: absolute; top: 50%; left: 50%;
                        transform: translate(-50%, -50%); font-size: 1.4rem;
                        font-weight: 700; }
  </style>
</head>
<body class="min-h-screen p-6">

  <h1 class="text-2xl font-bold mb-1 text-white">Fundamental Trading Dashboard</h1>
  <p class="text-slate-400 text-sm mb-6">AI-driven macro bias · Weekly horizon</p>

  <div id="tabs" class="flex flex-wrap gap-2 mb-6"></div>
  <div id="result-area"></div>

  <script>
    const PAIRS = [
      "XAU/USD","EUR/USD","GBP/USD","USD/JPY","AUD/USD",
      "USD/CAD","USD/CHF","NZD/USD","BTC/USD","ETH/USD"
    ];

    let activePair = PAIRS[1];
    let results = {};

    function renderTabs() {
      const container = document.getElementById('tabs');
      container.innerHTML = '';
      PAIRS.forEach(pair => {
        const btn = document.createElement('button');
        btn.textContent = pair;
        btn.className = `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
          pair === activePair ? 'tab-active' : 'tab-inactive'
        }`;
        btn.onclick = () => selectPair(pair);
        container.appendChild(btn);
      });
    }

    function selectPair(pair) {
      activePair = pair;
      renderTabs();
      renderResult();
    }

    async function fetchPair(pair, refresh = false) {
      const slug = pair.replace('/', '-');
      const url = `/analyze/${slug}?horizon=weekly${refresh ? '&refresh=true' : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      results[pair] = data;
      return data;
    }

    function convictionRing(conviction, biasClass) {
      const r = 50, circ = 2 * Math.PI * r;
      const dash = (conviction / 100) * circ;
      const colorMap = { bullish: '#4ade80', bearish: '#f87171', neutral: '#94a3b8' };
      const color = colorMap[biasClass] ?? '#94a3b8';
      return `
        <div class="conviction-ring mx-auto mb-4">
          <svg viewBox="0 0 120 120" width="120" height="120">
            <circle cx="60" cy="60" r="${r}" fill="none" stroke="#2d3148" stroke-width="12"/>
            <circle cx="60" cy="60" r="${r}" fill="none" stroke="${color}" stroke-width="12"
              stroke-dasharray="${dash} ${circ}" stroke-linecap="round"/>
          </svg>
          <div class="conviction-label ${biasClass}">${conviction}</div>
        </div>`;
    }

    function factorBar(f) {
      const pct = Math.round(f.weight * 100);
      return `
        <div class="mb-2">
          <div class="flex justify-between text-xs mb-0.5">
            <span class="text-slate-300">${f.label}</span>
            <span class="${f.direction} font-semibold">${f.direction.toUpperCase()} ${pct}%</span>
          </div>
          <div class="w-full bg-slate-700 rounded h-1.5">
            <div class="bar-${f.direction} h-1.5 rounded" style="width:${pct}%"></div>
          </div>
        </div>`;
    }

    function renderResult() {
      const area = document.getElementById('result-area');
      const data = results[activePair];

      if (!data) {
        area.innerHTML = `
          <div class="card p-8 flex flex-col items-center gap-4">
            <div class="spinner"></div>
            <p class="text-slate-400 text-sm">Fetching analysis for ${activePair}…</p>
          </div>`;
        return;
      }

      const biasClass = data.bias.toLowerCase();
      const ts = new Date(data.timestamp).toLocaleString('en-GB', { timeZone: 'UTC' }) + ' UTC';
      const factorBars = (data.factors || []).map(factorBar).join('');
      const riskItems = (data.risks_to_thesis || [])
        .map(r => `<li class="text-slate-300 text-sm">⚠ ${r}</li>`).join('');

      area.innerHTML = `
        <div class="card p-6 max-w-2xl">
          <div class="flex items-start justify-between mb-4">
            <div>
              <h2 class="text-xl font-bold text-white">${data.pair}</h2>
              <p class="text-slate-400 text-xs mt-0.5">${ts}</p>
            </div>
            <button onclick="refreshPair('${activePair}')"
              class="text-xs px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 transition-colors">
              ↺ Refresh
            </button>
          </div>

          <div class="flex flex-col items-center mb-6">
            ${convictionRing(data.conviction, biasClass)}
            <span class="text-2xl font-bold ${biasClass}">${data.bias}</span>
            <span class="text-slate-400 text-xs mt-1">conviction: ${data.conviction}/100</span>
          </div>

          <div class="mb-6">
            <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">Factors</h3>
            ${factorBars}
          </div>

          <div class="mb-6">
            <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">Reasoning</h3>
            <p class="text-slate-300 text-sm leading-relaxed">${data.reasoning}</p>
          </div>

          <div>
            <h3 class="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-2">Risks to thesis</h3>
            <ul class="space-y-1">${riskItems}</ul>
          </div>

          <div class="mt-4 pt-4 border-t border-slate-700 flex gap-3 items-center">
            <span class="text-slate-500 text-xs">Was this analysis useful?</span>
            <button onclick="sendFeedback('${activePair}','positive')"
              class="text-xs px-2 py-1 rounded bg-emerald-800 hover:bg-emerald-700 text-emerald-200">👍 Yes</button>
            <button onclick="sendFeedback('${activePair}','negative')"
              class="text-xs px-2 py-1 rounded bg-red-900 hover:bg-red-800 text-red-200">👎 No</button>
          </div>
        </div>`;
    }

    async function refreshPair(pair) {
      delete results[pair];
      renderResult();
      try { await fetchPair(pair, true); } catch(e) { console.error(e); }
      if (activePair === pair) renderResult();
    }

    async function sendFeedback(pair, feedback) {
      const slug = pair.replace('/', '-');
      await fetch(`/analyze/${slug}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback }),
      });
    }

    async function init() {
      renderTabs();
      renderResult();
      try { await fetchPair(activePair); } catch(e) { console.error(e); }
      renderResult();
      const others = PAIRS.filter(p => p !== activePair);
      for (const pair of others) {
        await new Promise(r => setTimeout(r, 2000));
        try { await fetchPair(pair); } catch(e) { /* silent */ }
      }
    }

    init();
  </script>
</body>
</html>
```

- [ ] **Step 2: Start server and verify dashboard loads**

```bash
cd backend && uv run python main.py
```

Open browser at `http://localhost:8000` — should see dashboard with EUR/USD loading.

- [ ] **Step 3: Commit**

```bash
cd backend && git add static/index.html
git commit -m "feat: add single-page trading dashboard frontend"
```

---

## Task 7: End-to-end smoke test + push

- [ ] **Step 1: Run full test suite**

```bash
cd backend && uv run pytest -v
```
Expected: all existing tests pass.

- [ ] **Step 2: Start server and test all endpoints**

```bash
cd backend && uv run python main.py &
sleep 3
curl -s http://localhost:8000/pairs | python3 -m json.tool
curl -s "http://localhost:8000/analyze/EUR-USD?horizon=weekly" | python3 -m json.tool
curl -s http://localhost:8000/analyze | python3 -m json.tool
kill %1
```

- [ ] **Step 3: Push to GitHub**

```bash
git push origin main
```

---

## Self-Review

**Spec coverage:**
- ✅ FastAPI server → Task 5
- ✅ In-memory cache with TTL → Task 1
- ✅ GET /pairs → Task 2
- ✅ GET /analyze/{pair} (cache-first, refresh flag) → Task 3
- ✅ GET /analyze (list all cached) → Task 3
- ✅ POST /analyze/{pair}/feedback → Task 3
- ✅ Background scheduler (4h refresh) → Task 4
- ✅ Vault write on fresh analysis → Task 3
- ✅ Frontend single-page dashboard → Task 6
- ✅ E2E smoke test + push → Task 7

**Placeholder scan:** No TBDs. All code is complete.

**Type consistency:**
- `ResultCache.set(result: BiasResult)` / `.get(pair, horizon)` / `.all()` — consistent across Tasks 1, 3, 4, 5.
- `SUPPORTED_PAIRS` defined in `pairs.py`, imported in `scheduler.py` — one source of truth.
- `app.state.cache`, `app.state.analyzer`, `app.state.vault_writer`, `app.state.scheduler` — set in `app.py` lifespan, read via `Depends` in routes.
