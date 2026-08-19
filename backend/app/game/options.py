"""docs/14: deterministic available-options generator (T1).

The Frontend renders ONLY what this returns: locked options are never
sent (D3 防剧透). An option is a UI channel wrapping an existing
authoritative endpoint — ``payload`` is endpoint parameters the Frontend
passes back uninterpreted (D7). Kind constants beyond T1 are reserved
structure for T3/T4 (docs/14 §3).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.game.investigation import (
    CH1_NOTE_01,
    INSPECT_HOTSPOT,
    PAPER_RUBBING_COMPLETE,
    InvestigationRuntime,
)
from app.narrative.state import NarrativeState

KIND_CHAT_ROUTING = "chat_routing"
KIND_INVESTIGATE = "investigate"
KIND_EVIDENCE_PRESENT = "evidence_present"  # T3
KIND_DEDUCTION = "deduction"  # T3（引导式提示，D2）
KIND_PRIVATE_INTERVIEW = "private_interview"  # T3
KIND_RECOVERY = "recovery"  # T4
KIND_NARRATIVE = "narrative"  # T4

DISPLAY_NAMES = {
    "deepseek": "DeepSeek",
    "claude": "Claude",
    "chatgpt": "ChatGPT",
    "doubao": "豆包",
}


@dataclass(frozen=True)
class GameOption:
    id: str
    label: str
    kind: str
    payload: dict
    hint: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def build_options(
    state: NarrativeState, default_character: str = "deepseek"
) -> list[GameOption]:
    """The options legal for the CURRENT state only (D3: fail closed,"
    locked options never emitted)."""
    options: list[GameOption] = []

    # ── investigate（docs/14 §2.3）：当前可调查且未完成的热点 ──
    for hotspot in InvestigationRuntime.available_hotspots(state):
        hotspot_id = hotspot["hotspot_id"]
        if state.chapter1.hotspot_states.get(hotspot_id) == "completed":
            continue
        steps = [{"action": INSPECT_HOTSPOT, "hotspot_id": hotspot_id}]
        if hotspot_id == CH1_NOTE_01:
            # 纸面拓印：inspect 后立即可拓印，一个选项两步执行（旧前端同流程）
            steps.append({"action": PAPER_RUBBING_COMPLETE, "hotspot_id": hotspot_id})
        options.append(
            GameOption(
                id=f"investigate:{hotspot_id}",
                label=hotspot["title"],
                kind=KIND_INVESTIGATE,
                payload={"steps": steps},
                hint=hotspot["preview"],
            )
        )

    # ── chat_routing（D5）：登场角色的对话路由；默认回应者无需选 ──
    for character_id in sorted(state.chapter1.available_characters):
        if character_id == default_character or character_id not in DISPLAY_NAMES:
            continue
        options.append(
            GameOption(
                id=f"chat_routing:{character_id}",
                label=f"找 {DISPLAY_NAMES[character_id]} 谈谈",
                kind=KIND_CHAT_ROUTING,
                payload={"character_id": character_id},
            )
        )

    # T3/T4 预留：evidence_present / deduction（引导式提示）/ private_interview /
    # recovery / narrative，按 docs/14 §2.3 的触发条件实现，同样未解锁不下发。
    return options
