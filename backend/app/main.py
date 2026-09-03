"""Gal backend application.

Run (from backend/):
    .venv/Scripts/python -m uvicorn app.main:app --port 8000

Then open http://localhost:8000/frontend-deprecated/index.html in a browser.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.developer_note import router as developer_note_router
from app.api.game import router as game_router
from app.api.saves import router as saves_router
from app.api.story import router as story_router
from app.auth import AuthService, MemoryAuthRepository, PostgresAuthRepository, UserRecord
from app.ops.dashboard import router as ops_router
from app.ops.events import MemoryOpsRecorder, PostgresOpsRecorder
from app.ops.feedback import (
    FeedbackClassifier,
    MemoryFeedbackStore,
    PostgresFeedbackStore,
)
from app.ops.page import PAGE_HTML
from app.characters.base import CharacterRuntime
from app.characters.claude import ClaudeRuntime
from app.characters.chatgpt import ChatGPTRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.characters.doubao import DoubaoRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.consistency import SemanticConsistencyChecker
from app.game.reflection import Reflector
from app.game.state.session import SessionStore
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.inquiry import Chapter1InquiryInterpreter
from app.persistence.repository import JsonSessionRepository
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider, ProviderConfigError
from app.providers.deepseek import DeepSeekProvider, DEEPSEEK_MODEL
from app.providers.mock import MockProvider
from app.save import JsonSaveRepository, PostgresSaveRepository, SaveSnapshotService
from app.script.chapter1 import build_script_registry
from app.script.fixture import build_script_nodes
from app.script.runtime import ScriptRuntime
from app.script.service import ScriptService
from app.script.story_runtime import StoryRuntime
from app.script.prologue_runtime import PrologueRuntime
from app.game.speaker_selector import SpeakerSelector

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

    # T2review P0 修复：CORS 不再对任意 Origin 开放。开发默认放行本地 vite
    #（:5173）；额外来源经 GAL_CORS_ORIGINS（逗号分隔）显式授权。
    cors_origins = [
        origin.strip()
        for origin in os.environ.get("GAL_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ] or [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    sessions = SessionStore()
    deepseek_provider = build_provider("deepseek")
    claude_provider = build_provider("claude")
    chatgpt_provider = build_provider("chatgpt")
    doubao_provider = build_provider("doubao")
    # Semantic consistency gate (defense-in-depth): OFF by default, since each
    # check is an extra LLM call. GAL_CONSISTENCY_CHECK=on enables it with the
    # real DeepSeek provider; under the mock provider the judge fails open.
    consistency_checker: SemanticConsistencyChecker | None = None
    if os.environ.get("GAL_CONSISTENCY_CHECK", "off") == "on":
        consistency_checker = SemanticConsistencyChecker(deepseek_provider)
    # Character self-reflection (docs/04 §47.1 extension): OFF by default, since
    # each reflection is an extra LLM call per turn. GAL_REFLECTION=on enables
    # it with the real DeepSeek provider; under the mock provider it fails open.
    reflector: Reflector | None = None
    if os.environ.get("GAL_REFLECTION", "off") == "on":
        reflector = Reflector(deepseek_provider)
    # Each generative character binds its own provider through the shared
    # LLMProvider interface (docs/02 §18). MVP default is the shared DeepSeek
    # adapter; Anthropic is an explicit opt-in (see build_provider). Each keeps
    # its own persona and Context Builder (docs/04 §62).
    runtimes: dict[str, CharacterRuntime] = {
        "deepseek": DeepSeekRuntime(deepseek_provider),
        "claude": ClaudeRuntime(claude_provider),
        "chatgpt": ChatGPTRuntime(chatgpt_provider),
        "doubao": DoubaoRuntime(doubao_provider),
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
        inquiry_interpreter=Chapter1InquiryInterpreter(deepseek_provider),
        speaker_selector=SpeakerSelector(deepseek_provider),
        # docs/12 §32: POC events remain available to their isolated runtime
        # tests, but must never be eligible in a formal Chapter One session.
        events=(),
        repository=JsonSessionRepository(data_dir),
        # Presence Gate (docs/03 §13.6): Claude is only interactable after the
        # Narrative Event commits `claude_has_appeared`. DeepSeek is ungated.
        availability={
            "claude": "claude_has_appeared",
            "chatgpt": "chatgpt_has_appeared",
            "doubao": "doubao_has_appeared",
        },
        # Script layer (docs/03 §37): the deterministic authored lines — the
        # active opening (docs/01 §4) and per-event beat lines. Fixture ≠
        # Production (docs/06 §10); the wording is a placeholder.
        script=ScriptService(build_script_nodes()),
        # Script Runtime (docs/12 §32-33): the fixed Chapter One beats (03:17
        # incident, GPT/豆包 arrivals, final reveal) as Script Sequences. The
        # runtime only proposes; the Narrative Runtime above stays authoritative.
        script_runtime=ScriptRuntime(build_script_registry()),
        # 快速上线固定剧本（临时组件）：AI 停用期间 /api/story 三端点驱动
        # 07 剧本（docs/story/07，评审稿）。与旧调查玩法并行，互不依赖。
        story_runtime=StoryRuntime(),
        consistency_checker=consistency_checker,
        reflector=reflector,
        # docs/19：序章与既有第一章故事 Runtime 并行；story_id=prologue
        # 才会进入无序探班流程，旧 story_cursor 继续由 StoryRuntime 恢复。
        prologue_runtime=PrologueRuntime(),
        # Auto Save (docs/13 §21, Task 8): the orchestrator fires the
        # checkpoint side effect after narrative commits, using the player_id
        # the API layer forwards. Wired below once the save service exists.
    )
    # Save Snapshot layer (docs/13 §14-21, Task 6): PostgreSQL is the target
    # backend (docs/13 §16); GAL_SAVE_BACKEND=postgres opts in with a DSN. The
    # default JSON file repository is the TV-14-style local fixture so the app
    # runs without a database (docs/06 §10: fixture ≠ production).
    save_backend = os.environ.get("GAL_SAVE_BACKEND", "json")
    postgres_dsn = os.environ.get(
        "GAL_POSTGRES_DSN",
        "postgresql://gal:gal@localhost:5432/gal",
    )
    if save_backend == "postgres":
        save_repository = PostgresSaveRepository(postgres_dsn)
    else:
        save_repository = JsonSaveRepository(REPO_ROOT / "backend" / "data" / "saves")
    app.state.save_service = SaveSnapshotService(save_repository)

    # docs/18: production reuses PostgreSQL for accounts, login sessions,
    # ownership and quota. JSON/local mode keeps an in-memory repository so
    # unit tests and keyless development do not need another service.
    auth_backend = os.environ.get(
        "GAL_AUTH_BACKEND", "postgres" if save_backend == "postgres" else "memory"
    )
    auth_repository = (
        PostgresAuthRepository(postgres_dsn)
        if auth_backend == "postgres"
        else MemoryAuthRepository()
    )
    # docs/21 §3：运营事件/指标与反馈分析跟随 auth 后端走同一数据库；内存
    # 实现供本地开发与测试，行为与 PG 一致。
    ops_recorder = (
        PostgresOpsRecorder(postgres_dsn)
        if auth_backend == "postgres"
        else MemoryOpsRecorder()
    )
    feedback_store = (
        PostgresFeedbackStore(postgres_dsn)
        if auth_backend == "postgres"
        else MemoryFeedbackStore()
    )
    app.state.ops = ops_recorder
    app.state.feedback_store = feedback_store
    auth_secret = os.environ.get("GAL_AUTH_SECRET")
    if not auth_secret:
        if auth_backend == "postgres":
            raise RuntimeError("GAL_AUTH_SECRET is required with PostgreSQL authentication")
        auth_secret = "local-development-only-change-me"
    app.state.auth_service = AuthService(auth_repository, auth_secret)
    # docs/21 §6：反馈分类器（LLM 分类 + 人工抽检）；与角色回复共用
    # DeepSeek 适配器，无 key 环境回落 mock（分类会记为 failed，不阻塞游戏）。
    app.state.feedback_classifier = FeedbackClassifier(
        deepseek_provider,
        app.state.auth_service,
        feedback_store,
        model_name=DEEPSEEK_MODEL,
    )
    app.state.auth_disabled = os.environ.get("GAL_AUTH_REQUIRED", "true").lower() in {
        "0", "false", "no"
    }
    app.state.auth_cookie_name = "gal_auth"
    app.state.auth_cookie_secure = os.environ.get(
        "GAL_AUTH_COOKIE_SECURE", "false"
    ).lower() in {"1", "true", "yes"}
    app.state.auth_cookie_max_age = 30 * 24 * 60 * 60

    @app.middleware("http")
    async def authenticate_request(request: Request, call_next):
        path = request.url.path
        public = path in {"/api/auth/login", "/api/health"} or request.method == "OPTIONS"
        # docs/21 §5：内部运营端点豁免会话认证，仅靠 GAL_OPS_TOKEN 门禁
        #（未配置时 503、错误时 401），开发者无需先登录游戏即可用看板。
        ops_endpoint = path.startswith("/api/ops/")
        protected = not ops_endpoint and (
            path.startswith("/api/") or path.startswith("/frontend-deprecated")
        )
        if not protected or public:
            return await call_next(request)
        if app.state.auth_disabled:
            request.state.user = UserRecord(
                id="test-user",
                display_name="Test User",
                invite_code_digest="",
                status="ACTIVE",
                quota_total=1_000_000,
                quota_used=0,
                created_at=datetime.now(timezone.utc),
            )
            return await call_next(request)
        token = request.cookies.get(app.state.auth_cookie_name)
        user = app.state.auth_service.authenticate(token)
        if user is None:
            return JSONResponse(status_code=401, content={"detail": "authentication required"})
        request.state.user = user
        return await call_next(request)
    # docs/13 §21 / Task 8: bind the Auto Save side effect to the orchestrator
    # now that the save service exists (constructed after the orchestrator).
    # The orchestrator stores it as `_save_service` (constructor param name);
    # assigning the public name would create a phantom attribute it never reads.
    app.state.orchestrator._save_service = app.state.save_service
    # docs/21 §4: bind the ops recorder the same way (orchestrator stores it
    # as `_ops`, the constructor param name).
    app.state.orchestrator._ops = ops_recorder
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(developer_note_router)
    app.include_router(game_router)
    app.include_router(saves_router)
    app.include_router(story_router)
    app.include_router(ops_router)

    # Liveness probe consumed by the Vue frontend (docs/13 Task 1: Vue 可请求
    # FastAPI health endpoint). Does not touch any game runtime state.
    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "service": "gal-backend"}

    # docs/21 §5：内部运营看板页面（数据端点另有 GAL_OPS_TOKEN 门禁，
    # 页面本身不含任何数据）。
    @app.get("/ops", include_in_schema=False)
    def ops_page() -> HTMLResponse:
        return HTMLResponse(PAGE_HTML)

    # T2review P0 修复：绝不再把 REPO_ROOT 挂到根 URL（仓库内 .env、会话
    # JSON 等敏感文件不可经静态路由暴露）。只对明确的素材/前端资源目录建立
    # allow-list 挂载（docs/13 Task 9 Step 3 的三棵树）。API 路由先注册、
    # 优先级高于挂载。
    app.mount("/char", StaticFiles(directory=REPO_ROOT / "char"), name="char-assets")
    app.mount(
        "/backgroud", StaticFiles(directory=REPO_ROOT / "backgroud"), name="background-assets"
    )
    app.mount(
        "/frontend-deprecated",
        StaticFiles(directory=REPO_ROOT / "frontend-deprecated", html=True),
        name="legacy-frontend",
    )

    return app


app = create_app()
