# ai-forecaster

Drop in an **Excel workbook**, get back a **probabilistic time-series forecast**, powered by a Hugging Face foundation model — no training data and no manual feature engineering required.

The default backend is [Amazon **Chronos**](https://huggingface.co/amazon/chronos-t5-small), a pretrained T5-based foundation model for *zero-shot* probabilistic forecasting. Any Chronos checkpoint published on the HF Hub can be swapped in via a single flag.

---

## Features

- Read univariate **or multi-column** time-series straight from `.xlsx` / `.xls`.
- Auto-detects the timestamp column and every numeric value column.
- Zero-shot forecasting — no training step required.
- Probabilistic output: mean, median, and configurable quantile bands.
- Batched inference for many series at once.
- Exports forecasts back to a multi-sheet Excel workbook (one sheet per series + `_summary`).
- Generates per-series PNG plots with uncertainty bands.
- CLI (`ai-forecast …`) and Python API.

---

## Installation

The recommended runtime is **Python in Docker** — it pins all native deps
(torch, openpyxl, matplotlib backends) and isolates the (large) Hugging Face
cache in a named volume.

### Docker (recommended)

```bash
# Build the image (CPU-only torch by default, ~1.8 GB)
docker build -t ai-forecaster .

# Generate sample data and run a forecast
docker run --rm -it \
    -v "$PWD:/work" \
    -v ai-forecaster-hf-cache:/root/.cache/huggingface \
    --entrypoint python ai-forecaster examples/generate_sample_data.py

docker run --rm -it \
    -v "$PWD:/work" \
    -v ai-forecaster-hf-cache:/root/.cache/huggingface \
    ai-forecaster forecast /work/examples/sample_data.xlsx \
                           --horizon 30 \
                           --output /work/outputs/forecast.xlsx \
                           --plot-dir /work/outputs/plots
```

Or with **docker compose** (drops into a bash shell with the project mounted):

```bash
docker compose run --rm ai-forecaster
# inside the container:
python examples/generate_sample_data.py
ai-forecast forecast examples/sample_data.xlsx --horizon 30
```

The named volume `ai-forecaster-hf-cache` (or `hf-cache` under compose) keeps
downloaded model weights between runs so you only pay the download cost once.

> For a CUDA build, pass the GPU PyTorch wheel index at build time:
> `docker build --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121 -t ai-forecaster:gpu .`
> and run with `--gpus all`.

### Local Python (alternative)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .          # exposes the `ai-forecast` console script
```

> First run will download the Chronos checkpoint from Hugging Face (≈ 200 MB for `chronos-t5-small`). It is cached under `~/.cache/huggingface/`.

---

## Recommended AI stack on Mac M1 (32 GB)

This repo is tuned for Apple Silicon. The default workflow combines a Hugging
Face foundation model with a constraint solver — the LLM does what it's good
at (forecast a continuous demand signal from history) and the solver does
what it's good at (optimise a combinatorial schedule).

| Layer | Choice | Why on M1 32 GB |
|---|---|---|
| **Demand forecasting** | `amazon/chronos-bolt-base` on **MPS** | Chronos-Bolt is ~250× faster than the T5 variants, ~200 M params; runs natively on Apple's Metal backend (`device="mps"`); 32 GB is more than enough headroom. |
| **Shift optimisation** | **Google OR-Tools (CP-SAT)** | CPU-only, native ARM64 wheel. Solves multi-store, multi-employee, multi-day rosters with thousands of binary variables in seconds. |
| **(optional) Schedule narration** | **MLX-LM** + Qwen2.5-7B-Instruct or Llama-3.1-8B | MLX is Apple's Metal-native LLM runtime — these 7-8 B models fit comfortably in 32 GB and run at 30+ tok/s on M1 Pro/Max. |

You don't need a GPU box for this — everything below runs locally on a Mac.

---

## Two supported input shapes

### A) Wide numeric time-series (`forecast`)

The workbook just needs:

1. One column holding **timestamps** (any format `pandas` can parse — auto-detected).
2. One or more columns of **numeric values** (each becomes its own forecast).

Example (`examples/sample_data.xlsx`):

| date       | sales | visitors | revenue |
|------------|-------|----------|---------|
| 2023-01-01 | 102.4 | 503      | 1024.7  |
| 2023-01-02 | 99.8  | 511      | 998.3   |
| …          | …     | …        | …       |

Generate this sample with:

```bash
python examples/generate_sample_data.py
```

### B) Event log + prediction rules (`forecast-events`)

For workbooks like `examples/simulated_event_data_and_rules.xlsx`, which contain:

- **`Tab1_EventTable`** — long-format event log: `store_id, date, time, event, event type`
- **`Tab2_PredictionRules`** — for every `(Event Type, Event)` and `Channel`, a multiplicative `Delta`. `Event = "Any"` is a wildcard that matches any event of that type.

The pipeline:

1. Joins the event log with the rules (handling the `Any` wildcard).
2. For each `(store_id, channel, date)` sums all matching `Delta` values.
3. Builds a daily `demand_index = 1.0 + Σ Delta` time-series per `(store_id, channel)` — `1.00` = no impact, `1.05` = +5% lift, `0.97` = -3% drop.
4. Forecasts every series forward with Hugging Face Chronos.

Example math from the attached workbook:

| Date           | Events for `S0001`                      | `Delivery` index | `Dine-in` index |
|----------------|------------------------------------------|------------------|-----------------|
| 2026-01-03 Sat | rain + Saturday                          | `1 + 0.05 + 0.06 = 1.11` | `1 + (-0.03) + 0.06 = 1.03` |
| 2026-01-05 Mon | rain                                     | `1 + 0.05 = 1.05`        | `1 + (-0.03) = 0.97`        |
| 2026-04-30 Thu | "30th April" (Holiday wildcard)          | `1 + 0.02 = 1.02`        | `1 + 0.02 = 1.02`           |

---

## Quick start — CLI

```bash
# A) wide numeric time-series → forecast every numeric column 30 steps ahead
ai-forecast forecast examples/sample_data.xlsx \
    --horizon 30 \
    --output outputs/forecast.xlsx \
    --plot-dir outputs/plots

# B) event log + rules → daily demand-index forecast per (store, channel)
ai-forecast forecast-events examples/simulated_event_data_and_rules.xlsx \
    --horizon 30 \
    --stores S0001,S0002,S0003 \
    --output outputs/event_forecast.xlsx \
    --plot-dir outputs/event_plots
```

The event-driven command also accepts `--channels`, `--baseline`, `--event-sheet`, `--rules-sheet`, plus all the model/quantile flags below.

Useful flags:

| Flag | Description |
|------|-------------|
| `--horizon / -h` | Number of future steps to predict. |
| `--model` | Any Chronos checkpoint, e.g. `amazon/chronos-t5-large`. |
| `--device` | `cpu`, `cuda`, or `mps`. Auto-detected if omitted. |
| `--quantiles` | Comma-separated quantile levels (default `0.1,0.5,0.9`). |
| `--num-samples` | Trajectories drawn from the predictive distribution. |
| `--freq` | Pandas offset alias to resample to (e.g. `D`, `H`, `MS`). |
| `--value-columns` | Restrict to specific numeric columns. |

`ai-forecast info` prints the package version and supported model checkpoints.

---

## Quick start — Python API

```python
from ai_forecaster import ChronosForecastModel, Forecaster
from ai_forecaster.visualization import plot_results

model = ChronosForecastModel(model_name="amazon/chronos-t5-small")
forecaster = Forecaster(model=model, num_samples=100)

results = forecaster.forecast_excel(
    path="examples/sample_data.xlsx",
    horizon=30,
)

forecaster.to_excel(results, out_path="outputs/forecast.xlsx")
plot_results(results, out_dir="outputs/plots")

for r in results:
    print(r.series_name, r.median.head())
```

A complete script is in `examples/example_usage.py`.

For the event-driven workflow:

```python
from ai_forecaster import (
    ChronosForecastModel, Forecaster,
    load_event_workbook, build_demand_index_series, filter_series,
)
from ai_forecaster.visualization import plot_results

data = load_event_workbook("examples/simulated_event_data_and_rules.xlsx")
series = build_demand_index_series(data)                    # 15 stores × 2 channels = 30 series
series = filter_series(series, stores=["S0001", "S0002"])   # optional subset

forecaster = Forecaster(model=ChronosForecastModel(), num_samples=50)
results = forecaster.forecast_many(series, horizon=30)

forecaster.to_excel(results, "outputs/event_forecast.xlsx")
plot_results(results, out_dir="outputs/event_plots")
```

The full demo is `examples/forecast_events_example.py`.

---

## Shift-scheduling optimiser (events + stores + employees → optimal roster)

Once you have:

* the **event workbook** (e.g. `examples/simulated_event_data_and_rules.xlsx`),
* a **stores workbook** (`examples/stores.xlsx`),
* an **employees workbook** (`examples/employees.xlsx`),

you can produce an optimal weekly shift schedule per store. Mock data for the
last two — plus every workbook the richer AI-deployment-chart UI needs — is
shipped.  Generate **all of it in one shot** with:

```bash
python examples/generate_full_mock_dataset.py
```

That writes 10 cross-referenced Excel workbooks in `examples/` (see the
[Mock dataset](#mock-dataset) section below). For a minimal run (just
stores + employees) you can still use the older script
`python examples/generate_store_employee_data.py`.

### Stores schema (`stores.xlsx`)

| column | meaning |
|---|---|
| `store_id` | unique id, must match `events` and `employees` |
| `store_name`, `city` | display only |
| `open_hour`, `close_hour` | informational |
| `shifts_per_day` | 2 (Morning + Afternoon) or 3 (+ Evening) |
| `base_staff_per_shift` | baseline headcount per shift on a normal day |
| `min_staff_per_shift` | hard lower bound |
| `max_staff_per_shift` | hard upper bound |

### Employees schema (`employees.xlsx`)

| column | meaning |
|---|---|
| `employee_id`, `employee_name` | unique id + display name |
| `store_id` | which store they belong to |
| `role` | `Manager`, `Cashier`, `Cook`, `Server`, `Cleaner` |
| `contract_hours_per_week` | hard weekly cap |
| `min_hours_per_week` | soft lower bound (penalised if missed) |
| `hourly_rate` | drives the wage-cost objective |
| `available_days` | comma list, e.g. `"Mon,Tue,Wed,Thu,Fri"` |
| `available_shifts` | comma list of `Morning,Afternoon,Evening` |
| `skills` | comma list of certified `station_id`s (see `stations.xlsx`) |

<a id="mock-dataset"></a>
## Mock dataset — full catalogue

`examples/generate_full_mock_dataset.py` writes every workbook the UI flow
(`examples/ai_deployment_chart_userflow.html`) expects. All IDs are
cross-referenced — the same `store_id`, `station_id`, `employee_id` mean the
same thing in every file.

| Priority | File | Rows (default) | Purpose |
|---|---|---:|---|
| P0 | `stations.xlsx` | 6 stations + channel map | Station catalogue (Grill, Fryer, Drive-Through, Front Counter, Assembly, Prep) with base staff per shift, channel weights, colours |
| P0 | `stores.xlsx` | 15 | One row per store. Adds `base_daily_orders` (used by `orders_history`) |
| P0 | `employees.xlsx` | ~175 | Roster with new `skills` column (CSV of certified `station_id`s) |
| P0 | `tasks.xlsx` | 3 | Rotational tasks: Cleaning, Restocking, Prep |
| P0 | `orders_history.xlsx` | ~10 k | 92 days × 15 stores × shifts × 3 channels with day-of-week seasonality + weather effects |
| P1 | `promos.xlsx` | 7 | BOGO / Discount / Combo / Loyalty campaigns, per-channel uplift, affected stations, store scope |
| P1 | `events_calendar.xlsx` | ~20 | External events (Sport / Concert / Festival / Holiday …) with `venue_distance_km`, `expected_crowd_size`, `time_window`, per-channel impact, confidence |
| P1 | `past_deployments.xlsx` | ~13 k | AI-recommended vs manager-assigned staffing per (date × store × shift × station) with `gap` + `outcome` (short/met/over) — powers the "reasoning" panel |
| P2 | `weather_forecast.xlsx` | ~13 k | Per-store × date × shift forecast for 2026 — `rain_probability`, `condition`, `intensity`, `temp_c`, `wind_kmh`, synced with the rain days in `simulated_event_data_and_rules.xlsx` |
| P2 | `crew_availability_overrides.xlsx` | ~1.3 k | PTO / Sick / Training / Personal / Swap overrides (~5% of (employee × day)) |

### Suggested downstream pipeline

```
stations × stores × employees                   ─► scheduler baseline roster
events_calendar + promos + weather_forecast     ─► demand_index time-series (Chronos)
past_deployments                                ─► AI reasoning / confidence
crew_availability_overrides                     ─► hard constraints on solver
```

Run the generator any time to reset; output is deterministic per seed.

### How it works

```
events.xlsx ─► event×rules join ─► daily demand_index per (store, channel)
                              │
                  (Chronos)   ▼  forecast future days if needed (MPS)
                       demand per (store, day)
                                    │
   stores.xlsx + employees.xlsx ─► OR-Tools CP-SAT ─► optimal roster
```

For each `(store, day, shift)` the required headcount is
`ceil(base_staff × demand_index)`, clamped to `[min_staff, max_staff]`.
The CP-SAT model decides which employees are scheduled, respecting:

- **Hard:** weekly contract cap, one shift / day, availability windows, max staff per shift.
- **Soft (penalised in the objective):** under-coverage, "no manager on shift", below-minimum hours.

The objective minimises **total wage cost + slack penalties**, so when full
coverage is impossible (tight roster, awkward availability) you get the *least
bad* schedule and can read off exactly which slots are still uncovered.

### CLI

```bash
ai-forecast optimize-shifts examples/simulated_event_data_and_rules.xlsx \
    --stores      examples/stores.xlsx \
    --employees   examples/employees.xlsx \
    --start-date  2026-02-02 \
    --horizon-days 7 \
    --stores-filter S0001,S0002,S0003 \
    --model       amazon/chronos-bolt-base \
    --device      mps \
    --output      outputs/shift_schedule.xlsx
```

Pass `--no-forecast` to skip the model entirely (uses the event-log demand
directly — instant, no HF download). Use `--solver-time-limit 60` to give
CP-SAT more time on large instances.

### Python API

```python
from ai_forecaster import (
    ChronosForecastModel, Forecaster, SchedulerConfig,
    optimise_shifts, write_schedule_excel,
)

model = ChronosForecastModel(model_name="amazon/chronos-bolt-base", device="mps")
forecaster = Forecaster(model=model, num_samples=50)

result = optimise_shifts(
    events_path="examples/simulated_event_data_and_rules.xlsx",
    stores_path="examples/stores.xlsx",
    employees_path="examples/employees.xlsx",
    start_date="2026-02-02",
    horizon_days=7,
    config=SchedulerConfig(solver_time_limit_s=20, shift_hours=8),
    forecaster=forecaster,
    stores_to_use=["S0001", "S0002", "S0003"],
)

write_schedule_excel(result, "outputs/shift_schedule.xlsx")
print(result.schedule.solver_status, result.schedule.objective_value)
```

The complete demo is `examples/optimize_shifts_example.py`.

### Output (`outputs/shift_schedule.xlsx`)

| Sheet | Contents |
|---|---|
| `assignments` | one row per `(store, date, shift, employee)` with hours + wage |
| `coverage` | per-slot demand_index, required vs. assigned staff, shortfall, has_manager flag |
| `employee_summary` | weekly hours, pay, and "below_min" gap per employee |
| `schedule_wide` | human-friendly pivot: rows = stores, columns = `"<date> <shift>"`, cells = employee names |
| `demand` | the per-(store, day) demand_index used by the solver |
| `_summary` | solver status, objective, total shortfall, horizon |

---

## Output

`outputs/forecast.xlsx` contains:

- One sheet per forecasted series with columns:
  - `actual` — original history (NaN in the future region)
  - `mean`, `median`
  - one column per quantile, e.g. `q10`, `q50`, `q90`
- A `_summary` sheet listing horizon, forecast window, and aggregate statistics for each series.

`outputs/plots/forecast_<series>.png` shows history + median forecast + uncertainty band.

---

## Project layout

```
.
├── pyproject.toml
├── requirements.txt
├── README.md
├── src/
│   └── ai_forecaster/
│       ├── __init__.py
│       ├── data_loader.py     # Excel → TimeSeries
│       ├── model.py           # Hugging Face model wrapper (Chronos)
│       ├── forecaster.py      # End-to-end pipeline + Excel export
│       ├── visualization.py   # Matplotlib plots
│       └── cli.py             # `ai-forecast` Typer CLI
├── src/
│   └── ai_forecaster/
│       ├── event_pipeline.py        # event log + rules → per-(store, channel) series
│       ├── scheduler.py             # OR-Tools CP-SAT shift optimiser
│       └── scheduling_pipeline.py   # events + Chronos + scheduler glue
├── examples/
│   ├── generate_sample_data.py
│   ├── generate_full_mock_dataset.py      # P0→P2 mock workbooks (stations, stores, employees, tasks, orders, promos, events, deployments, weather, overrides)
│   ├── generate_store_employee_data.py    # (legacy) minimal stores.xlsx + employees.xlsx
│   ├── api_client_walkthrough.py          # Python client — exercises all 5 screens of the user flow
│   ├── test_api_flow.sh                   # Shell/curl walkthrough — same flow, no Python required
│   ├── example_usage.py
│   ├── forecast_events_example.py
│   ├── optimize_shifts_example.py         # full M1-friendly demo
│   └── simulated_event_data_and_rules.xlsx
└── tests/
    ├── test_data_loader.py
    ├── test_event_pipeline.py
    ├── test_scheduler.py             # OR-Tools tests, no HF download
    └── test_forecaster.py            # uses a mock model, no HF download
```

---

## Choosing a model

| Checkpoint | Params | When to use |
|------------|-------:|-------------|
| `amazon/chronos-t5-tiny`  | ~8M   | Smoke tests, very fast CPU inference. |
| `amazon/chronos-t5-mini`  | ~20M  | Lightweight production use. |
| `amazon/chronos-t5-small` | ~46M  | **Default** — strong speed/quality trade-off. |
| `amazon/chronos-t5-base`  | ~200M | Better accuracy if a GPU is available. |
| `amazon/chronos-t5-large` | ~710M | Best accuracy, GPU strongly recommended. |
| `amazon/chronos-bolt-*`   | varies| Bolt variants — faster decoding. |

Pick one with the `--model` CLI flag or by passing `model_name=` to `ChronosForecastModel`.

---

## REST API — client integration

Everything above is also exposed as a FastAPI server whose shape mirrors
the screens in `examples/ai_deployment_chart_userflow.html` one-for-one.
A client developer can implement the UI by consuming these endpoints.

### Starting the server

```bash
# Local Python
ai-forecast serve --port 8000          # http://localhost:8000

# Or with docker-compose
docker compose up api                  # exposes :8000, uses mock dataset

# Auto-generated OpenAPI docs
open http://localhost:8000/docs
```

### Endpoint map (user-flow → HTTP)

| Screen | Method | Path | Purpose |
|---|---|---|---|
| 0 Store profile | `GET` | `/api/v1/stations` | Station catalogue |
| 0 Store profile | `GET` | `/api/v1/tasks` | Rotational tasks |
| 0 Store profile | `GET` | `/api/v1/stores`, `/api/v1/stores/{id}` | Stores & details |
| 1 Crew setup | `GET` | `/api/v1/stores/{id}/crew` | Roster with `skills` list |
| 1 Crew setup | `POST` | `/api/v1/stores/{id}/crew` | Add crew member |
| 1 Crew setup | `PATCH` | `/api/v1/crew/{id}` | Update crew (skills, availability) |
| 1 Crew setup | `DELETE` | `/api/v1/crew/{id}` | Remove crew member |
| 2 AI suggestion | `GET` | `/api/v1/context?store_id=&date=` | External factor badges (weather, events, promos, holiday, DoW) |
| 2 AI suggestion | `POST` | `/api/v1/forecast/staffing` | Full station×shift grid with reasoning + confidence |
| 3 Deployment chart | `POST` | `/api/v1/deployments` | Save manager's assignments |
| 3 Deployment chart | `PATCH` | `/api/v1/deployments/{id}` | Modify cells |
| 4 Summary | `GET` | `/api/v1/deployments/{id}/summary` | Totals, gap, coverage, wage cost |
| 4 Summary | `GET` | `/api/v1/deployments/{id}/comparison` | vs `past_deployments.xlsx` actuals |
| 5 Saved charts | `GET` | `/api/v1/deployments?store_id=` | List deployments |
| ops | `GET` | `/health`, `/api/v1/info` | Liveness + loaded-dataset sizes |

### Canonical "AI forecast" request

The single most important endpoint is the staffing forecast — it consumes
the mock workbooks, runs the reasoning engine, and returns the grid the
UI drops straight into Screen 2.

```bash
curl -sS -X POST http://localhost:8000/api/v1/forecast/staffing \
  -H 'content-type: application/json' \
  -d '{"store_id":"S0001","date":"2026-04-26","demo_mode":true}' | jq
```

Response shape (abbreviated):

```json
{
  "store_id": "S0001",
  "date": "2026-04-26",
  "day_of_week": "Sun",
  "model_used": "rules-only/demo",
  "generation_ms": 103,
  "context": {
    "factors": [
      {"kind":"weather","label":"🌧 Rain (94%)","source":"prediction_rule",
       "impact_delivery":0.05,"impact_dinein":-0.03, "...": "..."},
      {"kind":"promo","label":"📣 Delivery 20% Off","source":"ai_inference","...":"..."}
    ],
    "channel_multipliers": {"Delivery":1.39,"Dine-in":1.08,"Drive-Through":1.13}
  },
  "cells": [
    {"station_id":"ST_DT","station_name":"Drive-Through","shift":"Afternoon",
     "ai_recommended":3,"confidence":"medium","reason_short":"Rain → DT preference",
     "reason_rows":[
       {"icon":"📋","label":"Factors","value":"🌧 Rain (94%), 📣 Delivery 20% Off, 📅 Sun"},
       {"icon":"📐","label":"Rules","value":"Rain shifts customers from dine-in to DT..."},
       {"icon":"🔗","label":"Channel","value":"..."},
       {"icon":"👥","label":"Crew","value":"Only 2 certified + available — gap of 1..."},
       {"icon":"◆","label":"Confidence","value":"● Medium — blend of rules + inferred impact."}
     ]
    }
  ]
}
```

Every `reason_rows` array has the same 5 rows (Factors / Rules / Channel
/ Crew / Confidence), so the UI can render each expandable reason panel
from a fixed template.

### Two ways to test the AI forecast

**1. End-to-end curl walkthrough** (needs a running server + `jq`):

```bash
ai-forecast serve --port 8000 &          # leave running in one terminal
./examples/test_api_flow.sh              # hits all 5 screens, exits non-zero on any failure
```

**2. Python client walkthrough** (works with or without a live server):

```bash
# Against a running server
python examples/api_client_walkthrough.py --base http://localhost:8000

# Entirely in-process — no server, no HTTP, great for CI
python examples/api_client_walkthrough.py --in-process
```

### Integration tests

```bash
pytest tests/test_api.py -v
```

Uses FastAPI's `TestClient` so the whole flow (including the forecast
reasoning) runs in ~1 s without downloading any Chronos weights (the
`demo_mode=true` flag in the request body keeps torch out of the call
path).

### `demo_mode` vs real Chronos

- `demo_mode: true` — rule-based only: day-of-week × weather × promo × event multipliers applied to each station's base staff.  Deterministic, no torch, <200 ms.
- `demo_mode: false` — rule engine above is blended with a short-horizon
  Chronos forecast of the per-channel `demand_index` series.  Uses the
  `default_model` from `/api/v1/info` (Chronos-Bolt-Base recommended on
  Mac M1 with MPS).

### Client auth & state

- **Auth**: not in scope for the hackathon — CORS is `*`. Add a
  `Depends(security)` layer before production.
- **Deployment storage**: in-memory dict (`DeploymentStore`). Swap in
  Postgres / Redis for persistence.

---

## Tests

```bash
pip install -r requirements.txt
pytest
```

The test suite uses an in-process mock model so it does **not** download any Hugging Face weights — it runs in seconds. The API layer is tested end-to-end via FastAPI's `TestClient` (`tests/test_api.py`), and the mock-data generators are cross-reference-checked in `tests/test_mock_dataset.py`.

---

## License

MIT
