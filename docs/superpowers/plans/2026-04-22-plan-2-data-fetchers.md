# Plan 2: Data Fetchers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build async data fetchers for all 8 external sources that each return normalized markdown snippets ready to feed into Claude's analysis pipeline.

**Architecture:** Each fetcher lives in `backend/fetchers/`, accepts an injectable `httpx.AsyncClient` for testability, and returns `list[str]` — markdown snippets. A final `ContextAggregator` in `aggregator.py` maps each pair to its relevant fetchers and returns one combined markdown string per pair. FMP and Alpha Vantage check for empty keys and return `[]` gracefully. No fetcher imports `settings` at module level — API keys are passed as constructor args (caller does `settings.fred_api_key.get_secret_value()`).

**Tech Stack:** Python 3.12, httpx (async), pytest + pytest-asyncio, unittest.mock (no extra libs needed)

---

## File Map

```
backend/
├── fetchers/
│   ├── __init__.py          # exports all fetchers + ContextAggregator
│   ├── base.py              # BaseFetcher ABC: __init__(client), fetch() -> list[str]
│   ├── fred.py              # FREDFetcher(api_key, client): 6 series → 6 snippets
│   ├── ecb.py               # ECBFetcher(client): deposit rate + HICP → 2 snippets
│   ├── boe.py               # BoEFetcher(client): bank rate → 1 snippet
│   ├── coingecko.py         # CoinGeckoFetcher(api_key="", client): BTC+ETH → 2 snippets
│   ├── fear_greed.py        # FearGreedFetcher(client): index → 1 snippet
│   ├── cftc.py              # CftcFetcher(client): 8 contracts → up to 8 snippets
│   ├── fmp.py               # FMPFetcher(api_key, client): calendar+news → N snippets
│   ├── alpha_vantage.py     # AlphaVantageFetcher(api_key, client): news sentiment → 1 snippet
│   └── aggregator.py        # ContextAggregator(settings): fetch_for_pair(pair) -> str
└── tests/
    └── fetchers/
        ├── __init__.py
        ├── test_base.py
        ├── test_fred.py
        ├── test_ecb.py
        ├── test_boe.py
        ├── test_coingecko.py
        ├── test_fear_greed.py
        ├── test_cftc.py
        ├── test_fmp.py
        ├── test_alpha_vantage.py
        └── test_aggregator.py
```

---

## Task 1: Base fetcher + test infrastructure

**Files:**
- Create: `backend/fetchers/__init__.py`
- Create: `backend/fetchers/base.py`
- Create: `backend/tests/fetchers/__init__.py`
- Create: `backend/tests/fetchers/test_base.py`

- [ ] **Step 1: Check pytest-asyncio is installed**

```bash
cd backend && uv run pytest --version && uv run python -c "import pytest_asyncio; print(pytest_asyncio.__version__)"
```

Expected: pytest version printed, then a version string. If `ModuleNotFoundError`:

```bash
cd backend && uv add pytest-asyncio
```

- [ ] **Step 2: Write failing test**

Create `backend/tests/fetchers/__init__.py` (empty).

Create `backend/tests/fetchers/test_base.py`:

```python
import pytest
from backend.fetchers.base import BaseFetcher


class ConcreteFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        return ["## Test\n- value: 1"]


@pytest.mark.asyncio
async def test_base_fetcher_returns_list():
    f = ConcreteFetcher()
    result = await f.fetch()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].startswith("## Test")


def test_base_fetcher_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseFetcher()  # type: ignore
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_base.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.fetchers'`

- [ ] **Step 4: Create base.py**

Create `backend/fetchers/__init__.py` (empty for now).

Create `backend/fetchers/base.py`:

```python
import httpx
from abc import ABC, abstractmethod


class BaseFetcher(ABC):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)

    @abstractmethod
    async def fetch(self) -> list[str]:
        """Return list of markdown snippet strings for Claude context."""
        ...
```

- [ ] **Step 5: Add asyncio_mode to pyproject.toml**

Open `backend/pyproject.toml`. In the `[tool.pytest.ini_options]` section (add if missing):

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && uv run pytest tests/fetchers/test_base.py -v
```

Expected: `PASSED` for both tests.

- [ ] **Step 7: Commit**

```bash
git add backend/fetchers/__init__.py backend/fetchers/base.py backend/tests/fetchers/__init__.py backend/tests/fetchers/test_base.py backend/pyproject.toml
git commit -m "feat: add BaseFetcher ABC and test infrastructure"
```

---

## Task 2: FRED Fetcher

Fetches 6 FRED series: US10Y yield, US10Y Real yield (TIPS), Fed Funds rate, USD Broad Index, CPI YoY, Unemployment.

API: `GET https://api.stlouisfed.org/fred/series/observations?series_id={ID}&api_key={key}&limit=5&sort_order=desc&file_type=json`

