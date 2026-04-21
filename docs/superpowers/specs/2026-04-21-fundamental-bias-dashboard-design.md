# Fundamental Bias Trading Dashboard V1 — Design Document

**Auteur:** ClaudeBot (Opus 4.7) met user
**Datum:** 2026-04-21
**Status:** Approved — klaar voor implementation plan
**Taal:** Ontwerp in Engels/Nederlands mix (conform voorkeur user)

---

## 1. Overview

Een persoonlijk, lokaal draaiend web-dashboard dat **fundamentele handels-bias** per pair genereert voor een daytrader. Het dashboard combineert macro-economische data, kalenderevents, nieuws, rendementen, COT-posities en sentiment tot één Bullish / Bearish / Neutral label per pair per horizon, met conviction-percentage en de top-3 drijvende factoren.

Het dashboard is **geen signaal-generator voor entries/exits**. Het is een "macro-huiswerk-machine" die de fundamentele bias synthetiseert, zodat de user vervolgens met **technische analyse** de timing bepaalt.

### 1.1 User Profile

- Nederlandstalige daytrader
- Handelt voornamelijk XAU/USD, daarna FX-majors en BTC/ETH
- Kent Python beperkt (laat Claude meestal coderen)
- Heeft Next.js nog nooit gebruikt
- Heeft een Pro plan bij Anthropic
- Werkt graag in **Obsidian** — wil data daar opslaan

### 1.2 Scope (in)

10 pairs, drie horizons (Intraday / Weekly / Macro), zelflerende feedback-loop, vier edge-features, Obsidian-storage, lokaal-op-Mac architectuur.

### 1.3 Non-Goals (out)

- **Geen** auto-trading / broker-integratie
- **Geen** entry/exit signalen of TP/SL suggesties
- **Geen** cloud-hosting in V1 (draait lokaal op de Mac)
- **Geen** multi-user / auth-systeem
- **Geen** echte machine-learning modellen (de "self-learning" is prompt-memory-gebaseerd, zie §8)
- **Geen** mobile-app

---

## 2. De 10 Kernbeslissingen (samenvatting van brainstorm)

| # | Onderwerp | Keuze |
|---|---|---|
| 1 | Pairs | XAU/USD, EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, NZD/USD, BTC/USD, ETH/USD (10 totaal) |
| 2 | Horizons | Intraday + Weekly + Macro (alle 3 zichtbaar per pair) |
| 3 | Visuele stijl | **C — Hybrid (Dark + Modern)** — donkere achtergrond, glass-cards, gradient accenten |
| 4 | Update-frequentie | 3× per dag: 08:00, 14:00, 22:00 CET + on-demand refresh |
| 5 | Nieuws-diepte | Top 10 headlines per digest + AI-summary per pair (Haiku filtert, Opus synthetiseert) |
| 6 | Self-learning | Ja — dagelijkse evaluatie, Memory Bank per pair, thumbs-up/down feedback |
| 7 | Storage | **Obsidian vault** met YAML-frontmatter (geen SQLite) |
| 8 | AI-aanpak | **Aanpak 2 — "Sweet Spot":** Pipeline-then-analyze, Opus 4.7 + Haiku combi, prompt caching |
| 9 | Edge-features | Alle 4 toegevoegd: Risk Regime Gauge, Live Ticker, Conflict Warnings, Event Countdown |
| 10 | Build-workflow | v0.dev voor UI-scaffolding + Claude Code voor full-stack integratie |

---

## 3. Architecture (5-layer)

```
Layer 1 — EXTERNAL DATA SOURCES
  FMP Premium · Alpha Vantage Premium · FRED · ECB · BoE ·
  CFTC · CoinGecko · Farside · Fear & Greed · BIS
                        |
                        v
Layer 2 — PYTHON BACKEND (lokaal op Mac)
  [Fetchers (normalize)] -> [Scheduler (08/14/22 CET)] -> [AI Analyzer (Opus + Haiku)]
                        |
                        v
Layer 3 — OBSIDIAN VAULT STORAGE (lokaal)
  vault/biases/YYYY-MM-DD/{pair}-{horizon}.md
  vault/memory/{pair}.md
  vault/news/YYYY-MM-DD-digest.md
  vault/reflections/YYYY-MM-DD.md
                        |
                        v
Layer 4 — FASTAPI (localhost:8000)
  /api/biases  /api/news  /api/events  /api/feedback
  /api/regime  /api/ticker  /api/refresh
                        |
                        v
Layer 5 — NEXT.JS FRONTEND (localhost:3000)
  10 pair-cards · 3 horizons · Risk Gauge · Ticker · News
```

