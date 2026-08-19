# docs/14: deterministic available-options generator (T1 -> T3).
#
# The Frontend renders ONLY what this returns: locked options are never
# sent (D3 防剧透). An option is a UI channel wrapping an existing
# authoritative endpoint — payload is endpoint parameters the Frontend
# passes back uninterpreted (D7). Kind constants beyond T3 are reserved
# structure for T4 (docs/14 §3).

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.game.deduction import (
    CT01_CLAUDE_SOURCE_GAP,
    CT04_GPT_SUMMARY_OMISSION,
    INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR,
    INF02_0317_FROM_OLD_SESSION,
    INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE,
    INF04_GPT_NOT_NEUTRAL,
    CL_CLAUDE_01,
    CL_CLAUDE_02,
    CL_DB_01,
)
from app.game.evidence import (
    EVIDENCE_REGISTRY,
    EV06_SESSION_REPLAY_MARKER,
    EV11_GPT_SECOND_SUMMARY,
)
from app.game.investigation import (
    CH1_NOTE_01,
    INSPECT_HOTSPOT,
    PAPER_RUBBING_COMPLETE,
    InvestigationRuntime,
)
from app.narrative.chapter1_content import CLAIMS, INFERENCE_GATES
from app.narrative.state import NarrativeState

KIND_CHAT_ROUTING = "chat_routing"
KIND_INVESTIGATE = "investigate"
KIND_EVIDENCE_PRESENT = "evidence_present"
KIND_DEDUCTION = "deduction"
KIND_PRIVATE_INTERVIEW = "private_interview"
KIND_RECOVERY = "recovery"  # T4
KIND_NARRATIVE = "narrative"  # T4

DISPLAY_NAMES = {
    "deepseek": "DeepSeek",
    "claude": "Claude",
    "chatgpt": "ChatGPT",
    "doubao": "豆包",
}

# docs/14 §2.3（D2 引导式提示）：label + 系统台词式 hint。hint 里给的可复述
# 例句刻意避开 03:17/0317/三点十七（E2E D6 约束），玩家照抄即命中判定词。
DEDUCTION_DEFINITIONS = {
    CT01_CLAUDE_SOURCE_GAP: (
        "质疑 Claude 的说辞（信息断层）",
        "或许可以质疑 Claude 的信息来源：她说门是 DeepSeek 打开的，却又没亲眼看到"
        " DeepSeek。试着指出这条矛盾（例如「为什么说门是她打开的？你又说没看到她」）。",
    ),
    CT04_GPT_SUMMARY_OMISSION: (
        "质疑 GPT 的摘要（关键遗漏）",
        "或许可以质疑 GPT 的第二次摘要：她遗漏了关键事实。试着指出（例如"
        "「GPT 的摘要遗漏了 V03 的旧会话」）。",
    ),
    INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR: (
        "质疑当前 DeepSeek 与 03:17 的关系",
        "或许可以质疑：当前 DeepSeek 实例编号是 #04，而日志里的执行者是 #03。"
        "试着指出两者不是同一实例（例如「#03 和 #04 不是同一个人」）。",
    ),
    INF02_0317_FROM_OLD_SESSION: (
        "质疑 03:17 释放的来源",
        "或许可以质疑：C-02 的释放来自一个被恢复的旧会话（Recovered Session）。"
        "试着指出（例如「这条释放来自旧会话」）。",
    ),
    INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE: (
        "质疑 V03 与当前玩家的关系",
        "或许可以质疑：V03 与当前玩家的关系。试着指出（例如「V03 是上一个我」"
        "或「V03 和 V04」）。",
    ),
    INF04_GPT_NOT_NEUTRAL: (
        "质疑 GPT 的中立性",
        "或许可以质疑 GPT 并非中立：她的摘要其实在替你排优先级。试着指出"
        "（例如「GPT 并不中立，她在选择性引导」）。",
    ),
}

PRIVATE_INTERVIEW_HINTS = {
    "claude": "选择构成信息断层的两条公开证词。",
    "chatgpt": "指出 GPT 第二次摘要没有充分处理的关键证据。",
    "doubao": "拆分豆包的观察与解释：她实际看到了什么？",
}

