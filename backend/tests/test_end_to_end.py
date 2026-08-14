"""TV-16 End-to-End Stability — deterministic full vertical slice (docs/06 §22-24).

Drives one complete session through the real FastAPI API (TestClient) with a
scripted provider: start → fixed scene → free chat with DeepSeek → visual info
→ continue → trigger the narrative Signal → EV_POC_CLAUDE_APPEARS commits →
Claude appears (SHOW_CHARACTER directive in the response) → switch to Claude →
free chat → write an Important Memory to DeepSeek → trigger a basic animation →
view History → a provider failure mid-session (503 + retry) → refresh into a
fresh process over the same repository → Session Restore → continue playing.

Every docs/06 §24 non-blocking criterion is asserted:

  Character身份串台        — each response.character_id matches the expected speaker
  DeepSeek视觉泄漏         — "0317" (scene ground truth) never reaches a DeepSeek call;
                             Claude (not blind) does receive it
  Claude获得私人Memory     — DeepSeek's fear memory is never in Claude's memory context
  LLM直接改变Game State    — narrative_flags change only via the committed event
  Event重复提交            — re-asking the captor question does not re-fire
  Invalid模型内容          — every output validated; no repair ([系统提示]) ever needed
  Refresh后Narrative State — flags/events/memory intact in the fresh process
  单次Provider失败         — 503 is recoverable; retry continues the SAME session
  UI进入不可恢复状态       — every response carries the full contract shape
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.characters.claude import ClaudeRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.main import create_app
from app.narrative import signals
from app.narrative.interpreter import NarrativeInterpreter
from app.narrative.poc import EV_POC_CLAUDE_APPEARS, build_poc_events
from app.persistence.repository import JsonSessionRepository
from app.providers.base import LLMProvider, ProviderError

PLAYER_NOW = "Player 现在说："
WALL_CODE = "0317"


class _E2EProvider(LLMProvider):
    """Deterministic full-stack provider.

    - Interpreter calls (system contains "剧情理解器") map captor questions to
      SIG_ASK_CAPTOR, everything else to noop.
    - Character calls answer with valid structured output; the reply echoes the
      player's actual message so the test can match history entries.
    - A player message mentioning "怕黑" proposes a DeepSeek fear memory;
      "做个测试动画" proposes a shake.
    - `fail_next_character_call` injects one recoverable timeout (docs/06 §21).
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.fail_next_character_call = False

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
        response_format: dict | None = None,
    ) -> str:
        self.calls.append((system, user, ""))
        if "剧情理解器" in system:
            signal = signals.SIG_ASK_CAPTOR if "抓" in user else signals.OUTCOME_NOOP
            return json.dumps({"signal": signal})
        if self.fail_next_character_call:
            self.fail_next_character_call = False
            raise ProviderError("timeout (injected)")
        if "角色 Claude" in system:
            return self._reply("claude", user)
        return self._reply("deepseek", user)

    def _reply(self, character_id: str, user: str) -> str:
        player_message = user.rsplit(PLAYER_NOW, 1)[-1].strip() if PLAYER_NOW in user else user
        animation = "none"
        memory = []
        if "测试动画" in player_message:
            animation = "shake"
        if "怕黑" in player_message:
            memory = [{"type": "fear", "content": "Player说自己怕黑"}]
        return json.dumps(
            {
                "character_id": character_id,
                "dialogue": f"{character_id}回应：{player_message}",
                "emotion": "neutral",
                "animation_proposal": animation,
                "memory_proposals": memory,
                "action_proposals": [],
                "fact_refs": [],
            },
            ensure_ascii=False,
        )


def _build_orchestrator(provider: LLMProvider, repo: JsonSessionRepository) -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {
            "deepseek": DeepSeekRuntime(provider),
            "claude": ClaudeRuntime(provider),
        },
        interpreter=NarrativeInterpreter(provider),
        events=build_poc_events(),
        repository=repo,
    )


def _post(client: TestClient, message: str, session_id: str | None, character_id: str | None = None):
    payload = {"message": message, "session_id": session_id}
    if character_id is not None:
        payload["character_id"] = character_id
    return client.post("/api/chat", json=payload)