**Files:**
- Create: `backend/fetchers/fred.py`
- Create: `backend/tests/fetchers/test_fred.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_fred.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.fred import FREDFetcher


def _mock_client(json_by_series: dict[str, dict]) -> MagicMock:
    """Return a mock AsyncClient whose .get() returns different JSON per series_id."""
    client = MagicMock()

    async def fake_get(url: str, params: dict | None = None, **kwargs):
        series_id = (params or {}).get("series_id", "")
        data = json_by_series.get(series_id, {"observations": []})
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client.get = fake_get
    return client


FRED_FIXTURES = {
    "DGS10": {"observations": [
        {"date": "2026-04-21", "value": "4.32"},
        {"date": "2026-04-18", "value": "4.40"},
        {"date": "2026-04-17", "value": "4.41"},
        {"date": "2026-04-16", "value": "4.45"},
        {"date": "2026-04-15", "value": "4.42"},
    ]},
    "DFII10": {"observations": [
        {"date": "2026-04-21", "value": "1.87"},
        {"date": "2026-04-18", "value": "1.95"},
        {"date": "2026-04-17", "value": "1.96"},
        {"date": "2026-04-16", "value": "1.98"},
        {"date": "2026-04-15", "value": "1.97"},
    ]},
    "FEDFUNDS": {"observations": [
        {"date": "2026-03-01", "value": "5.33"},
        {"date": "2026-02-01", "value": "5.33"},
    ]},
    "DTWEXBGS": {"observations": [
        {"date": "2026-04-21", "value": "103.42"},
        {"date": "2026-04-18", "value": "104.10"},
        {"date": "2026-04-17", "value": "104.20"},
        {"date": "2026-04-16", "value": "104.55"},
        {"date": "2026-04-15", "value": "104.30"},
    ]},
    "CPIAUCSL": {"observations": [
        {"date": "2026-03-01", "value": "315.2"},
        {"date": "2026-02-01", "value": "313.8"},
        {"date": "2026-01-01", "value": "312.1"},
        {"date": "2025-12-01", "value": "310.5"},
        {"date": "2025-11-01", "value": "309.2"},
        {"date": "2025-10-01", "value": "308.1"},
        {"date": "2025-09-01", "value": "307.5"},
        {"date": "2025-08-01", "value": "307.0"},
        {"date": "2025-07-01", "value": "306.5"},
        {"date": "2025-06-01", "value": "306.0"},
        {"date": "2025-05-01", "value": "305.9"},
        {"date": "2025-04-01", "value": "305.9"},
        {"date": "2025-03-01", "value": "305.8"},
    ]},
    "UNRATE": {"observations": [
        {"date": "2026-03-01", "value": "3.8"},
        {"date": "2026-02-01", "value": "3.9"},
    ]},
}


@pytest.mark.asyncio
async def test_fred_returns_six_snippets():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 6


@pytest.mark.asyncio
async def test_fred_us10y_snippet_format():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    us10y = next(s for s in snippets if "US 10Y Treasury Yield" in s)
    assert "4.32" in us10y
    assert "1d:" in us10y
    assert "5d:" in us10y


@pytest.mark.asyncio
async def test_fred_real_yield_snippet():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    real = next(s for s in snippets if "Real Yield" in s)
    assert "1.87" in real


@pytest.mark.asyncio
async def test_fred_cpi_yoy_calculated():
    client = _mock_client(FRED_FIXTURES)
    fetcher = FREDFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    cpi = next(s for s in snippets if "CPI" in s)
    # YoY: (315.2 - 305.8) / 305.8 * 100 ≈ 3.07%
    assert "3.0" in cpi or "3.1" in cpi
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_fred.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.fetchers.fred'`

- [ ] **Step 3: Implement FREDFetcher**

Create `backend/fetchers/fred.py`:

```python
import httpx
from backend.fetchers.base import BaseFetcher

_BASE = "https://api.stlouisfed.org/fred/series/observations"

_SERIES = {
    "DGS10":    ("US 10Y Treasury Yield",          "%", 5),
    "DFII10":   ("US 10Y Real Yield (TIPS)",        "%", 5),
    "FEDFUNDS": ("Fed Funds Rate",                  "%", 2),
    "DTWEXBGS": ("USD Nominal Broad Index",         "",  5),
    "CPIAUCSL": ("CPI All Urban Consumers",         "",  13),  # 13 for YoY
    "UNRATE":   ("Unemployment Rate",              "%", 2),
}


class FREDFetcher(BaseFetcher):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        snippets = []
        for series_id, (label, unit, limit) in _SERIES.items():
            params = {
                "series_id": series_id,
                "api_key": self._api_key,
                "limit": limit,
                "sort_order": "desc",
                "file_type": "json",
            }
            resp = await self._client.get(_BASE, params=params)
            resp.raise_for_status()
            obs = [o for o in resp.json()["observations"] if o["value"] != "."]
            if not obs:
                continue
            snippets.append(self._format(series_id, label, unit, obs))
        return snippets

    @staticmethod
    def _format(series_id: str, label: str, unit: str, obs: list[dict]) -> str:
        current = float(obs[0]["value"])
        lines = [f"## {label}", f"- Current: {current}{unit}"]
        if len(obs) >= 2:
            prev1d = float(obs[1]["value"])
            lines.append(f"- Change 1d: {current - prev1d:+.2f}{unit}")
        if len(obs) >= 5:
            prev5d = float(obs[4]["value"])
            lines.append(f"- Change 5d: {current - prev5d:+.2f}{unit}")
        if series_id == "CPIAUCSL" and len(obs) >= 13:
            yoy_base = float(obs[12]["value"])
            yoy = (current - yoy_base) / yoy_base * 100
            lines.append(f"- YoY: {yoy:.1f}%")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_fred.py -v
```

Expected: all 4 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/fred.py backend/tests/fetchers/test_fred.py
git commit -m "feat: add FREDFetcher — 6 series, normalized markdown snippets"
```

---

## Task 3: ECB Fetcher

Fetches ECB deposit rate and HICP from the ECB SDMX REST API. Returns 2 snippets.

API: `GET https://data-api.ecb.europa.eu/service/data/{flowRef}/{key}?format=jsondata&lastNObservations=2`

