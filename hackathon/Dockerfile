# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# ai-forecaster — runtime image.
#
# Build:
#   docker build -t ai-forecaster .
#
# Run (CPU, mount current dir for I/O, persist HF cache):
#   docker run --rm -it \
#       -v "$PWD:/work" \
#       -v ai-forecaster-hf-cache:/root/.cache/huggingface \
#       ai-forecaster forecast /work/examples/sample_data.xlsx \
#                              --horizon 30 \
#                              --output /work/outputs/forecast.xlsx
# ---------------------------------------------------------------------------

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers \
    MPLBACKEND=Agg

# System libs needed by torch / pandas / openpyxl / matplotlib.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        libgomp1 \
        libstdc++6 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- dependency layer (cached) -------------------------------------------
COPY requirements.txt ./
# Install CPU-only torch from the official wheel index to keep the image small.
# Override at build time with `--build-arg TORCH_INDEX_URL=` for GPU builds.
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --upgrade pip && \
    pip install --extra-index-url "${TORCH_INDEX_URL}" -r requirements.txt

# ---- project ---------------------------------------------------------------
COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples
COPY tests ./tests

RUN pip install --no-deps -e .

# Default working directory for user files when running interactively.
WORKDIR /work

# FastAPI server port (the docker-compose `api` service listens here).
EXPOSE 8000

# Railway (and similar PaaS) inject a PORT env var.
# Default to 8000 for local Docker usage.
CMD ["sh", "-c", "ai-forecast serve --host 0.0.0.0 --port ${PORT:-8000}"]