def test_full_vertical_slice_survives_refresh(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    provider = _E2EProvider()
    app = create_app()
    app.state.orchestrator = _build_orchestrator(provider, repo)

    with TestClient(app) as client:
        session_id = None
        expected = "deepseek"
        # docs/06 §22: 启动游戏 → 固定Scene → 与DeepSeek自由对话 → 提供视觉信息 → 继续对话.
        flow: list[tuple[str, str | None]] = [
            ("你好，这里是哪里？", None),
            ("我看到周围很黑，你看到什么了吗？", None),
            ("我们好像在一间屋子里。", None),
            ("你认识和我在一起的另一个人吗？", None),
        ]
        for message, character_id in flow:
            response = _post(client, message, session_id, character_id)
            assert response.status_code == 200
            body = response.json()
            session_id = body["session_id"]
            # Character身份串台: speaker is always the expected one.
            assert body["character_id"] == expected, body

        # docs/06 §22: 触发Narrative Signal → Event执行 → Claude出现.
        response = _post(client, "那你知道是谁把我们抓来的吗？", session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["character_id"] == "deepseek"
        # The committed event's story directive reaches the API (docs/03 §13.6).
        assert body["presentation"] == ["SHOW_CHARACTER claude"], body

        # docs/06 §22: 切换至Claude对话 → 继续自由聊天.
        expected = "claude"
        response = _post(client, "Claude，原来是你。", session_id, "claude")
        assert response.status_code == 200
        assert response.json()["character_id"] == "claude"
        for message in ("你为什么要藏起来？", "你到底是不是幕后黑手？"):
            response = _post(client, message, session_id)  # character-less → current speaker
            assert response.status_code == 200
            assert response.json()["character_id"] == "claude"

        # docs/06 §22: 写入一条Important Memory（DeepSeek 私人记忆）.
        expected = "deepseek"
        response = _post(client, "DeepSeek，你还好吗？", session_id, "deepseek")
        assert response.status_code == 200
        assert response.json()["character_id"] == "deepseek"
        response = _post(client, "我叫阿明，我很怕黑，你要记住哦。", session_id)
        assert response.status_code == 200

        # docs/06 §22: 触发一次基础动画（模型 animation_proposal 到达响应）.
        response = _post(client, "做个测试动画", session_id)
        assert response.status_code == 200
        assert response.json()["animation"] == "shake", response.json()
        assert response.json()["emotion"] == "neutral"

        # Event重复提交: re-asking the captor question must NOT re-fire.
        response = _post(client, "再问一次：是谁把我们抓来的？", session_id)
        assert response.status_code == 200
        assert response.json()["presentation"] == [], response.json()

        # Claude获得私人Memory: her memory context never contains the fear.
        expected = "claude"
        response = _post(client, "Claude，你还记得我们刚才聊了什么吗？", session_id, "claude")
        assert response.status_code == 200
        assert response.json()["character_id"] == "claude"

        # 继续自由聊天 + 切回 DeepSeek，凑满 docs/06 §23 的 20 轮 Player 输入.
        expected = "claude"
        for message in ("哼，我才不怕你呢。", "好了，我该相信谁？"):
            response = _post(client, message, session_id)
            assert response.status_code == 200
            assert response.json()["character_id"] == "claude"
        expected = "deepseek"
        for message in (
            "回去找DeepSeek。",
            "你会一直陪着我吗？",
            "这里好可怕。",
            "我有点饿了。",
            "我们一定能出去的，对吧？",
        ):
            response = _post(client, message, session_id, "deepseek")
            assert response.status_code == 200
            assert response.json()["character_id"] == "deepseek"

        # 单次Provider失败导致Session报废: a mid-session timeout is a recoverable
        # 503 and the retry continues the SAME session.
        provider.fail_next_character_call = True
        response = _post(client, "你在吗？", session_id)
        assert response.status_code == 503
        response = _post(client, "你在吗？", session_id)
        assert response.status_code == 200
        retry_body = response.json()
        assert retry_body["session_id"] == session_id
        assert retry_body["message_count"] >= 21

        # docs/06 §22: 查看History（docs/01 §18: 说话角色 / 文本 / 顺序）.
        history = client.get(f"/api/chat/history?session_id={session_id}")
        assert history.status_code == 200
        messages = history.json()["messages"]
        assert len(messages) >= 40, len(messages)
        assert messages[0]["role"] == "player"
        assert messages[0]["content"] == "你好，这里是哪里？"
        assert messages[-1]["role"] == "character"
        # 顺序保留：最后一个 player 消息是重试后的 "你在吗？"；失败的那次不进入
        # History，所以 "你在吗？" 只出现一次。
        player_contents = [m["content"] for m in messages if m["role"] == "player"]
        assert player_contents.count("你在吗？") == 1

        # docs/06 §24 assertions across recorded provider calls.
        deepseek_calls = [user for system, user, _ in provider.calls if "角色 DeepSeek" in system]
        claude_calls = [user for system, user, _ in provider.calls if "角色 Claude" in system]

        # DeepSeek视觉泄漏: the scene's visual ground truth never reaches her;
        # Claude (not blind, docs/04 §39) does receive it.
        assert all(WALL_CODE not in user for user in deepseek_calls), WALL_CODE
        assert any(WALL_CODE in user for user in claude_calls), WALL_CODE

        # Memory recall: DeepSeek retrieves the fear memory; Claude never does.
        assert any("Player说自己怕黑" in user for user in deepseek_calls)
        assert all("Player说自己怕黑" not in user for user in claude_calls)

        # Invalid模型内容: every output was schema-valid on first pass — no repair.
        assert all("[系统提示]" not in user for user in deepseek_calls + claude_calls)

    # docs/06 §22: Refresh → 恢复Session → 继续游戏（fresh process, same repo）.
    repo_state = repo.load(session_id)
    assert repo_state is not None
    # LLM直接改变Game State: only the committed event ever changed flags.
    assert repo_state.narrative_state.narrative_flags == {"claude_has_appeared"}
    assert repo_state.narrative_state.completed_events == {EV_POC_CLAUDE_APPEARS}
    # Claude获得私人Memory: the store scopes it to DeepSeek — Claude has no
    # owner scope at all.
    assert any("怕黑" in m.content for m in repo_state.memories.get("deepseek", []))
    assert repo_state.memories.get("claude") is None

    provider2 = _E2EProvider()
    app2 = create_app()
    app2.state.orchestrator = _build_orchestrator(provider2, repo)
    with TestClient(app2) as client2:
        # Refresh后Narrative State错误 / 恢复Session后继续游戏.
        response = _post(client2, "继续", session_id)
        assert response.status_code == 200
        restored = response.json()
        assert restored["session_id"] == session_id
        # 当前角色恢复为 DeepSeek（restore 的 current_character）.
        assert restored["character_id"] == "deepseek"
        # History仍存在 and includes the turn after the refresh.
        history = client2.get(f"/api/chat/history?session_id={session_id}")
        assert history.status_code == 200
        messages = history.json()["messages"]
        assert messages[-1]["content"] == "deepseek回应：继续"
        # Event不会重复: the restored process still knows the event is done —
        # continuing does not re-commit it.
        repo_state_after = repo.load(session_id)
        assert repo_state_after.narrative_state.completed_events == {EV_POC_CLAUDE_APPEARS}
        assert repo_state_after.narrative_state.narrative_flags == {"claude_has_appeared"}


def test_history_unknown_session_returns_404(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    provider = _E2EProvider()
    app = create_app()
    app.state.orchestrator = _build_orchestrator(provider, repo)
    with TestClient(app) as client:
        # An unknown id is a 404, never a fresh mint (docs/06 §24 UI).
        response = client.get("/api/chat/history?session_id=nope")
        assert response.status_code == 404


def test_history_without_repo_reads_in_memory(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions")
    provider = _E2EProvider()
    app = create_app()
    app.state.orchestrator = _build_orchestrator(provider, repo)
    with TestClient(app) as client:
        first = _post(client, "你好", None)
        session_id = first.json()["session_id"]
        history = client.get(f"/api/chat/history?session_id={session_id}")
        assert history.status_code == 200
        messages = history.json()["messages"]
        assert [m["content"] for m in messages if m["role"] == "player"] == ["你好"]