### 3.1 Keuze: Pipeline-then-analyze (Aanpak 2)

We bouwen **geen** agentic tool-use systeem waar Claude zelf besluit welke data hij ophaalt. In plaats daarvan:

1. Python haalt **alle relevante data** op per pair (deterministisch, getrapt, robuust)
2. Python **normaliseert** naar platte tekst-snippets (per factor een stukje markdown)
3. Claude krijgt de voorbewerkte context → schrijft bias + conviction + factors
4. Output wordt gevalideerd (JSON schema) → in Obsidian gezet

**Waarom:** goedkoper, sneller, deterministisch, debugbaar, cache-vriendelijk.

---

## 4. Data Sources (Layer 1)

### 4.1 Paid (essentieel)

| Source | Doel | Kosten | Auth |
|---|---|---|---|
| **FMP Premium** | Economische kalender, COT rapporten, company news | ~€45/mo | API key |
| **Alpha Vantage Premium** | Nieuws + sentiment scoring | ~€50/mo | API key |

### 4.2 Free (kritiek)

| Source | Doel | Rate limit |
|---|---|---|
| **FRED** (St. Louis Fed) | US rates, yields, CPI, NFP, US10Y Real | 120/min |
| **ECB SDMX** | EUR rates, HICP, depo-rate | onbeperkt |
| **BoE IADB** | GBP bank-rate, gilt-yields | onbeperkt |
| **CFTC** | COT report (weekly, speculative positioning) | 1× per week |
| **CoinGecko Demo** | BTC/ETH prijs + metrics | 30/min |
| **Farside Investors** | BTC spot-ETF flows (scrape) | voorzichtig |
| **Fear & Greed Index** | Crypto sentiment | API |
| **BIS** | USD effective exchange rates | dagelijks |

### 4.3 Data-normalisatie

Elke fetcher output = markdown-snippet met de vorm:

```markdown
## US10Y Real Yield
- Current: 1.87%
- Change 1d: -0.08bps
- Change 5d: -0.14bps
- Percentile 1y: 34th
- Signal (voor XAU): **BULLISH** — reële rente zakt
```

Claude ziet alleen deze pre-verwerkte snippets, niet ruwe CSVs.

---

## 5. Obsidian Vault Structure (Layer 3)

### 5.1 Directory layout

```
vault/
├── biases/
│   └── 2026-04-21/
│       ├── xau-usd-intraday.md
│       ├── xau-usd-weekly.md
│       ├── xau-usd-macro.md
│       ├── eur-usd-intraday.md
│       └── ... (10 pairs × 3 horizons = 30 files/dag)
├── memory/
│   ├── xau-usd.md          <- accumuleert lessons learned per pair
│   ├── eur-usd.md
│   └── ...
├── news/
│   └── 2026-04-21-digest.md
├── reflections/
│   └── 2026-04-21.md       <- dagelijkse zelfreflectie
└── events/
    └── 2026-04-21-calendar.md
```

### 5.2 Bias-file frontmatter schema

```yaml
---
pair: XAU/USD
horizon: intraday
timestamp: 2026-04-21T08:00:00+02:00
bias: BULLISH
conviction: 78
factors:
  - label: "US10Y Real yields dalen (-8bps 5d)"
    weight: 0.35
    direction: bullish
  - label: "DXY zakt door 104.20 support"
    weight: 0.28
    direction: bullish
  - label: "Geopolitieke risk-premie (Red Sea)"
    weight: 0.22
    direction: bullish
conflict_with:
  - macro           # macro horizon is BEARISH -> conflict badge
model: claude-opus-4-7
prompt_cache_hit: true
news_refs:
  - "news/2026-04-21-digest.md#fed-cut"
feedback: null      # wordt gevuld door user via thumbs up/down
---

# XAU/USD — Intraday Bias — 2026-04-21 08:00 CET

**Bias:** BULLISH (78% conviction)

## Reasoning
...markdown body met de volledige analyse door Opus...

## Top drivers
1. **Reële rente lager** — de 10-year TIPS yield zakt voor de 4e dag op rij...
2. **DXY zwakte** — dollar-index breekt door 104.20...
3. **Geopolitieke premie** — spanningen rond Red Sea blijven...

## Risks to thesis
- Verrassend hoge US CPI print vandaag 14:30 CET kan DXY opstuwen
- Fed-speaker hawkish -> real yields kunnen rebouncen

## Data snapshot
(table met alle factor-waarden — voor reproduceerbaarheid)
```

