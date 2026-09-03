#!/usr/bin/env python3
"""真实玩家会话回放：合并后记忆管线在真实输入上的行为（生产数据复验）。

输入：/tmp/game_saves.jsonl（生产 PostgreSQL game_saves 快照，真实玩家数据；
不入库、不入仓库）。每行一个快照 JSON。

A. 兼容性：快照经 JsonSessionRepository 当前代码解析（_session_from_dict）。
B. 回放写入：快照内玩家消息按原顺序走 GameOrchestrator（真机 DeepSeek），
   度量：模型记忆提案数 → 最终落库数（差值 = 去重 + 写门拒绝）。
C. 真实分布召回增益：回放结束后，用每条真实玩家消息作 query，
   对比 retrieve_context(query=msg) 与 retrieve_context(query=None)：
   救回 = 与消息相关（bigram>0）且被语义召回带回窗口的记忆条次。
D. 分区不变量：全部真实消息上，一般窗口含 player_* 的次数（修复后应恒 0）。

用法：
  python scripts/memory_realdata.py /tmp/game_saves.jsonl            # mock（占位）
  GAL_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-xxx python scripts/memory_realdata.py /tmp/game_saves.jsonl  # 真机
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

if __file__ and __file__ != "<stdin>":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.characters.base import CharacterRuntime, CharacterResponse, MemoryProposal
from app.characters.claude import ClaudeRuntime
from app.characters.chatgpt import ChatGPTRuntime
from app.characters.deepseek import DeepSeekRuntime
from app.game.memory import relevance_score
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository
from app.providers.deepseek import DeepSeekProvider
from app.providers.mock import MockProvider


def _load_saves(path: str) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8").strip()
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def _build_orchestrator():
    # 真机：DeepSeek 实时生成（回复短，无 prompt 回显膨胀问题）。
    if os.environ.get("DEEPSEEK_API_KEY"):
        provider = DeepSeekProvider()
        runtimes = {
            "deepseek": DeepSeekRuntime(provider),
            "claude": ClaudeRuntime(provider),
            "chatgpt": ChatGPTRuntime(provider),
        }
        return GameOrchestrator(SessionStore(), runtimes, default_character="deepseek")

    # 无 key：本地占位桩（注意：不能用 MockProvider 回放——它把整个 prompt
    # 回显进 dialogue，历史递归引用导致第 25 轮左右指数膨胀卡死）。
    print("（未检测到 DEEPSEEK_API_KEY：回放用本地桩，全部度量为占位值）")

    class _Stub(CharacterRuntime):
        character_id = "deepseek"
        persona_system = "回放占位桩"

        def respond(self, request):
            return CharacterResponse(
                character_id=self.character_id, dialogue="……嗯。", emotion="neutral"
            )

    return GameOrchestrator(SessionStore(), {"deepseek": _Stub()}, default_character="deepseek")


def compat_check(saves: list[dict]) -> tuple[int, int]:
    ok = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = JsonSessionRepository(tmpdir)
        for snap in saves:
            path = Path(tmpdir) / (snap["session_id"] + ".json")
            path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
            if repo.load(snap["session_id"]) is not None:
                ok += 1
    return ok, len(saves)


def replay_and_measure(save: dict, orch: GameOrchestrator) -> dict:
    player_messages = [
        m["content"]
        for m in save.get("messages", [])
        if m.get("role") == "player" and m.get("content", "").strip()
    ]
    sid = None
    proposals_emitted = 0
    for content in player_messages:
        result = orch.handle_turn(sid, content)
        sid = result.session_id
        proposals_emitted += len(result.response.memory_proposals)
    store = orch._memory.store_for(sid)
    snapshot = store.snapshot().get("deepseek", [])
    all_mems = snapshot
    player_mems = [m for m in all_mems if m.memory_type.startswith("player_")]

    rescued_total = 0
    relevant_out_total = 0
    violations = 0
    for content in player_messages:
        gen_q, notes_q = store.retrieve_context(
            "deepseek", limit=5, player_note_limit=5, query=content
        )
        gen_n, notes_n = store.retrieve_context(
            "deepseek", limit=5, player_note_limit=5, query=None
        )
        if any(m.memory_type.startswith("player_") for m in gen_q):
            violations += 1
        window_n = set(gen_n + notes_n)
        window_q = set(gen_q + notes_q)
        relevant = [m for m in all_mems if relevance_score(content, m.content) > 0]
        relevant_out = [m for m in relevant if m not in window_n]
        rescued = [m for m in relevant_out if m in window_q]
        relevant_out_total += len(relevant_out)
        rescued_total += len(rescued)

    return {
        "player_turns": len(player_messages),
        "proposals_emitted": proposals_emitted,
        "final_memories": len(all_mems),
        "player_notes": len(player_mems),
        "general_memories": len(all_mems) - len(player_mems),
        "relevant_out_without_query": relevant_out_total,
        "rescued_by_query": rescued_total,
        "partition_violations": violations,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python scripts/memory_realdata.py /tmp/game_saves.jsonl")
        return 2
    saves = _load_saves(sys.argv[1])
    print(f"快照数：{len(saves)}")
    ok, total = compat_check(saves)
    print(f"A. 兼容性：当前代码解析 {ok}/{total} 份生产快照（JsonSessionRepository）")

    print("B/C/D. 回放与度量（角色：deepseek；消息按原顺序）")
    totals = {
        "player_turns": 0, "proposals_emitted": 0, "final_memories": 0,
        "player_notes": 0, "general_memories": 0,
        "relevant_out_without_query": 0, "rescued_by_query": 0,
        "partition_violations": 0,
    }
    for index, save in enumerate(saves):
        orch = _build_orchestrator()
        result = replay_and_measure(save, orch)
        print(
            f"  存档 {index}（{save['session_id'][:8]}…）："
            f"玩家消息 {result['player_turns']} 条，提案 {result['proposals_emitted']} → "
            f"落库 {result['final_memories']}（画像 {result['player_notes']} / 一般 {result['general_memories']}）"
        )
        print(
            f"    召回增益：纯近因窗口会漏掉的相关记忆 {result['relevant_out_without_query']} 条次，"
            f"语义召回救回 {result['rescued_by_query']} 条次；分区违规 {result['partition_violations']}"
        )
        for key in totals:
            totals[key] += result[key]

    print("汇总：")
    print(f"  玩家消息 {totals['player_turns']} 条；模型记忆提案 {totals['proposals_emitted']}；"
          f"落库 {totals['final_memories']}（画像 {totals['player_notes']} / 一般 {totals['general_memories']}）")
    if totals["relevant_out_without_query"]:
        rate = totals["rescued_by_query"] / totals["relevant_out_without_query"]
        print(f"  真实分布召回增益：救回 {totals['rescued_by_query']}/"
              f"{totals['relevant_out_without_query']}（{rate:.0%}）")
    else:
        print("  真实分布召回增益：无相关-漏出条次（落库记忆与真实消息无相关性重叠，增益不可测）")
    print(f"  分区不变量违规：{totals['partition_violations']}（修复后应恒 0）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
