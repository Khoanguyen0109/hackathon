# Architecture — Hackathon Repo

Long-form companion to the rules in `.cursor/rules/`. Read this when you need to decide *where* a new piece of code belongs.

## The two stacks at a glance

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Restaurant Manager App (UI)                       │
│            (browser, drag-and-drop deployment chart grid)               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP (JSON)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Node.js API                                  │
│   • CRUD: stores, stations, tasks, crew, deployment charts              │
│   • Auth scoping by store_id                                            │
│   • Proxies AI requests, validates AI responses                         │
│   • Writes audit log (suggestion vs. final assignment)                  │
└──────────┬──────────────────────────────────────────┬───────────────────┘
           │ SQL                                     │ HTTP (JSON)
           ▼                                          ▼
   ┌───────────────┐                 ┌─────────────────────────────────┐
   │    SQLite     │                 │       Python AI Service         │
   │  (single file)│                 │  • Builds prompts (no PII)      │
   └───────────────┘                 │  • Calls Ollama                 │
                                     │  • Parses + validates outputs   │
                                     │  • (Optionally) calls           │
                                     │    ai_forecaster for demand     │
                                     └────────────┬────────────────────┘
                                                  │ HTTP
                                                  ▼
                                          ┌──────────────┐
                                          │    Ollama    │
                                          │ (local LLM)  │
                                          └──────────────┘
```

## How `ai-forecaster` plugs in

`ai-forecaster` is the **demand-prediction substrate**. It is a self-contained Python package; the deployment-chart Python AI service depends on it, never the reverse.

Reusable flow:

1. Historical sales/visitor data (Excel today, DB later) → `ExcelTimeSeriesLoader` → `TimeSeries`.
2. `Forecaster.forecast_many(...)` → `ForecastResult` per series (mean / median / quantiles).
3. The deployment AI service feeds the forecast (e.g., predicted Saturday lunch transactions) into the prompt as one more *external factor* alongside weather/events.
4. Ollama returns staffing-level suggestions per shift × station; the AI service validates and returns structured JSON to the Node API.

If a feature needs forecasting, **extend `ai-forecaster`** rather than reimplementing model code in the deployment service.

## Where things go (decision table)

| If you need to... | Put it here |
|---|---|
| Add a new Excel I/O option (sheets, columns, freq) | `src/ai_forecaster/data_loader.py` |
| Support a new HF/Chronos checkpoint or backend | `src/ai_forecaster/model.py` |
| Change forecast aggregation / export format | `src/ai_forecaster/forecaster.py` |
| Add a new CLI flag for `ai-forecast` | `src/ai_forecaster/cli.py` |
| Plotting tweaks | `src/ai_forecaster/visualization.py` |
| New REST endpoint for the manager UI | Node.js API (alongside `index.js`) |
| Schema change (new table/column) | Update `schema.md` + migrations + Node DAL |
| Prompt engineering for staffing | Python AI service (`src/deployment_ai/`, to be created) |
| Mock data for weather/events/holidays | Python AI service, in a clearly-named `mocks/` module |
| LLM response validation/sanitization | **Both** sides (Python AI service first, Node API again) |
| New tests | `tests/` (Python) — keep them mocked / no network |

## Boundaries to respect

- **No HF / torch imports outside `ai_forecaster.model`.** Forecasting orchestration goes through `ChronosForecastModel`.
- **No PII into prompts.** The Python AI service receives anonymized operational context only. Crew names stay in SQLite, never reach the LLM.
- **No live external APIs in hackathon.** Weather / events / holidays / promotions are mock data. The shape of the mock should match a future real provider so swapping it later is mechanical.
- **Single source of truth for the schema.** `schema.md` (project root, per PRD §7). Do not re-declare table shapes in code comments.

## Dev environments

- Python: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && pip install -e .`
- Docker (full forecaster): `docker compose run --rm ai-forecaster`
- Tests: `pytest` (mocked, fast).
- Node: scaffolded; expand `package.json` and add Express/Fastify when introducing the API.