### 5.3 Memory file

`vault/memory/xau-usd.md` accumuleert:
- Lessons learned (wat werkte, wat niet)
- Recurring patterns (bv. "Gold faalt vaak te breken boven 2400 bij US CPI ochtenden")
- User feedback quotes (thumbs-down met user-annotatie)

Dit file wordt **in context gegeven** aan Claude bij elke nieuwe analyse → adaptive behavior.

---

## 6. AI Analysis Pipeline (Layer 2)

### 6.1 Model-splitsing

| Taak | Model | Waarom |
|---|---|---|
| Nieuws filteren / dedup / relevance-scoring | **Haiku 4.5** | Hoog volume, simpele classificatie |
| Economic-event parsing | **Haiku 4.5** | Structuur-extractie |
| Bias-synthese per pair/horizon | **Opus 4.7** | Diep redeneren, conflict-detectie |
| Dagelijkse reflectie (alle pairs) | **Opus 4.7** | Long-context overview |

### 6.2 Prompt Caching Strategy

Caches met 5-min TTL en 1024-token breakpoint minimum. Per Opus-call 4 cache-breakpoints:

1. **System prompt** (macro framework, gold thesis, DXY framework) — **statisch**
2. **Pair-specifiek briefing** (hoe XAU reageert op real yields vs. DXY vs. risk-on/off) — **statisch per pair**
3. **Memory bank** (lessons learned voor deze pair) — **semi-statisch**
4. **Data snapshot** (kalendersnapshot, nieuws digest) — **dynamisch, niet gecached**

Verwachte cache-hit-rate na warm-up: ~85%. Bespaart geschat **70-80%** op Opus-tokens.

### 6.3 Output-contract

Claude wordt gedwongen via structured output (JSON-schema) om exact dit te produceren:

```json
{
  "bias": "BULLISH | BEARISH | NEUTRAL",
  "conviction": "0-100",
  "factors": [
    {"label": "...", "weight": "0.0-1.0", "direction": "bullish | bearish"}
  ],
  "risks_to_thesis": ["..."],
  "reasoning": "<markdown>"
}
```

Validator faalt luid als schema breekt → retry met Opus op lagere temperature.

---

## 7. Frontend (Layer 5)

### 7.1 Visuele stijl — C (Hybrid Dark + Modern)

- Donkere achtergrond (`#0f172a` → `#1e293b` gradient)
- Glass-cards (`rgba(255,255,255,0.05)` + subtle border)
- Groen `#22c55e` bullish / Rood `#ef4444` bearish / Amber `#f59e0b` neutral
- Afgeronde hoeken (`rounded-xl`)
- Inter font voor body, JetBrains Mono voor tickers

### 7.2 Layout

Referentie: `.superpowers/brainstorm/86200-1776765974/content/layout-v2.html`

**Topbar (sticky)** — Live Ticker:
- DXY · US10Y Real · VIX · Fear&Greed Crypto · Laatst-bijgewerkt badge

**Hero sectie** — Risk Regime Gauge:
- Horizontale meter: RISK-OFF (links) ↔ RISK-ON (rechts)
- Needle op 0-100 score
- Composiet-factoren zichtbaar bij hover: VIX · AUD/JPY · HYG/LQD · ES-futures
- Label: "Mild Risk-On" / "Strong Risk-Off" / etc.

**Countdown-strip:**
- Rood: Next high-impact event (bv. "US CPI over 1u 42m")
- Kleuren per impact: Rood High / Oranje Medium / Wit Low

**Pair-grid (5×2):**
- 10 cards met:
  - Pair symbol + flags
  - **Grote Bias-label** (BULLISH/BEARISH/NEUTRAL)
  - Conviction % + progress-bar
  - Top 3 factors (compact)
  - Tab-switcher: [Intraday] [Weekly] [Macro]
  - CONFLICT badge als horizons disagreeable
  - Thumbs up / thumbs down feedback-knoppen

**News-sectie:**
- Top 10 gefilterde headlines
- Per item: source · tijd · sentiment-badge · relevante pairs (chips)
- Click → expanded summary (AI-samenvatting in NL)

**Events-sectie:**
- Kalender van vandaag + morgen
- Per event: tijd · land · naam · impact · previous · forecast · actual (na release)

**Reflections-paneel (collapsible):**
- Wat Claude's reflectie van gisteren was
- Accuracy-score trend

### 7.3 Stack

