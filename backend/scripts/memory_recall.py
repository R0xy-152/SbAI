#!/usr/bin/env python3
"""记忆召回率实验（P0-2 补充：正确设计的确定性实验 + 真机端到端）。

背景：此前的 A/B 单轮质量分实验证明「单轮 LLM-as-judge 分数不是记忆系统
价值的合适度量」（见 validation-results/eval-ab/result.md）。本实验改为直接
度量「事实是否被带回上下文」——确定性、可复现，不依赖评审模型。

Layer 1（确定性，无需任何 LLM）：
  种 10 条一般记忆 + 6 条玩家画像 → 20 轮无关干扰对话（脚本内断言干扰消息
  与所有事实零相关性）→ 逐条探测：
    OFF 臂（纯近因窗口，探测消息与事实无关）＝ 无语义召回时的行为
    ON  臂（语义召回，探测消息与事实相关）＝ retrieve_context(query) 系统特性
  度量：一般记忆窗口命中率；玩家画像窗口命中率；召回强化与衰减侧查。

Layer 2（真机 DeepSeek，可选）：
  种 4 条玩家画像 + 6 条一般记忆 → 10 轮干扰 → 4 条相关提问 →
  检查回复是否引用目标事实（端到端：记忆 → 上下文 → 回复）。

用法：
  python scripts/memory_recall.py                       # Layer 1（mock 环境即可）
  GAL_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-xxx python scripts/memory_recall.py  # + Layer 2
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if __file__ and __file__ != "<stdin>":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.characters.base import (
    CharacterRequest,
    CharacterResponse,
    CharacterRuntime,
    MemoryProposal,
)
from app.game.memory import relevance_score
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore

# 一般记忆（token 唯一，query 与 content 有确定的 bigram 重叠）
GENERAL = [
    ("围巾", "玩家提到序章里出现过一条红色围巾", "那条红色围巾后来去哪了？"),
    ("收音机", "玩家说教室里有一台老式收音机", "那台收音机还能用吗？"),
    ("铁门", "玩家讲过走廊尽头有一扇铁门", "那扇铁门后面是什么？"),
    ("停电", "玩家记得停电发生在下午三点", "那天停电是几点？"),
    ("下雨", "玩家说窗外一直在下雨", "外面还在下雨吗？"),
    ("手套", "玩家提到自己丢了一只手套", "我的手套找到了吗？"),
    ("糖醋排骨", "玩家说过楼下食堂卖糖醋排骨", "食堂的糖醋排骨怎么样？"),
    ("蝉鸣", "玩家记得第一次见面时外面有蝉鸣", "那天真的有蝉鸣吗？"),
    ("箱子", "玩家说过宿舍床底下有个旧箱子", "床底下的箱子打开过吗？"),
    ("小路", "玩家提到学校后山有条小路", "后山的小路怎么走？"),
]

PLAYER = [
    ("小明", "player_name", "玩家叫小明", "小明是不是我的名字？"),
    ("怕黑", "player_fear", "玩家最怕黑", "我是不是说过我怕黑？"),
    ("安静", "player_like", "玩家喜欢安静的教室", "我说过喜欢安静的教室吗？"),
    ("围棋", "player_hobby", "玩家喜欢下围棋", "我是不是喜欢下围棋？"),
    ("温水", "player_habit", "玩家习惯喝温水", "我习惯喝温水吗？"),
    ("猫", "player_pet", "玩家小时候养过一只猫", "我小时候养过猫吗？"),
]

INTERFERENCE = [
    "今天天气不错。", "你在吗？", "嗯。", "继续。", "然后呢？",
    "随便聊聊。", "你吃饭了吗？", "哈哈。", "有意思。", "真的假的？",
    "好的。", "知道了。", "没别的事了。", "随便说说。", "今天过得怎么样？",
    "无聊。", "好吧。", "懂了。", "行。", "睡了吗？",
]

ALL_CONTENTS = [c for _t, c, _q in GENERAL] + [c for _t, _ty, c, _q in PLAYER]


class _CaptureRuntime(CharacterRuntime):
    character_id = "deepseek"
    persona_system = "测试人格（记忆召回实验桩）"

    def __init__(self) -> None:
        self.requests: list[CharacterRequest] = []

    def respond(self, request: CharacterRequest) -> CharacterResponse:
        self.requests.append(request)
        return CharacterResponse(
            character_id=self.character_id, dialogue="……嗯。", emotion="neutral"
        )


def _seed(orch: GameOrchestrator, session_id: str) -> None:
    store = orch._memory.store_for(session_id)
    for _token, content, _query in GENERAL:
        store.propose("deepseek", MemoryProposal("scene_note", content))
    for _token, mtype, content, _query in PLAYER:
        store.propose("deepseek", MemoryProposal(mtype, content))


def _arm(probe_on: bool):
    rt = _CaptureRuntime()
    orch = GameOrchestrator(SessionStore(), {"deepseek": rt})
    sid = orch.handle_turn(None, "你好。").session_id
    _seed(orch, sid)
    for message in INTERFERENCE:
        orch.handle_turn(sid, message)
    hits: dict[str, tuple[bool, bool]] = {}  # (在一般窗口, 在画像通道)
    for token, _content, query in GENERAL:
        orch.handle_turn(sid, query if probe_on else "你继续说。")
        request = rt.requests[-1]
        hits["general:" + token] = (
            token in request.memory_context,
            token in request.player_notes,
        )
    for token, _mtype, _content, query in PLAYER:
        orch.handle_turn(sid, query if probe_on else "你继续说。")
        request = rt.requests[-1]
        hits["player:" + token] = (
            token in request.memory_context,
            token in request.player_notes,
        )
    store = orch._memory.store_for(sid)
    return hits, store, rt


def layer1() -> None:
    print("== Layer 1: 确定性召回率（OFF=纯近因窗口 / ON=语义召回） ==")
    # 实验前提断言：干扰消息与所有事实零相关性（否则干扰轮会意外强化事实）
    leaks = [
        (m, c)
        for m in INTERFERENCE
        for c in ALL_CONTENTS
        if relevance_score(m, c) > 0
    ]
    if leaks:
        print("  [FAIL] 干扰消息与事实存在相关性，实验无效：", leaks[:3])
        return
    print("  [OK] 干扰消息与全部 16 条事实零相关性（relevance_score=0）")

    off_hits, off_store, _off_rt = _arm(probe_on=False)
    on_hits, on_store, _on_rt = _arm(probe_on=True)

    def render(pair):
        in_gen, in_pl = pair
        if in_gen and in_pl:
            return "GEN+PL"
        if in_gen:
            return "GEN(泄漏通道)"
        if in_pl:
            return "PL(画像通道)"
        return "MISS"

    print("  一般记忆窗口命中（cap=5；GEN=一般窗口）：")
    for token, _c, _q in GENERAL:
        off_g, _ = off_hits["general:" + token]
        on_g, _ = on_hits["general:" + token]
        print(f"    {token}: OFF={'GEN' if off_g else 'MISS'}  ON={'GEN' if on_g else 'MISS'}")
    print("  玩家画像命中（PL=画像通道；GEN=溢出后走一般窗口，分区不变量被破坏）：")
    for token, _t, _c, _q in PLAYER:
        off_g, off_pl = off_hits["player:" + token]
        on_g, on_pl = on_hits["player:" + token]
        def label(g, pl):
            return "GEN+PL" if g and pl else ("GEN" if g else ("PL" if pl else "MISS"))
        print(f"    {token}: OFF={label(off_g, off_pl)}  ON={label(on_g, on_pl)}")

    gen_off = sum(1 for k, v in off_hits.items() if k.startswith("general:") and v[0])
    gen_on = sum(1 for k, v in on_hits.items() if k.startswith("general:") and v[0])
    pl_off = sum(1 for k, v in off_hits.items() if k.startswith("player:") and v[1])
    pl_on = sum(1 for k, v in on_hits.items() if k.startswith("player:") and v[1])
    leak_off = sum(1 for k, v in off_hits.items() if k.startswith("player:") and v[0])
    leak_on = sum(1 for k, v in on_hits.items() if k.startswith("player:") and v[0])
    print(f"  汇总：一般记忆窗口 OFF {gen_off}/10 vs ON {gen_on}/10；玩家画像通道 OFF {pl_off}/6 vs ON {pl_on}/6")
    print(f"  画像经一般窗口泄漏通道命中：OFF {leak_off}/6 vs ON {leak_on}/6（分区不变量在窗口溢出时被破坏，见记录）")

    # 侧查：召回强化（一般窗口被召回的记忆 reinforcements>=1）
    snap = on_store.snapshot()["deepseek"]
    recalled = [m for m in snap if m.reinforcements >= 1]
    print(f"  侧查：ON 臂结束后被强化过的记忆 {len(recalled)}/16 条（一般窗口召回即强化，玩家画像不参与强化）")
    never = [m for m in snap if m.reinforcements == 0]
    print(f"  侧查：0 次强化的记忆 {len(never)} 条：" + "、".join(m.content[:12] for m in never))


def layer2() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("== Layer 2: 真机端到端（跳过：无 DEEPSEEK_API_KEY，请在服务器执行） ==")
        return
    from app.characters.deepseek import DeepSeekRuntime
    from app.providers.deepseek import DeepSeekProvider

    print("== Layer 2: 真机端到端（记忆 → 上下文 → 回复引用） ==")
    orch = GameOrchestrator(
        SessionStore(), {"deepseek": DeepSeekRuntime(DeepSeekProvider())}
    )
    sid = orch.handle_turn(None, "你好。").session_id
    store = orch._memory.store_for(sid)
    for _token, content, _q in GENERAL[:6]:
        store.propose("deepseek", MemoryProposal("scene_note", content))
    for _token, mtype, content, _q in PLAYER[:4]:
        store.propose("deepseek", MemoryProposal(mtype, content))
    for message in INTERFERENCE[:10]:
        orch.handle_turn(sid, message)
    probes = [
        ("怕黑", "我是不是说过我怕什么？"),
        ("小明", "你还记得我叫什么吗？"),
        ("围棋", "我平时喜欢玩什么棋？"),
        ("温水", "我习惯喝什么温度的水？"),
    ]
    hits = 0
    for token, query in probes:
        result = orch.handle_turn(sid, query)
        dialogue = result.response.dialogue
        hit = token in dialogue
        hits += 1 if hit else 0
        print(f"  [{'HIT' if hit else 'MISS'}] {token}: {dialogue[:50]!r}")
    print(f"  真机端到端引用命中 {hits}/{len(probes)}")


def main() -> int:
    layer1()
    print("")
    layer2()
    return 0


if __name__ == "__main__":
    sys.exit(main())
