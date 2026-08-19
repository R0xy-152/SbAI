"""T2review P1-1（Claim disclosure gate）与 P2-1（公开台词 heard_by）。"""

from __future__ import annotations

from app.characters.base import CharacterResponse
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore


class _Echo:
    def __init__(self, character_id: str) -> None:
        self.character_id = character_id

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue=f"{self.character_id} 回应。")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="请继续。")


class _ClaudeClaims05(_Echo):
    def respond(self, request):
        return CharacterResponse(
            character_id="claude",
            dialogue="是，我访问过 Recovery Interface。",
            claim_refs=["CL_CLAUDE_05"],
        )


def _orchestrator() -> GameOrchestrator:
    return GameOrchestrator(
        SessionStore(),
        {
            "deepseek": _Echo("deepseek"),
            "claude": _ClaudeClaims05("claude"),
            "chatgpt": _Echo("chatgpt"),
            "doubao": _Echo("doubao"),
        },
        default_character="deepseek",
    )


def test_claude_05_claim_blocked_until_disclosure_open():
    """不可信 LLM 不能提前提交 CL_CLAUDE_05 / 解锁 EV07（disclosure gate）。"""
    orchestrator = _orchestrator()
    session_id = orchestrator.handle_turn(None, "你好", character_id="claude").session_id
    state = orchestrator._state.state_for(session_id)
    assert "CL_CLAUDE_05" not in state.chapter1.claim_store
    assert "EV07_CLAUDE_RECOVERY_ACCESS" not in state.chapter1.acquired_evidence

    # 披露开启后同一证词才成立
    state.narrative_flags.add("claude_recovery_disclosure_open")
    orchestrator.handle_turn(session_id, "你访问过 Recovery Interface 吗？", character_id="claude")
    state = orchestrator._state.state_for(session_id)
    assert "CL_CLAUDE_05" in state.chapter1.claim_store
    assert "EV07_CLAUDE_RECOVERY_ACCESS" in state.chapter1.acquired_evidence


def test_character_replies_carry_heard_by():
    """P2-1：公开台词记录听众，同场其他角色能听到公开回复。"""
    orchestrator = _orchestrator()
    session_id = orchestrator.handle_turn(None, "你好").session_id
    messages = orchestrator.get_history(session_id)
    player_message = messages[0]
    character_message = messages[1]
    assert player_message["role"] == "player"
    assert player_message["heard_by"] == ["deepseek"]
    assert character_message["role"] == "character"
    assert character_message["heard_by"] == ["deepseek"]
    assert character_message["character_id"] in character_message["heard_by"]

def test_parallel_turns_are_serialized_per_session():
    """P1-3：同一 session 的并发回合必须串行——历史严格 player/character 交替。"""
    import threading

    orchestrator = _orchestrator()
    session_id = orchestrator.handle_turn(None, "开场").session_id
    errors: list[Exception] = []

    def worker(index: int) -> None:
        try:
            for _ in range(5):
                orchestrator.handle_turn(session_id, f"并发消息{index}")
        except Exception as exc:  # pragma: no cover - 失败即测试失败
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors

    messages = orchestrator.get_history(session_id)
    roles = [m["role"] for m in messages]
    assert len(roles) == 22  # 开场 2 条 + 2 线程 × 5 回合 × 2 条
    for index, role in enumerate(roles):
        assert role == ("player" if index % 2 == 0 else "character"), (
            f"history interleaved at {index}: {roles[index:index+4]}"
        )

