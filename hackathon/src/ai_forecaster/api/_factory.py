"""Module-level ASGI app for ``uvicorn`` string imports.

``uvicorn ai_forecaster.api._factory:app`` loads this module, reads
``AI_FORECASTER_EXAMPLES_DIR`` (if set), and builds the FastAPI app.
"""

from __future__ import annotations

import os
from pathlib import Path

from .app import create_app

examples_dir_env = os.environ.get("AI_FORECASTER_EXAMPLES_DIR")
app = create_app(examples_dir=Path(examples_dir_env) if examples_dir_env else None)
