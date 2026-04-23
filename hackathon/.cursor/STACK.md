# Stack & Tooling

Pinned versions and runtime expectations for both stacks. Keep this in sync with `requirements.txt`, `pyproject.toml`, `Dockerfile`, and `package.json`.

## Python (ai-forecaster + future AI service)

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ (Docker uses 3.11) | `requires-python = ">=3.9"` in pyproject for compat, but assume 3.10+ syntax. |
| torch | ≥ 2.1 | CPU wheel by default in Docker; pass `--build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121` for CUDA. |
| transformers | ≥ 4.40 | |
| accelerate | ≥ 0.30 | |
| chronos-forecasting | ≥ 1.5 | Required for the unified `BaseChronosPipeline.predict_quantiles` API. |
| pandas | ≥ 2.1 | |
| numpy | ≥ 1.26 | |
| openpyxl | ≥ 3.1 | `.xlsx` engine. |
| xlrd | ≥ 2.0 | legacy `.xls`. |
| matplotlib | ≥ 3.8 | Use `MPLBACKEND=Agg` in headless / Docker contexts. |
| typer | ≥ 0.12 | CLI. |
| rich | ≥ 13.7 | CLI output. |
| pytest | ≥ 8.0 | Tests. |

**Default model:** `amazon/chronos-t5-small`. Override with `--model` flag or `ChronosForecastModel(model_name=...)`.

**HF cache:** mounted as a named Docker volume (`ai-forecaster-hf-cache`) at `/root/.cache/huggingface`. Do not bake weights into images.

## Node.js (deployment chart API)

| Tool | Version | Notes |
|---|---|---|
| Node.js | ≥ 20 | LTS. |
| Module system | ESM | `"type": "module"` (add when expanding `package.json`). |
| HTTP framework | TBD | Pick Express or Fastify when scaffolding the API; keep one — don't mix. |
| ORM / driver | `better-sqlite3` (sync, simple) recommended for hackathon. | |

`index.js` and `package.json` are placeholders today. Expand them — don't create a parallel `server/` tree without discussion.

## Persistence

- **SQLite**, single file. No Postgres / no cloud DB for the hackathon.
- Schema lives at project root in `schema.md` (per PRD §7).
- New tables (crew members, deployment charts, AI suggestion audit) must coexist with the existing `t_store`, `t_store_station`, `t_store_task` schema.

## LLM

- **Ollama**, local only. Default model class: 7B (Llama 3 / Mistral). Make the model id configurable via env var (e.g. `OLLAMA_MODEL`).
- Minimum host RAM for a 7B model: ~8 GB.
- AI suggestion latency target: < 30s end-to-end (PRD §5.3).

## Containerization

- Dockerfile: multi-stage minimal (single stage today, fine for hackathon). CPU-only torch by default.
- `docker-compose.yml` mounts the project at `/work` and persists the HF cache.
- Don't add the Node service to the existing image — give it its own `Dockerfile`/compose service when introduced.
