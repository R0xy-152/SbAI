"""Gal backend application.

Run (from backend/):
    .venv/Scripts/python -m uvicorn app.main:app --port 8000

Then open http://localhost:8000/frontend/index.html in a browser.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.characters.base import CharacterRuntime
from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.poc import build_poc_events
from app.providers.base import LLMProvider
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_provider() -> LLMProvider:
    """Pick a provider: GAL_PROVIDER=mock|deepseek, defaulting to deepseek
    when a key is present and mock otherwise (so the app runs keyless)."""
    mode = os.environ.get("GAL_PROVIDER", "auto")
    if mode == "mock":
        return MockProvider()
    if mode == "deepseek":
        return DeepSeekProvider()
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekProvider()
    return MockProvider()


def create_app() -> FastAPI:
    app = FastAPI(title="Gal Backend", version="0.2.0")

    # Local dev fixture: permissive CORS so the frontend can also be opened
    # from another origin during validation. Not a production policy.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    sessions = SessionStore()
    provider = build_provider()
    # TV-09: both MVP generative characters share the configured provider
    # (docs/04 §62); each keeps its own persona and Context Builder.
    runtimes: dict[str, CharacterRuntime] = {
        "deepseek": DeepSeekRuntime(provider),
        "claude": ClaudeRuntime(provider),
    }
    # TV-11: the narrative pipeline (Interpreter → Event Evaluation → Commit)
    # is wired in for the running app. The POC events are validation fixtures
    # (docs/06 §10), not production plot. With a mock provider the interpreter
    # fails closed to noop, so the app still runs keyless.
    app.state.orchestrator = GameOrchestrator(
        sessions,
        runtimes,
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
    )
    app.include_router(chat_router)

    # Serve the static frontend from the repo root so the game can be validated
    # in a browser without a separate static server. API routes are registered
    # before this mount and therefore take precedence.
    app.mount("/", StaticFiles(directory=REPO_ROOT, html=True), name="static")

    return app


app = create_app()