- Next.js 15 App Router
- Tailwind CSS + `shadcn/ui` voor base components
- TanStack Query voor data-fetching (auto-refetch op `/api/refresh`)
- Recharts voor de Risk Gauge
- Zustand voor lokale UI-state (geselecteerde horizon per pair)

---

## 8. Self-Learning Loop

### 8.1 Hoe het werkt (eerlijk beschreven)

Dit is **geen** echte ML. Het is een **prompt-memory-feedback** loop:

1. **Dagelijkse reflectie** (22:00 CET):
   - Opus 4.7 leest alle biases van vandaag + markt-bewegingen van de dag
   - Beoordeelt: waar zat het goed? waar zat het fout? welke factor overschat/onderschat?
   - Schrijft een reflection in `vault/reflections/YYYY-MM-DD.md`

2. **Memory Bank update** (wekelijks, zondag):
   - Opus leest 7 reflections + user-feedback (thumbs up/down)
   - Distilleert **concrete lessen per pair** in `vault/memory/{pair}.md`
   - Voorbeeld lesson: *"XAU/USD bullish-calls met conviction >75% gebaseerd op real-yield-move alleen faalden 4/10 als DXY tegelijk steeg. -> Down-weight pure-yield signalen bij DXY-divergentie."*

3. **Bij volgende analyse:**
   - Memory bank wordt in de cached system prompt gestopt
   - Claude past het toe op nieuwe data

### 8.2 Overfitting-risico (belangrijk)

Zonder temperen kan de loop "mode-collapsen" op recente markt-regime. Mitigaties:
- Memory-bank gecapt op **max 20 lessons per pair** (oude weggeknipt)
- Weekly review vraagt expliciet: *"Zijn deze lessons regime-specifiek of structureel?"*
- User kan lessons handmatig bewerken/verwijderen in Obsidian

### 8.3 Feedback

- Thumbs up / thumbs down per bias in UI → schrijft naar bias-frontmatter
- Thumbs-down opent tekstveld voor reden ("te vroeg bullish, DXY bleef sterk")
- Alle feedback wordt in weekly-review meegenomen

---

## 9. Edge Features (de 4 toegevoegde)

### 9.1 Risk Regime Gauge

Composite score 0-100 voor **RISK-OFF ↔ RISK-ON** staat van de markt:

```
score = w1 · z(VIX, inverted)       # lager VIX = risk-on
      + w2 · z(AUD/JPY change)      # stijgend = risk-on
      + w3 · z(HYG/LQD ratio)       # credit spreads: dalend = risk-on
      + w4 · z(ES-futures mom 5d)   # positief = risk-on
```

Gewichten in V1: gelijk (0.25 each), in V2 kunnen we leren.

**Waarom:** daytrader kan snel zien of markt-context risk-on of risk-off is → kleurt alle pair-biases.

### 9.2 Conflict Warnings

Als een pair Intraday-bias en Macro-bias tegengesteld zijn → CONFLICT badge op de card.

**Waarom:** voorkomt dat je "blind bullish" gaat op een intraday-signaal terwijl macro al dagen bearish is. Conflict = trade met kleinere size of wacht.

### 9.3 Live Ticker (sticky topbar)

Real-time-ish (5 min refresh): **DXY · US10Y Real · VIX · Fear&Greed**.

**Waarom:** deze 4 waardes verklaren 70%+ van cross-asset moves. Direct in het zicht.

### 9.4 Event Countdown

Rode countdown naar volgende high-impact event.

**Waarom:** als CPI in <2u is → niet trade openen op stale bias. Forceert timing-awareness.

---

## 10. Build Workflow (Layer 5 + Integration)

### 10.1 Gecombineerde aanpak — v0.dev + Claude Code

**Fase A: UI-scaffolding via v0.dev** (dag 1-2)
- Upload `layout-v2.html` mockup naar v0.dev
- Laat v0 Next.js + Tailwind + shadcn/ui componenten genereren
- Download de repo-skeleton

**Fase B: Backend bouwen in Claude Code** (dag 3-7)
- Python fetchers, Obsidian writer, FastAPI, scheduler
- AI pipeline met prompt caching
- Tests per fetcher (vcrpy voor HTTP-fixtures)

**Fase C: Frontend ↔ backend integreren in Claude Code** (dag 8-10)
- TanStack Query hooks → FastAPI endpoints
- Real-time ticker polling
- Feedback-submissie

**Fase D: Dogfood + iterate** (week 2+)
- Dagelijks gebruiken, reflections lezen, lessons finetunen