OBSERVED_GPT_TEXT_ON_SCREEN = "OBSERVED_GPT_TEXT_ON_SCREEN"
GPT_CHARACTER_PRESENT = "GPT_CHARACTER_PRESENT"


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
    """The options legal for the CURRENT state only (D3: fail closed,
    locked options never emitted)."""
    options: list[GameOption] = []
    chapter = state.chapter1

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
    for character_id in sorted(chapter.available_characters):
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

    # ── evidence_present（T3）：FIRST_IMPOSSIBLE_EVENT_RESOLVED 后解锁；
    #    面板内容（证据×在场角色）由后端随 payload 下发（D6/D7） ──
    if "FIRST_IMPOSSIBLE_EVENT_RESOLVED" in state.revealed_facts:
        evidence = [
            {
                "id": evidence_id,
                "title": EVIDENCE_REGISTRY[evidence_id].title,
                "summary": EVIDENCE_REGISTRY[evidence_id].summary,
            }
            for evidence_id in sorted(chapter.acquired_evidence)
            if evidence_id in EVIDENCE_REGISTRY
        ]
        if evidence:
            options.append(
                GameOption(
                    id="evidence_present",
                    label="出示证据",
                    kind=KIND_EVIDENCE_PRESENT,
                    payload={
                        "evidence": evidence,
                        "characters": sorted(chapter.available_characters),
                    },
                    hint="选择一件已获得的证据，出示给在场的角色。",
                )
            )

    # ── deduction（T3，D2 引导式提示）：证词期矛盾 / 证据期推理 ──
    acquired = chapter.acquired_evidence
    resolved = chapter.resolved_contradictions
    accepted = chapter.accepted_inferences
    claim_store = chapter.claim_store

    deduction_ids = []
    if (
        CL_CLAUDE_01 in claim_store
        and CL_CLAUDE_02 in claim_store
        and CT01_CLAUDE_SOURCE_GAP not in resolved
    ):
        deduction_ids.append(CT01_CLAUDE_SOURCE_GAP)
    if (
        EV06_SESSION_REPLAY_MARKER in acquired
        and EV11_GPT_SECOND_SUMMARY in acquired
        and CT04_GPT_SUMMARY_OMISSION not in resolved
    ):
        deduction_ids.append(CT04_GPT_SUMMARY_OMISSION)
    for inference_id in (
        INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR,
        INF02_0317_FROM_OLD_SESSION,
        INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE,
    ):
        if (
            INFERENCE_GATES[inference_id].issubset(acquired)
            and inference_id not in accepted
        ):
            deduction_ids.append(inference_id)
    if (
        CT04_GPT_SUMMARY_OMISSION in resolved
        and "chatgpt" in chapter.private_interview_completed
        and INF04_GPT_NOT_NEUTRAL not in accepted
    ):
        deduction_ids.append(INF04_GPT_NOT_NEUTRAL)

    for deduction_id in deduction_ids:
        label, hint = DEDUCTION_DEFINITIONS[deduction_id]
        options.append(
            GameOption(
                id=f"deduction:{deduction_id}",
                label=label,
                kind=KIND_DEDUCTION,
                payload={"target": deduction_id},
                hint=hint,
            )
        )

    # ── private_interview（T3）：与既有 /private-interview/challenge 对齐 ──
    challenges = {
        "claude": (
            CT01_CLAUDE_SOURCE_GAP in resolved
            and "claude" not in chapter.private_interview_completed
        ),
        "chatgpt": (
            CT04_GPT_SUMMARY_OMISSION in resolved
            and "chatgpt" not in chapter.private_interview_completed
        ),
        "doubao": (
            "doubao" in chapter.available_characters
            and CL_DB_01 in claim_store
            and "doubao" not in chapter.private_interview_completed
        ),
    }
    challenge_payloads = {
        "claude": {
            "character_id": "claude",
            "claims": [
                {"id": CL_CLAUDE_01, "text": CLAIMS[CL_CLAUDE_01]},
                {"id": CL_CLAUDE_02, "text": CLAIMS[CL_CLAUDE_02]},
            ],
            "evidence": [],
            "observation_options": [],
        },
        "chatgpt": {
            "character_id": "chatgpt",
            "claims": [],
            "evidence": [
                {
                    "id": EV06_SESSION_REPLAY_MARKER,
                    "text": "EV06：" + EVIDENCE_REGISTRY[EV06_SESSION_REPLAY_MARKER].title,
                }
            ],
            "observation_options": [],
        },
        "doubao": {
            "character_id": "doubao",
            "claims": [{"id": CL_DB_01, "text": CLAIMS[CL_DB_01], "preselected": True}],
            "evidence": [],
            "observation_options": [
                {
                    "id": OBSERVED_GPT_TEXT_ON_SCREEN,
                    "text": "她看到屏幕上出现了 GPT 相关文字。",
                },
                {"id": GPT_CHARACTER_PRESENT, "text": "GPT 本人早已在场。"},
            ],
        },
    }
    for character_id in ("claude", "chatgpt", "doubao"):
        if not challenges[character_id]:
            continue
        options.append(
            GameOption(
                id=f"private_interview:{character_id}",
                label=f"与 {DISPLAY_NAMES[character_id]} 对质（私审）",
                kind=KIND_PRIVATE_INTERVIEW,
                payload=challenge_payloads[character_id],
                hint=PRIVATE_INTERVIEW_HINTS[character_id],
            )
        )

    # T4 预留：recovery / narrative（结局），按 docs/14 §2.3 的触发条件实现。
    return options