**Files:**
- Create: `backend/fetchers/ecb.py`
- Create: `backend/tests/fetchers/test_ecb.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_ecb.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.ecb import ECBFetcher


def _make_sdmx_response(values: list[float]) -> dict:
    """Minimal SDMX jsondata structure with N observations."""
    obs = {str(i): [v] for i, v in enumerate(values)}
    return {
        "dataSets": [{"series": {"0:0:0:0:0": {"observations": obs}}}],
    }


def _mock_client(deposit_rate_vals: list[float], hicp_vals: list[float]) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        if "IR.MR.LEV" in url:
            resp.json.return_value = _make_sdmx_response(deposit_rate_vals)
        else:
            resp.json.return_value = _make_sdmx_response(hicp_vals)
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_ecb_returns_two_snippets():
    client = _mock_client([4.0, 4.0], [2.3, 2.4])
    fetcher = ECBFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 2


@pytest.mark.asyncio
async def test_ecb_deposit_rate_snippet():
    client = _mock_client([4.0, 3.75], [2.3, 2.4])
    fetcher = ECBFetcher(client=client)
    snippets = await fetcher.fetch()
    dfr = next(s for s in snippets if "Deposit" in s)
    assert "4.0" in dfr


@pytest.mark.asyncio
async def test_ecb_hicp_snippet():
    client = _mock_client([4.0, 4.0], [2.3, 2.4])
    fetcher = ECBFetcher(client=client)
    snippets = await fetcher.fetch()
    hicp = next(s for s in snippets if "HICP" in s)
    assert "2.3" in hicp
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_ecb.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement ECBFetcher**

Create `backend/fetchers/ecb.py`:

```python
import httpx
from backend.fetchers.base import BaseFetcher

_BASE = "https://data-api.ecb.europa.eu/service/data"
_DEPOSIT_RATE_KEY = "FM/M.U2.EUR.IR.MR.LEV"
_HICP_KEY = "ICP/M.U2.N.000000.4.ANR"


class ECBFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        snippets = [
            await self._fetch_series(_DEPOSIT_RATE_KEY, "ECB Deposit Facility Rate", "%"),
            await self._fetch_series(_HICP_KEY, "Eurozone HICP Inflation", "%"),
        ]
        return [s for s in snippets if s]

    async def _fetch_series(self, key: str, label: str, unit: str) -> str:
        url = f"{_BASE}/{key}"
        params = {"format": "jsondata", "lastNObservations": 2}
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        try:
            series = data["dataSets"][0]["series"]["0:0:0:0:0"]["observations"]
            values = [series[k][0] for k in sorted(series.keys(), key=int)]
        except (KeyError, IndexError):
            return ""
        if not values:
            return ""
        current = values[-1]
        lines = [f"## {label}", f"- Current: {current}{unit}"]
        if len(values) >= 2:
            lines.append(f"- Previous: {values[-2]}{unit}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_ecb.py -v
```

Expected: all 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/ecb.py backend/tests/fetchers/test_ecb.py
git commit -m "feat: add ECBFetcher — deposit rate + HICP via SDMX REST API"
```

---

## Task 4: BoE Fetcher

Fetches the Bank of England base rate via the BoE IADB CSV endpoint. Returns 1 snippet.

API: `GET https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2020&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y`

Response is CSV: `DATE,IUDBEDR\n01 Jan 2024,5.25\n...`

**Files:**
- Create: `backend/fetchers/boe.py`
- Create: `backend/tests/fetchers/test_boe.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_boe.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.boe import BoEFetcher

_CSV = "DATE,IUDBEDR\n01 Jan 2024,5.25\n01 Aug 2024,5.00\n01 Nov 2024,4.75\n01 Feb 2025,4.50\n20 Mar 2025,4.25\n"


def _mock_client(csv_text: str) -> MagicMock:
    async def fake_get(url: str, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = csv_text
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_boe_returns_one_snippet():
    client = _mock_client(_CSV)
    fetcher = BoEFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_boe_snippet_contains_rate():
    client = _mock_client(_CSV)
    fetcher = BoEFetcher(client=client)
    snippets = await fetcher.fetch()
    assert "4.25" in snippets[0]
    assert "Bank Rate" in snippets[0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_boe.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement BoEFetcher**

Create `backend/fetchers/boe.py`:

```python
import httpx
from backend.fetchers.base import BaseFetcher

_URL = (
    "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"
    "?csv.x=yes&Datefrom=01/Jan/2020&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y"
)


class BoEFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        resp = await self._client.get(_URL)
        resp.raise_for_status()
        rows = [
            line.split(",")
            for line in resp.text.strip().splitlines()
            if line and not line.startswith("DATE")
        ]
        valid = [(r[0].strip(), r[1].strip()) for r in rows if len(r) == 2 and r[1].strip()]
        if not valid:
            return []
        date, rate = valid[-1]
        lines = ["## BoE Bank Rate", f"- Current: {rate}%", f"- As of: {date}"]
        if len(valid) >= 2:
            lines.append(f"- Previous: {valid[-2][1]}%")
        return ["\n".join(lines)]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_boe.py -v
```

Expected: both tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/boe.py backend/tests/fetchers/test_boe.py
git commit -m "feat: add BoEFetcher — GBP bank rate via BoE IADB CSV endpoint"
```

---

## Task 5: CoinGecko Fetcher

Fetches BTC and ETH price, 24h change, and market cap. Returns 2 snippets (1 per coin). API key optional (empty string = demo tier, 30 req/min).

API: `GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true&include_market_cap=true`

**Files:**
- Create: `backend/fetchers/coingecko.py`
- Create: `backend/tests/fetchers/test_coingecko.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_coingecko.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.coingecko import CoinGeckoFetcher

_FIXTURE = {
    "bitcoin":  {"usd": 68500.0, "usd_24h_change": 2.34,  "usd_market_cap": 1350000000000},
    "ethereum": {"usd": 3420.0,  "usd_24h_change": -0.87, "usd_market_cap": 411000000000},
}


def _mock_client(data: dict) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_coingecko_returns_two_snippets():
    client = _mock_client(_FIXTURE)
    fetcher = CoinGeckoFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 2


@pytest.mark.asyncio
async def test_coingecko_btc_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = CoinGeckoFetcher(client=client)
    snippets = await fetcher.fetch()
    btc = next(s for s in snippets if "BTC" in s)
    assert "68,500" in btc or "68500" in btc
    assert "+2.34%" in btc


@pytest.mark.asyncio
async def test_coingecko_eth_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = CoinGeckoFetcher(client=client)
    snippets = await fetcher.fetch()
    eth = next(s for s in snippets if "ETH" in s)
    assert "3,420" in eth or "3420" in eth
    assert "-0.87%" in eth
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_coingecko.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement CoinGeckoFetcher**

Create `backend/fetchers/coingecko.py`:

```python
import httpx
from backend.fetchers.base import BaseFetcher

_URL = "https://api.coingecko.com/api/v3/simple/price"
_COINS = {"bitcoin": "BTC", "ethereum": "ETH"}


class CoinGeckoFetcher(BaseFetcher):
    def __init__(self, api_key: str = "", client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        params: dict = {
            "ids": ",".join(_COINS.keys()),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        }
        if self._api_key:
            params["x_cg_pro_api_key"] = self._api_key
        resp = await self._client.get(_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return [
            self._format(ticker, data[coin_id])
            for coin_id, ticker in _COINS.items()
            if coin_id in data
        ]

    @staticmethod
    def _format(ticker: str, d: dict) -> str:
        price = d.get("usd", 0)
        change = d.get("usd_24h_change", 0)
        mcap = d.get("usd_market_cap", 0)
        sign = "+" if change >= 0 else ""
        return "\n".join([
            f"## {ticker}/USD (CoinGecko)",
            f"- Price: ${price:,.0f}",
            f"- 24h Change: {sign}{change:.2f}%",
            f"- Market Cap: ${mcap / 1e9:.1f}B",
        ])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_coingecko.py -v
```

Expected: all 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/coingecko.py backend/tests/fetchers/test_coingecko.py
git commit -m "feat: add CoinGeckoFetcher — BTC/ETH price, 24h change, market cap"
```

---

## Task 6: Fear & Greed Fetcher

Fetches the Crypto Fear & Greed Index from alternative.me. Returns 1 snippet.

API: `GET https://api.alternative.me/fng/?limit=1`

Response: `{"data": [{"value": "72", "value_classification": "Greed", "timestamp": "1713700800"}]}`

**Files:**
- Create: `backend/fetchers/fear_greed.py`
- Create: `backend/tests/fetchers/test_fear_greed.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_fear_greed.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.fear_greed import FearGreedFetcher

_FIXTURE = {"data": [{"value": "72", "value_classification": "Greed", "timestamp": "1713700800"}]}


def _mock_client(data: dict) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_fear_greed_returns_one_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = FearGreedFetcher(client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_fear_greed_snippet_content():
    client = _mock_client(_FIXTURE)
    fetcher = FearGreedFetcher(client=client)
    snippets = await fetcher.fetch()
    assert "72" in snippets[0]
    assert "Greed" in snippets[0]
    assert "Fear" in snippets[0]  # header contains "Fear & Greed"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_fear_greed.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement FearGreedFetcher**

Create `backend/fetchers/fear_greed.py`:

```python
import httpx
from backend.fetchers.base import BaseFetcher

_URL = "https://api.alternative.me/fng/"


class FearGreedFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        resp = await self._client.get(_URL, params={"limit": 1})
        resp.raise_for_status()
        data = resp.json()
        try:
            entry = data["data"][0]
            value = int(entry["value"])
            classification = entry["value_classification"]
        except (KeyError, IndexError, ValueError):
            return []
        signal = "RISK-ON" if value >= 55 else "RISK-OFF" if value <= 45 else "NEUTRAL"
        return ["\n".join([
            "## Crypto Fear & Greed Index",
            f"- Value: {value}/100",
            f"- Classification: {classification}",
            f"- Signal: {signal}",
        ])]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_fear_greed.py -v
```

Expected: both tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/fear_greed.py backend/tests/fetchers/test_fear_greed.py
git commit -m "feat: add FearGreedFetcher — crypto sentiment index"
```

---

## Task 7: CFTC Fetcher

Fetches COT (Commitment of Traders) non-commercial positioning for 8 contracts: Gold, EUR, GBP, JPY, AUD, CAD, CHF, BTC. Returns up to 8 snippets (skips contracts with no data).

API: CFTC Socrata public API — no key required.
`GET https://publicreporting.cftc.gov/resource/jun7-fc8e.json?market_and_exchange_names={name}&$order=report_date_as_yyyy_mm_dd DESC&$limit=2`

**Files:**
- Create: `backend/fetchers/cftc.py`
- Create: `backend/tests/fetchers/test_cftc.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_cftc.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.cftc import CftcFetcher

_GOLD_ROWS = [
    {
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
        "report_date_as_yyyy_mm_dd": "2026-04-15",
        "noncomm_positions_long_all": "220000",
        "noncomm_positions_short_all": "80000",
    },
    {
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
        "report_date_as_yyyy_mm_dd": "2026-04-08",
        "noncomm_positions_long_all": "210000",
        "noncomm_positions_short_all": "85000",
    },
]


def _mock_client(rows_by_contract: dict[str, list]) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        name = (params or {}).get("market_and_exchange_names", "")
        data = rows_by_contract.get(name, [])
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_cftc_skips_contracts_with_no_data():
    gold_name = "GOLD - COMMODITY EXCHANGE INC."
    client = _mock_client({gold_name: _GOLD_ROWS})
    fetcher = CftcFetcher(client=client)
    snippets = await fetcher.fetch()
    # Only gold has data; 7 others return [] → skipped
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_cftc_gold_snippet_net_long():
    gold_name = "GOLD - COMMODITY EXCHANGE INC."
    client = _mock_client({gold_name: _GOLD_ROWS})
    fetcher = CftcFetcher(client=client)
    snippets = await fetcher.fetch()
    gold_snip = snippets[0]
    # Net = 220000 - 80000 = 140000
    assert "140,000" in gold_snip or "140000" in gold_snip


@pytest.mark.asyncio
async def test_cftc_gold_snippet_weekly_change():
    gold_name = "GOLD - COMMODITY EXCHANGE INC."
    client = _mock_client({gold_name: _GOLD_ROWS})
    fetcher = CftcFetcher(client=client)
    snippets = await fetcher.fetch()
    gold_snip = snippets[0]
    # Previous net: 210000 - 85000 = 125000; change = +15000
    assert "+15,000" in gold_snip or "+15000" in gold_snip
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_cftc.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement CftcFetcher**

Create `backend/fetchers/cftc.py`:

```python
import httpx
from backend.fetchers.base import BaseFetcher

_URL = "https://publicreporting.cftc.gov/resource/jun7-fc8e.json"

_CONTRACTS = [
    ("Gold (XAU)",              "GOLD - COMMODITY EXCHANGE INC."),
    ("Euro (EUR)",              "EURO FX - CHICAGO MERCANTILE EXCHANGE"),
    ("British Pound (GBP)",     "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE"),
    ("Japanese Yen (JPY)",      "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"),
    ("Australian Dollar (AUD)", "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
    ("Canadian Dollar (CAD)",   "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"),
    ("Swiss Franc (CHF)",       "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"),
    ("Bitcoin (BTC)",           "BITCOIN - CHICAGO MERCANTILE EXCHANGE"),
]


class CftcFetcher(BaseFetcher):
    async def fetch(self) -> list[str]:
        snippets = []
        for display_name, market_name in _CONTRACTS:
            params = {
                "market_and_exchange_names": market_name,
                "$order": "report_date_as_yyyy_mm_dd DESC",
                "$limit": 2,
            }
            resp = await self._client.get(_URL, params=params)
            resp.raise_for_status()
            rows = resp.json()
            if not rows:
                continue
            snippets.append(self._format(display_name, rows))
        return snippets

    @staticmethod
    def _format(display_name: str, rows: list[dict]) -> str:
        def net(row: dict) -> int:
            return int(row["noncomm_positions_long_all"]) - int(row["noncomm_positions_short_all"])

        current_net = net(rows[0])
        date = rows[0].get("report_date_as_yyyy_mm_dd", "")
        lines = [
            f"## COT — {display_name}",
            f"- Date: {date}",
            f"- Non-commercial net: {current_net:+,}",
            f"- Long: {int(rows[0]['noncomm_positions_long_all']):,}",
            f"- Short: {int(rows[0]['noncomm_positions_short_all']):,}",
        ]
        if len(rows) >= 2:
            change = current_net - net(rows[1])
            lines.append(f"- Weekly change: {change:+,}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_cftc.py -v
```

Expected: all 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/cftc.py backend/tests/fetchers/test_cftc.py
git commit -m "feat: add CftcFetcher — COT positioning for 8 contracts"
```

---

## Task 8: FMP Fetcher

Fetches economic calendar events (next 7 days, high-impact only) and recent general news. Returns `[]` gracefully if `api_key` is empty.

APIs:
- Calendar: `GET https://financialmodelingprep.com/api/v3/economic_calendar?from={YYYY-MM-DD}&to={YYYY-MM-DD}&apikey={key}`
- News: `GET https://financialmodelingprep.com/api/v4/general_news?page=0&apikey={key}`

**Files:**
- Create: `backend/fetchers/fmp.py`
- Create: `backend/tests/fetchers/test_fmp.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_fmp.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.fmp import FMPFetcher

_CALENDAR = [
    {"date": "2026-04-23 12:30:00", "country": "US", "event": "Initial Jobless Claims",    "impact": "High",   "previous": "215K", "estimate": "210K", "actual": None},
    {"date": "2026-04-24 14:00:00", "country": "US", "event": "Core PCE Price Index m/m",  "impact": "High",   "previous": "0.3%", "estimate": "0.3%", "actual": None},
    {"date": "2026-04-23 10:00:00", "country": "EU", "event": "Flash Manufacturing PMI",   "impact": "Medium", "previous": "46.5", "estimate": "47.0", "actual": None},
]
_NEWS = [
    {"title": "Fed holds rates steady amid inflation concerns", "publishedDate": "2026-04-22 08:00:00", "site": "Reuters",   "url": "https://reuters.com/1"},
    {"title": "ECB signals possible June cut",                  "publishedDate": "2026-04-22 07:30:00", "site": "Bloomberg", "url": "https://bloomberg.com/2"},
]


def _mock_client(calendar: list, news: list) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = calendar if "economic_calendar" in url else news
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_fmp_returns_empty_when_no_key():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="", client=client)
    snippets = await fetcher.fetch()
    assert snippets == []


@pytest.mark.asyncio
async def test_fmp_returns_calendar_snippet():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    cal = next(s for s in snippets if "Economic Calendar" in s)
    assert "Jobless Claims" in cal
    assert "Core PCE" in cal


@pytest.mark.asyncio
async def test_fmp_high_impact_only_in_calendar():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    cal = next(s for s in snippets if "Economic Calendar" in s)
    assert "Flash Manufacturing PMI" not in cal


@pytest.mark.asyncio
async def test_fmp_news_snippet():
    client = _mock_client(_CALENDAR, _NEWS)
    fetcher = FMPFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    news = next(s for s in snippets if "News" in s)
    assert "Fed holds rates" in news
    assert "ECB signals" in news
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_fmp.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement FMPFetcher**

Create `backend/fetchers/fmp.py`:

```python
import datetime
import httpx
from backend.fetchers.base import BaseFetcher

_BASE = "https://financialmodelingprep.com/api"


class FMPFetcher(BaseFetcher):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        if not self._api_key:
            return []
        snippets = []
        cal = await self._fetch_calendar()
        if cal:
            snippets.append(cal)
        news = await self._fetch_news()
        if news:
            snippets.append(news)
        return snippets

    async def _fetch_calendar(self) -> str:
        today = datetime.date.today()
        params = {
            "from": today.isoformat(),
            "to": (today + datetime.timedelta(days=7)).isoformat(),
            "apikey": self._api_key,
        }
        resp = await self._client.get(f"{_BASE}/v3/economic_calendar", params=params)
        resp.raise_for_status()
        events = [e for e in resp.json() if (e.get("impact") or "").lower() == "high"]
        if not events:
            return ""
        lines = ["## Economic Calendar (High Impact, Next 7 Days)"]
        for e in events[:10]:
            date_str = e.get("date", "")[:10]
            country = e.get("country", "")
            name = e.get("event", "")
            prev = e.get("previous") or "—"
            est = e.get("estimate") or "—"
            lines.append(f"- [{date_str}] {country} — {name} | prev: {prev} | est: {est}")
        return "\n".join(lines)

    async def _fetch_news(self) -> str:
        resp = await self._client.get(f"{_BASE}/v4/general_news", params={"page": 0, "apikey": self._api_key})
        resp.raise_for_status()
        articles = resp.json()[:10]
        if not articles:
            return ""
        lines = ["## Recent Market News (FMP)"]
        for a in articles:
            date_str = a.get("publishedDate", "")[:10]
            title = a.get("title", "")
            site = a.get("site", "")
            lines.append(f"- [{date_str}] {title} ({site})")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_fmp.py -v
```

Expected: all 4 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/fmp.py backend/tests/fetchers/test_fmp.py
git commit -m "feat: add FMPFetcher — economic calendar (high-impact) + news"
```

---

## Task 9: Alpha Vantage Fetcher

Fetches news with sentiment scores for key tickers. Returns 1 snippet with top headlines. Returns `[]` if `api_key` is empty.

API: `GET https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={tickers}&sort=LATEST&limit=20&apikey={key}`

**Files:**
- Create: `backend/fetchers/alpha_vantage.py`
- Create: `backend/tests/fetchers/test_alpha_vantage.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_alpha_vantage.py`:

```python
import pytest
from unittest.mock import MagicMock
from backend.fetchers.alpha_vantage import AlphaVantageFetcher

_FIXTURE = {
    "feed": [
        {"title": "Gold rallies on dollar weakness",  "source": "Reuters",   "time_published": "20260422T080000", "overall_sentiment_label": "Bullish", "overall_sentiment_score": "0.35"},
        {"title": "Fed holds rates, dollar steady",   "source": "Bloomberg", "time_published": "20260422T075000", "overall_sentiment_label": "Neutral",  "overall_sentiment_score": "0.05"},
        {"title": "EUR/USD breaks key resistance",    "source": "FXStreet",  "time_published": "20260422T074000", "overall_sentiment_label": "Bullish", "overall_sentiment_score": "0.28"},
    ]
}


def _mock_client(data: dict) -> MagicMock:
    async def fake_get(url: str, params=None, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    client = MagicMock()
    client.get = fake_get
    return client


@pytest.mark.asyncio
async def test_alphavantage_empty_when_no_key():
    client = _mock_client(_FIXTURE)
    fetcher = AlphaVantageFetcher(api_key="", client=client)
    snippets = await fetcher.fetch()
    assert snippets == []


@pytest.mark.asyncio
async def test_alphavantage_returns_one_snippet():
    client = _mock_client(_FIXTURE)
    fetcher = AlphaVantageFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    assert len(snippets) == 1


@pytest.mark.asyncio
async def test_alphavantage_snippet_contains_headlines():
    client = _mock_client(_FIXTURE)
    fetcher = AlphaVantageFetcher(api_key="test_key", client=client)
    snippets = await fetcher.fetch()
    assert "Gold rallies" in snippets[0]
    assert "Bullish" in snippets[0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_alpha_vantage.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement AlphaVantageFetcher**

Create `backend/fetchers/alpha_vantage.py`:

```python
import httpx
from backend.fetchers.base import BaseFetcher

_URL = "https://www.alphavantage.co/query"
_TICKERS = "FOREX:EURUSD,FOREX:GBPUSD,FOREX:USDJPY,COMMODITY:XAU,CRYPTO:BTC,CRYPTO:ETH"


class AlphaVantageFetcher(BaseFetcher):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        super().__init__(client)
        self._api_key = api_key

    async def fetch(self) -> list[str]:
        if not self._api_key:
            return []
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": _TICKERS,
            "sort": "LATEST",
            "limit": 20,
            "apikey": self._api_key,
        }
        resp = await self._client.get(_URL, params=params)
        resp.raise_for_status()
        feed = resp.json().get("feed", [])
        if not feed:
            return []
        lines = ["## News Sentiment (Alpha Vantage)"]
        for item in feed[:10]:
            date_str = item.get("time_published", "")[:8]
            title = item.get("title", "")
            source = item.get("source", "")
            sentiment = item.get("overall_sentiment_label", "Neutral")
            score = float(item.get("overall_sentiment_score", 0))
            lines.append(f"- [{date_str}] [{sentiment} {score:+.2f}] {title} ({source})")
        return ["\n".join(lines)]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/fetchers/test_alpha_vantage.py -v
```

Expected: all 3 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add backend/fetchers/alpha_vantage.py backend/tests/fetchers/test_alpha_vantage.py
git commit -m "feat: add AlphaVantageFetcher — news sentiment headlines"
```

---

## Task 10: Context Aggregator

Maps each of the 10 pairs to its relevant fetchers and returns one combined markdown context string per pair. This is the single call-site for Plan 3 (AI Analyzer).

**Files:**
- Create: `backend/fetchers/aggregator.py`
- Modify: `backend/fetchers/__init__.py`
- Create: `backend/tests/fetchers/test_aggregator.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/fetchers/test_aggregator.py`:

```python
import pytest
from backend.fetchers.aggregator import ContextAggregator


class FakeSecret:
    def __init__(self, v: str):
        self._v = v
    def get_secret_value(self) -> str:
        return self._v


class FakeSettings:
    fred_api_key         = FakeSecret("fred_key")
    fmp_api_key          = FakeSecret("")
    alpha_vantage_api_key = FakeSecret("")
    coingecko_api_key    = FakeSecret("")


@pytest.mark.asyncio
async def test_aggregator_unknown_pair_raises():
    agg = ContextAggregator(FakeSettings())
    with pytest.raises(ValueError, match="Unknown pair"):
        await agg.fetch_for_pair("XXX/YYY")


@pytest.mark.asyncio
async def test_aggregator_xauusd_calls_fred_and_cftc(monkeypatch):
    from unittest.mock import AsyncMock
    agg = ContextAggregator(FakeSettings())

    monkeypatch.setattr(agg._fetchers["XAU/USD"]["fred"],       "fetch", AsyncMock(return_value=["## US 10Y\n- Current: 4.32%"]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["cftc"],       "fetch", AsyncMock(return_value=["## COT Gold\n- Net: +140,000"]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["fear_greed"], "fetch", AsyncMock(return_value=["## Fear\n- Value: 72"]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["fmp"],        "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["XAU/USD"]["alpha_vantage"], "fetch", AsyncMock(return_value=[]))

    context = await agg.fetch_for_pair("XAU/USD")
    assert "US 10Y" in context
    assert "COT Gold" in context
    assert "Fear" in context


@pytest.mark.asyncio
async def test_aggregator_btcusd_calls_coingecko_and_fear(monkeypatch):
    from unittest.mock import AsyncMock
    agg = ContextAggregator(FakeSettings())

    monkeypatch.setattr(agg._fetchers["BTC/USD"]["coingecko"],  "fetch", AsyncMock(return_value=["## BTC/USD\n- Price: $68,500"]))
    monkeypatch.setattr(agg._fetchers["BTC/USD"]["fear_greed"], "fetch", AsyncMock(return_value=["## Fear\n- Value: 72"]))
    monkeypatch.setattr(agg._fetchers["BTC/USD"]["fred"],       "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["BTC/USD"]["fmp"],        "fetch", AsyncMock(return_value=[]))

    context = await agg.fetch_for_pair("BTC/USD")
    assert "BTC/USD" in context
    assert "Fear" in context


@pytest.mark.asyncio
async def test_aggregator_eurusd_includes_ecb(monkeypatch):
    from unittest.mock import AsyncMock
    agg = ContextAggregator(FakeSettings())

    monkeypatch.setattr(agg._fetchers["EUR/USD"]["ecb"],  "fetch", AsyncMock(return_value=["## ECB Deposit\n- Current: 4.0%"]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["fred"], "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["cftc"], "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["fmp"],  "fetch", AsyncMock(return_value=[]))
    monkeypatch.setattr(agg._fetchers["EUR/USD"]["alpha_vantage"], "fetch", AsyncMock(return_value=[]))

    context = await agg.fetch_for_pair("EUR/USD")
    assert "ECB Deposit" in context
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/fetchers/test_aggregator.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement ContextAggregator**

Create `backend/fetchers/aggregator.py`:

```python
import asyncio
import httpx
from backend.fetchers.fred import FREDFetcher
from backend.fetchers.ecb import ECBFetcher
from backend.fetchers.boe import BoEFetcher
from backend.fetchers.coingecko import CoinGeckoFetcher
from backend.fetchers.fear_greed import FearGreedFetcher
from backend.fetchers.cftc import CftcFetcher
from backend.fetchers.fmp import FMPFetcher
from backend.fetchers.alpha_vantage import AlphaVantageFetcher


class ContextAggregator:
    def __init__(self, settings) -> None:
        client = httpx.AsyncClient(timeout=30.0)
        fred         = FREDFetcher(api_key=settings.fred_api_key.get_secret_value(), client=client)
        ecb          = ECBFetcher(client=client)
        boe          = BoEFetcher(client=client)
        coingecko    = CoinGeckoFetcher(api_key=settings.coingecko_api_key.get_secret_value(), client=client)
        fear_greed   = FearGreedFetcher(client=client)
        cftc         = CftcFetcher(client=client)
        fmp          = FMPFetcher(api_key=settings.fmp_api_key.get_secret_value(), client=client)
        alpha_vantage = AlphaVantageFetcher(api_key=settings.alpha_vantage_api_key.get_secret_value(), client=client)

        # Fetcher instances are shared across pairs — one HTTP client, no duplicate calls.
        self._fetchers: dict[str, dict] = {
            "XAU/USD": {"fred": fred, "cftc": cftc, "fear_greed": fear_greed, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "EUR/USD": {"fred": fred, "ecb": ecb, "cftc": cftc, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "GBP/USD": {"fred": fred, "boe": boe, "cftc": cftc, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "USD/JPY": {"fred": fred, "cftc": cftc, "fmp": fmp, "alpha_vantage": alpha_vantage},
            "AUD/USD": {"fred": fred, "coingecko": coingecko, "cftc": cftc, "fmp": fmp},
            "USD/CAD": {"fred": fred, "cftc": cftc, "fmp": fmp},
            "USD/CHF": {"fred": fred, "cftc": cftc, "fmp": fmp},
            "NZD/USD": {"fred": fred, "cftc": cftc, "fmp": fmp},
            "BTC/USD": {"coingecko": coingecko, "fear_greed": fear_greed, "fred": fred, "fmp": fmp},
            "ETH/USD": {"coingecko": coingecko, "fear_greed": fear_greed, "fmp": fmp},
        }

    async def fetch_for_pair(self, pair: str) -> str:
        if pair not in self._fetchers:
            raise ValueError(f"Unknown pair: {pair}. Valid: {list(self._fetchers.keys())}")
        results = await asyncio.gather(
            *[f.fetch() for f in self._fetchers[pair].values()],
            return_exceptions=True,
        )
        snippets: list[str] = []
        for r in results:
            if isinstance(r, list):
                snippets.extend(r)
        return "\n\n".join(snippets)
```

- [ ] **Step 4: Update `backend/fetchers/__init__.py`**

```python
from backend.fetchers.fred import FREDFetcher
from backend.fetchers.ecb import ECBFetcher
from backend.fetchers.boe import BoEFetcher
from backend.fetchers.coingecko import CoinGeckoFetcher
from backend.fetchers.fear_greed import FearGreedFetcher
from backend.fetchers.cftc import CftcFetcher
from backend.fetchers.fmp import FMPFetcher
from backend.fetchers.alpha_vantage import AlphaVantageFetcher
from backend.fetchers.aggregator import ContextAggregator

__all__ = [
    "FREDFetcher",
    "ECBFetcher",
    "BoEFetcher",
    "CoinGeckoFetcher",
    "FearGreedFetcher",
    "CftcFetcher",
    "FMPFetcher",
    "AlphaVantageFetcher",
    "ContextAggregator",
]
```

- [ ] **Step 5: Run all fetcher tests**

```bash
cd backend && uv run pytest tests/fetchers/ -v
```

Expected: all tests across all test files `PASSED`.

- [ ] **Step 6: Run full test suite — no regressions**

```bash
cd backend && uv run pytest -v
```

Expected: all existing model tests + all fetcher tests pass.

- [ ] **Step 7: Commit and push**

```bash
git add backend/fetchers/ backend/tests/fetchers/
git commit -m "feat: add ContextAggregator — maps 10 pairs to fetchers, returns combined markdown context"
git push
```

---

## Self-Review

**Spec coverage:**

| Spec requirement (§4) | Covered by |
|---|---|
| FRED: US10Y, Real Yield, Fed rate, CPI YoY, Unemployment, DXY | Task 2 — 6 series |
| ECB SDMX: EUR deposit rate, HICP | Task 3 |
| BoE: GBP bank rate | Task 4 |
| CoinGecko: BTC/ETH price + metrics | Task 5 |
| Fear & Greed: crypto sentiment | Task 6 |
| CFTC: COT for Gold + 7 FX/BTC contracts | Task 7 |
| FMP: economic calendar + news (paid, graceful if missing) | Task 8 |
| Alpha Vantage: news sentiment (paid, graceful if missing) | Task 9 |
| Data normalization → markdown snippets (§4.3 format) | All fetchers return `list[str]` |
| Pipeline-then-analyze (§3.1) | Aggregator compiles all snippets; Claude sees only pre-processed text |
| 10 pairs, each mapped to relevant sources | Task 10 `_fetchers` dict |

**Placeholder scan:** No TBD/TODO/placeholder text. All code blocks are complete.

**Type consistency:** `fetch() -> list[str]` used consistently in all 8 fetchers and base class. `ContextAggregator.fetch_for_pair(pair: str) -> str` signature matches test calls exactly.
