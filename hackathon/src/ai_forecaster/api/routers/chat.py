"""Chat — AI assistant powered by Ollama with direct context injection.

``POST /api/v1/chat`` accepts a user message along with conversation
history and current deployment state, queries the local Ollama model
with xlsx-derived context, and returns a response with optional
structured actions the UI can auto-apply.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from ..chat_service import (
    build_data_context,
    build_system_prompt,
    call_ollama,
    parse_response,
)
from ..schemas import ChatRequest, ChatResponse
from ..state import AppState

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, state: AppState = Depends(_state)) -> ChatResponse:
    data_context = build_data_context(state.data, body.store_id, body.date)
    system_prompt = build_system_prompt(data_context, body.current_cells)

    try:
        raw = await call_ollama(system_prompt, body.conversation_history, body.message)
    except Exception as exc:
        logger.error("Ollama call failed: %s", exc)
        return ChatResponse(
            message=(
                "I couldn't reach the AI model right now. "
                "Make sure Ollama is running (`ollama serve`) with a model pulled "
                f"(`ollama pull {__import__('os').getenv('OLLAMA_MODEL', 'llama3.2')}`). "
                f"Error: {exc}"
            ),
            actions=[],
        )

    return parse_response(raw)
