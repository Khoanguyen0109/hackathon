"""Wrapper around Hugging Face foundation models for time-series forecasting.

Default backend: **Chronos** (https://huggingface.co/amazon/chronos-t5-small).
Chronos is a family of pretrained models that perform *zero-shot* probabilistic
forecasting on arbitrary univariate series — no training data required, which
makes it a great fit for "drop in an Excel and get a forecast" workflows.

The wrapper uses the unified ``BaseChronosPipeline.predict_quantiles`` API
introduced in ``chronos-forecasting>=1.5`` so it works with both the original
T5-based checkpoints and the newer Chronos-Bolt variants.

Supported model checkpoints (any HF id can be used):

* ``amazon/chronos-t5-tiny``    (~8M params, fastest)
* ``amazon/chronos-t5-mini``    (~20M)
* ``amazon/chronos-t5-small``   (~46M, default — good speed/quality balance)
* ``amazon/chronos-t5-base``    (~200M)
* ``amazon/chronos-t5-large``   (~710M, best quality)
* ``amazon/chronos-bolt-tiny`` / ``-mini`` / ``-small`` / ``-base`` (faster decoding)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import torch


DEFAULT_MODEL = "amazon/chronos-t5-small"
DEFAULT_QUANTILES = (0.1, 0.5, 0.9)


@dataclass
class ModelPrediction:
    """Probabilistic forecast for a single series."""

    quantiles: dict[float, np.ndarray]   # quantile -> shape (horizon,)
    mean: np.ndarray                     # shape: (horizon,)
    median: np.ndarray                   # shape: (horizon,)
    samples: np.ndarray | None = None    # only populated for sample-based backends


class ChronosForecastModel:
    """Lazy-loaded wrapper around the Chronos pipeline."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        torch_dtype: torch.dtype | str = "auto",
    ) -> None:
        self.model_name = model_name
        self.device = device or self._auto_device()
        self.torch_dtype = torch_dtype
        self._pipeline = None  # lazy

    @staticmethod
    def _auto_device() -> str:
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #
    def load(self) -> None:
        """Eagerly download and instantiate the underlying HF pipeline."""
        if self._pipeline is not None:
            return

        try:
            from chronos import BaseChronosPipeline
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "The `chronos-forecasting` package is required.\n"
                "Install it with `pip install 'chronos-forecasting>=1.5'`."
            ) from e

        dtype = self._resolve_dtype()
        self._pipeline = BaseChronosPipeline.from_pretrained(
            self.model_name,
            device_map=self.device,
            torch_dtype=dtype,
        )

    @property
    def pipeline(self):
        if self._pipeline is None:
            self.load()
        return self._pipeline

    def _resolve_dtype(self) -> torch.dtype:
        if isinstance(self.torch_dtype, torch.dtype):
            return self.torch_dtype
        if self.torch_dtype == "auto":
            if self.device == "cuda":
                return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            return torch.float32
        return getattr(torch, str(self.torch_dtype))

    # ------------------------------------------------------------------ #
    # Inference
    # ------------------------------------------------------------------ #
    def predict(
        self,
        history: np.ndarray | Sequence[float],
        horizon: int,
        num_samples: int = 100,
        quantile_levels: Sequence[float] = DEFAULT_QUANTILES,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 1.0,
    ) -> ModelPrediction:
        """Generate a probabilistic forecast for a single univariate series."""
        results = self.predict_batch(
            histories=[np.asarray(history, dtype=np.float32)],
            horizon=horizon,
            num_samples=num_samples,
            quantile_levels=quantile_levels,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )
        return results[0]

    def predict_batch(
        self,
        histories: Sequence[np.ndarray],
        horizon: int,
        num_samples: int = 100,
        quantile_levels: Sequence[float] = DEFAULT_QUANTILES,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 1.0,
    ) -> list[ModelPrediction]:
        """Forecast many independent series with one model call."""
        if horizon <= 0:
            raise ValueError("`horizon` must be > 0.")
        if not histories:
            return []

        contexts = [torch.tensor(np.asarray(h, dtype=np.float32)) for h in histories]
        for c in contexts:
            if c.ndim != 1:
                raise ValueError("Each history must be 1-D for univariate forecasting.")

        # Median (q=0.5) is required so we can return a "median" forecast.
        levels = sorted({float(q) for q in quantile_levels} | {0.5})

        extra_kwargs = self._supported_sampling_kwargs(
            num_samples=num_samples,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

        # ``predict_quantiles`` works uniformly for T5 (sample-based) and Bolt
        # (direct-quantile) backends. Returns:
        #   quantiles: (batch, horizon, num_quantiles)
        #   mean:      (batch, horizon)
        quantiles, mean = self.pipeline.predict_quantiles(
            inputs=contexts,
            prediction_length=horizon,
            quantile_levels=levels,
            **extra_kwargs,
        )

        quantiles_np = quantiles.detach().cpu().to(torch.float32).numpy()
        mean_np = mean.detach().cpu().to(torch.float32).numpy()

        results: list[ModelPrediction] = []
        for i in range(quantiles_np.shape[0]):
            q_for_series = {
                float(q): quantiles_np[i, :, j].astype(np.float32)
                for j, q in enumerate(levels)
            }
            results.append(
                ModelPrediction(
                    quantiles={
                        float(q): q_for_series[float(q)]
                        for q in quantile_levels
                    },
                    mean=mean_np[i].astype(np.float32),
                    median=q_for_series[0.5],
                    samples=None,
                )
            )
        return results

    def _supported_sampling_kwargs(
        self,
        *,
        num_samples: int,
        temperature: float,
        top_k: int,
        top_p: float,
    ) -> dict:
        """Forward sampling controls only when the backend accepts them.

        Chronos-Bolt is a direct-quantile model and its ``predict`` signature
        does not take ``num_samples`` / ``temperature`` / ``top_k`` / ``top_p``.
        The original T5 ``ChronosPipeline`` does. We introspect the underlying
        ``predict`` signature and only forward kwargs the backend understands,
        so the same wrapper code works for every Chronos checkpoint.
        """
        import inspect

        try:
            params = inspect.signature(self.pipeline.predict).parameters
        except (TypeError, ValueError):
            return {}

        candidates = {
            "num_samples": int(num_samples),
            "temperature": float(temperature),
            "top_k": int(top_k),
            "top_p": float(top_p),
        }
        return {k: v for k, v in candidates.items() if k in params}
