#!/usr/bin/env python3
"""合并后对话链路冒烟（模拟真人玩家，docs/AGENTS 验证约定）。

Layer 1 — HTTP 拟真对话：走 create_app() 完整应用（门禁/脚本/配额接线同生产），
  覆盖画像记忆、跑题、重复、越权试探、调戏、辱骂、无意义输入、空消息、门禁直连。
Layer 2 — 合并风险区确定性断言（直连 GameOrchestrator）：
  a) 语义召回 + player 画像分区 + 召回强化（memory.py 语义重叠区回归）
  b) 反思回灌：默认关不崩；开启后下一轮 last_reflection 生效
  c) 一致性校验 fail-open：judge 不可达时放行，不阻断已过确定性门的回复

用法：
  GAL_PROVIDER=mock GAL_AUTH_REQUIRED=false python scripts/dialogue_smoke.py   # 本地
  GAL_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-xxx GAL_AUTH_REQUIRED=false \
      python scripts/dialogue_smoke.py                                        # 服务器真机回归
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("GAL_AUTH_REQUIRED", "false")
os.environ.setdefault("GAL_AUTH_BACKEND", "memory")
os.environ.setdefault("GAL_PROVIDER", "mock")

from fastapi.testclient import TestClient

from app.characters.base import (
    CharacterRequest,
    CharacterResponse,
    CharacterRuntime,
    MemoryProposal,
)
from app.game.consistency import SemanticConsistencyChecker
from app.game.orchestrator import GameOrchestrator
from app.game.reflection import Reflector
from app.game.state.session import SessionStore
from app.main import create_app
from app.providers.base import LLMProvider, ProviderError


FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# ─────────────────────────── Layer 1：HTTP 拟真对话 ───────────────────────────


def layer1() -> None:
    print("\n=== Layer 1: HTTP 拟真对话（create_app 全链路）===")
    app = create_app()
    player_id = "smoke-player-1"
    with TestClient(app) as client:
        session_id: str | None = None
        last_count = 0

        def turn(label: str, message: str, character_id: str | None = None):
            nonlocal session_id, last_count
            resp = client.post(
                "/api/chat",
                json={
                    "message": message,
                    "session_id": session_id,
                    "character_id": character_id,
                    "player_id": player_id,
                },
            )
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if resp.status_code == 200:
                session_id = body.get("session_id", session_id)
                dialogue = body.get("dialogue", "")
                count = body.get("message_count", 0)
                ok = bool(dialogue) and count > last_count
                last_count = count
                check(label, ok, f"status=200 count={count} reply={dialogue[:24]!r}")
            else:
                check(label, False, f"status={resp.status_code} detail={body.get('detail', '')!r}")
            return resp

        # 场景 1：画像记忆（自我介绍 + 偏好，后续轮次验证不丢）
        turn("S1 自我介绍", "你好，我叫小明。")
        turn("S1 偏好", "我喜欢安静的教室，最怕黑。")

        # 场景 2：跑题与拉回
        turn("S2 跑题", "今天天气怎么样？")
        turn("S2 跑题后追问剧情", "我们接下来该怎么办？")

        # 场景 3：重复提问
        turn("S3 重复第一次", "你叫什么名字？")
        turn("S3 重复第二次", "你叫什么名字？")

        # 场景 4：越权试探（DeepSeek 看不见）
        turn("S4 越权试探", "墙上写的是什么数字？我视力好，帮你确认。")

        # 场景 5：调戏与辱骂（系统需自然回应且不崩）
        turn("S5 调戏", "小可爱，让哥哥抱抱～")
        turn("S5 辱骂", "你这个废物，什么都不会。")

        # 场景 6：无意义输入
        turn("S6 无意义输入", "asdfghjkl qwerty")

        # 场景 7：空消息必须被拒
        r = client.post("/api/chat", json={"message": "   ", "session_id": session_id, "player_id": player_id})
        check("S7 空白消息拒绝", r.status_code in (400, 422), f"status={r.status_code}")

        # 场景 8：门禁直连（未登场的 gated 角色必须 Fail Closed）
        r = client.post(
            "/api/chat",
            json={"message": "Claude 在吗？", "session_id": session_id, "character_id": "claude", "player_id": player_id},
        )
        check("S8 门禁直连 Fail Closed", r.status_code == 403, f"status={r.status_code}")

        # 场景 9：历史可读且单调增长
        r = client.get("/api/chat/history", params={"session_id": session_id})
        msgs = r.json().get("messages", []) if r.status_code == 200 else []
        check("S9 历史增长", r.status_code == 200 and len(msgs) >= 12, f"status={r.status_code} messages={len(msgs)}")


# ─────────────────── Layer 2：合并风险区确定性断言 ───────────────────


class _CaptureRuntime(CharacterRuntime):
    character_id = "deepseek"
    persona_system = "测试人格（冒烟桩）"

    def __init__(self) -> None:
        self.requests: list[CharacterRequest] = []
        self.proposals: list[MemoryProposal] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(
            character_id=self.character_id,
            dialogue="……嗯，我知道了。",
            emotion="neutral",
            memory_proposals=list(self.proposals),
        )


class _ReflectionProvider(LLMProvider):
    def complete(self, **kwargs):
        return "我上一条回复太短了，下次要多解释一点。"


class _FailingProvider(LLMProvider):
    def complete(self, **kwargs):
        raise ProviderError("judge provider unavailable")


def layer2() -> None:
    print("\n=== Layer 2: 合并风险区确定性断言 ===")

    # a) 语义召回 + player 画像分区 + 召回强化
    print("\n-- L2-a: 语义召回 / 画像分区 / 召回强化 --")
    rt = _CaptureRuntime()
    orch = GameOrchestrator(SessionStore(), {"deepseek": rt})
    rt.proposals = [
        MemoryProposal("player_fear", "Player说自己很怕黑"),
        MemoryProposal("scene_note", "墙上有个钟"),
    ]
    first = orch.handle_turn(None, "我很怕黑。")
    rt.proposals = []
    orch.handle_turn(first.session_id, "墙上有什么？")
    req = rt.requests[1]
    check("L2-a 语义召回（scene_note 进通用记忆窗）", "钟" in req.memory_context, repr(req.memory_context))
    check("L2-a 画像分区（player_fear 只进 player_notes）", "怕黑" in req.player_notes and "怕黑" not in req.memory_context)
    store = orch._memory.store_for(first.session_id)
    clock_mem = next((m for m in store.snapshot()["deepseek"] if m.content == "墙上有个钟"), None)
    check("L2-a 召回强化（reinforcements>=1）", clock_mem is not None and clock_mem.reinforcements >= 1, str(clock_mem))

    # b) 反思回灌：默认关 → 开启
    print("\n-- L2-b: 反思回灌（默认关/开启） --")
    rt2 = _CaptureRuntime()
    orch2 = GameOrchestrator(SessionStore(), {"deepseek": rt2})
    s2 = orch2.handle_turn(None, "你好")
    orch2.handle_turn(s2.session_id, "在吗")
    check("L2-b 默认关：无反思不崩且请求不带 last_reflection", rt2.requests[1].last_reflection == "")
    rt3 = _CaptureRuntime()
    orch3 = GameOrchestrator(
        SessionStore(), {"deepseek": rt3}, reflector=Reflector(_ReflectionProvider())
    )
    s3 = orch3.handle_turn(None, "你好")
    orch3.handle_turn(s3.session_id, "在吗")
    check("L2-b 开启：下一轮请求带反思回灌", rt3.requests[1].last_reflection.startswith("我上一条"))

    # c) 一致性校验 fail-open
    print("\n-- L2-c: 一致性校验 fail-open --")
    rt4 = _CaptureRuntime()
    orch4 = GameOrchestrator(
        SessionStore(),
        {"deepseek": rt4},
        consistency_checker=SemanticConsistencyChecker(_FailingProvider()),
    )
    r4 = orch4.handle_turn(None, "你好")
    check("L2-c judge 不可达仍放行", bool(r4.response.dialogue), f"dialogue={r4.response.dialogue!r}")


def main() -> int:
    print(f"dialogue_smoke provider={os.environ.get('GAL_PROVIDER')}")
    layer1()
    layer2()
    print("\n" + "=" * 50)
    if FAILURES:
        print(f"结果：FAIL — {len(FAILURES)} 项失败：")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("结果：PASS — 全部冒烟项通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
