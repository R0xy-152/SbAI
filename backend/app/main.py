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
from app.api.game import router as game_router
from app.characters.base import CharacterRuntime
from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.poc import build_poc_events
from app.persistence.repository import JsonSessionRepository
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider, ProviderConfigError
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider
from app.script.fixture import build_script_nodes
from app.script.service import ScriptService

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_provider(character_id: str) -> LLMProvider:
    """Pick one character's provider (docs/02 §18: Character Runtime and model
    provider are decoupled).

    GAL_PROVIDER=mock forces the deterministic mock for every character.
    Otherwise every generative character defaults to the shared DeepSeek
    adapter (MVP: DeepSeek and Claude both speak through DeepSeek). A character
    can be explicitly switched to Anthropic via <CHARACTER>_PROVIDER=anthropic
    (e.g. CLAUDE_PROVIDER=anthropic); that explicit opt-in fails loudly when
    ANTHROPIC_API_KEY is missing, so a misconfiguration never silently falls
    back to the wrong provider. With no DEEPSEEK_API_KEY the shared adapter
    degrades to a mock, so the app still runs keyless (docs/06 §5)."""
    if os.environ.get("GAL_PROVIDER", "auto") == "mock":
        return MockProvider(character_id=character_id)

    provider = os.environ.get(f"{character_id.upper()}_PROVIDER", "deepseek")
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderConfigError(
                f"{character_id.upper()}_PROVIDER=anthropic but "
                "ANTHROPIC_API_KEY is not set"
            )
        return AnthropicProvider()

    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekProvider()
    return MockProvider(character_id=character_id)


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
    deepseek_provider = build_provider("deepseek")
    claude_provider = build_provider("claude")
    # Each generative character binds its own provider through the shared
    # LLMProvider interface (docs/02 §18). MVP default is the shared DeepSeek
    # adapter; Anthropic is an explicit opt-in (see build_provider). Each keeps
    # its own persona and Context Builder (docs/04 §62).
    runtimes: dict[str, CharacterRuntime] = {
        "deepseek": DeepSeekRuntime(deepseek_provider),
        "claude": ClaudeRuntime(claude_provider),
    }
    # TV-11: the narrative pipeline (Interpreter → Event Evaluation → Commit)
    # is wired in for the running app. The POC events are validation fixtures
    # (docs/06 §10), not production plot. The interpreter keeps the DeepSeek
    # adapter; with a mock provider it fails closed to noop, so the app still
    # runs keyless.
    # TV-14: the JSON repository is the Session Restore fixture (docs/02 §22
    # Repository pattern; PostgreSQL is the target backend). Runtime session
    # data lives under backend/data/, which is gitignored.
    data_dir = REPO_ROOT / "backend" / "data" / "sessions"
    app.state.orchestrator = GameOrchestrator(
        sessions,
        runtimes,
        interpreter=NarrativeInterpreter(deepseek_provider),
        events=build_poc_events(),
        repository=JsonSessionRepository(data_dir),
        # Presence Gate (docs/03 §13.6): Claude is only interactable after the
        # Narrative Event commits `claude_has_appeared`. DeepSeek is ungated.
        availability={"claude": "claude_has_appeared"},
        # Script layer (docs/03 §37): the deterministic authored lines — the
        # active opening (docs/01 §4) and per-event beat lines. Fixture ≠
        # Production (docs/06 §10); the wording is a placeholder.
        script=ScriptService(build_script_nodes()),
    )
    app.include_router(chat_router)
    app.include_router(game_router)

    # Serve the static frontend from the repo root so the game can be validated
    # in a browser without a separate static server. API routes are registered
    # before this mount and therefore take precedence.
    app.mount("/", StaticFiles(directory=REPO_ROOT, html=True), name="static")

    return app


app = create_app()