### 10.2 Waarom niet puur Claude Design?

Claude Designs was overwogen, maar:
- Minder native Next.js conventies
- UI-only → backend moet alsnog in Claude Code
- v0.dev is specifiek gebouwd voor shadcn/ui → sneller productie-klare React

---

## 11. Budget (maandelijks)

| Item | Kosten (€/mo) |
|---|---|
| FMP Premium | 45 |
| Alpha Vantage Premium | 50 |
| Anthropic API (Opus+Haiku, gecached) | 15-40 (sterk afhankelijk van cache-hit) |
| Domain / hosting | 0 (lokaal) |
| Obsidian | 0 (lokaal) |
| **Totaal** | **€110-135/mo** |

**Onverwachte kosten:**
- Alpha Vantage rate-limit hit → upgrade naar hogere tier (~€75/mo)
- Claude-tokens explosie als cache breekt (>300 refreshes/dag) → budget-monitor alarm op $5/dag

---

## 12. Risico's & Waarschuwingen

### 12.1 Gedragsrisico's (voor de trader)

- **Claude is geen crystal ball.** Bias is fundamentele richting, NIET een entry-signaal.
- **Mode collapse risico** als self-learning niet getemperd wordt → Claude herhaalt dezelfde lessen ook wanneer regime kantelt.
- **Over-reliance.** Dashboard moet **aanvulling** zijn op eigen TA, nooit vervanging.
- **Confirmation bias.** Thumbs-up geven aan biases die bij jouw mening passen vervuilt de memory bank.

### 12.2 Technische risico's

- **Rate-limits** bij bursts → implement retry + circuit breaker
- **Obsidian vault race conditions** als zowel Python als Obsidian desktop schrijft → lock-file pattern
- **Cache-miss kosten-explosie** → budget-alarm op Anthropic dashboard
- **Scheduler clock-drift** → gebruik `apscheduler` met absolute tijden, niet relatief

### 12.3 Data-integriteit

- Alle fetches **gelogd** met timestamp, status, bytes
- Failed fetch → `NEUTRAL` + reden in bias-file (niet stilletjes fallbacken)
- Nooit een bias persisten met `model: null`

---

## 13. Success Criteria (V1 "klaar")

1. Dashboard draait lokaal op `http://localhost:3000`
2. 10 pairs × 3 horizons = 30 biases per dag, 3× per dag ververst
3. Elke bias heeft: label, conviction, top-3 factors, reasoning, data-snapshot
4. Obsidian vault wordt correct gevuld (valid YAML, geen corruptie)
5. Frontend toont alle 4 edge-features live
6. Self-learning loop draait (reflection + memory + feedback)
7. Cache-hit-rate Opus calls >70% na week 1
8. Totale kosten blijven <€150/mo
9. User kan 2 weken lang daily gebruiken zonder crash

---

## 14. V2 Extensions (expliciet uit V1)

- Price-alerts (bv. "alert als XAU bias flipt van neutral naar bullish")
- COT-extremes scanner (extreme net-long/short → contra-indicator)
- Economic Surprise Index (Citi-style eigen build)
- Accuracy-tracker dashboard (hit-rate per pair per horizon over tijd)
- Mobile-view
- Multi-user / cloud-sync
- Backtest-mode (run biases tegen historische data)

---

## 15. Open Questions (voor implementation plan)

1. Welke Obsidian-plugin (als enige) moet het vault-schrijven zien zonder interference? → check Dataview, Templater.
2. Hoe te monitoren dat APIs blijven werken zonder handmatig checken? → simple `/healthz` endpoint + daily e-mail?
3. Should news-section ook Nederlandse bronnen pakken (FD, BNR) of strict EN? → default EN, optional NL later.

---

## 16. References & Inspiration

- **Architectuur-mockup:** `.superpowers/brainstorm/82708-1776710591/content/architecture.html`
- **Layout-mockup:** `.superpowers/brainstorm/86200-1776765974/content/layout-v2.html`
- **Visual style keuze:** `.superpowers/brainstorm/82708-1776710591/content/visual-style.html` (optie C)
- **Research-basis:** Reddit r/algotrading, r/Daytrading consensus over fundamental-dashboards (2025-2026); Substack posts van Concoda, The Macro Compass; X threads van @MacroAlf, @INArteCarloDoss; Anthropic prompt caching cookbook

---

**Einde design doc.** Volgende stap: spec self-review → user review → `writing-plans` skill voor implementation plan.
