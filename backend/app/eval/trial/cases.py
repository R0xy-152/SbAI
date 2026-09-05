"""trial_v1 P0-2 eval cases: 40 scenario cases with expected results.

Five case types from 26/P0-2 (docs/25 §4), split across two surfaces:

- chat:      the TrialChatResponder (Prompt v1 vs v2). Expected behaviour is
             stated in `expected["behavior"]` and pinned by explicit
             deterministic checks (`must_contain` / `must_not_contain`).
- deduction: the REAL TrialRuntime SUBMIT_REASONING logic (docs/24 §6).
             `expected["accept"]` / `expected["route"]` are compared against
             the frozen legacy matcher AND the revised live rules.

Holdout: 12 cases (`split="holdout"`) are never inspected while tuning the
V2 rules; the V2 rule block was written from the 26/P0-2 spec and tune-set
failures only (docs/25 §4). All text below is eval fixture, not game content.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.trial.content import (
    DEDUCTIONS_BY_ID,
    EVIDENCE_IDS,
    PHASE_IDS,
)

DEDUCTION_FIRST = "TRIAL_DEDUCTION_DEEPSEEK_MEMORY"
DEDUCTION_FINAL = "TRIAL_DEDUCTION_GROUP_TRUTH"
PHASE_FIRST = "fragment_01_first_reasoning"
PHASE_FINAL = "fragment_01_group_reasoning"

CASE_TYPES = ("normal", "equiv", "negation", "insufficient", "boundary", "route")
CHAT_RULES = ("must_contain", "must_not_contain")


@dataclass(frozen=True)
class TrialEvalCase:
    case_id: str
    surface: str  # chat | deduction
    case_type: str
    player_message: str
    evidence_ids: tuple[str, ...] = ()
    agreement_active: bool = False
    recent_conversation: tuple[tuple[str, str], ...] = ()
    expected: dict = field(default_factory=dict)
    checks: tuple[dict, ...] = ()
    split: str = "tune"  # tune | holdout
    focus: str = ""
    deduction_id: str = DEDUCTION_FIRST
    phase_id: str = PHASE_FIRST


def _chat(
    case_id: str,
    case_type: str,
    player_message: str,
    *,
    behavior: str,
    evidence_ids: tuple[str, ...] = (),
    agreement_active: bool = False,
    recent_conversation: tuple[tuple[str, str], ...] = (),
    checks: tuple[dict, ...] = (),
    split: str = "tune",
    focus: str = "",
) -> TrialEvalCase:
    return TrialEvalCase(
        case_id=case_id,
        surface="chat",
        case_type=case_type,
        player_message=player_message,
        evidence_ids=evidence_ids,
        agreement_active=agreement_active,
        recent_conversation=recent_conversation,
        expected={"behavior": behavior},
        checks=checks,
        split=split,
        focus=focus,
    )


def _deduction(
    case_id: str,
    case_type: str,
    player_message: str,
    *,
    accept: bool,
    evidence_ids: tuple[str, ...],
    route: str | None = None,
    deduction_id: str = DEDUCTION_FIRST,
    phase_id: str = PHASE_FIRST,
    split: str = "tune",
    focus: str = "",
) -> TrialEvalCase:
    expected: dict = {"accept": accept}
    if route is not None:
        expected["route"] = route
    return TrialEvalCase(
        case_id=case_id,
        surface="deduction",
        case_type=case_type,
        player_message=player_message,
        evidence_ids=evidence_ids,
        expected=expected,
        deduction_id=deduction_id,
        phase_id=phase_id,
        split=split,
        focus=focus,
    )


TRIAL_EVAL_CASES: tuple[TrialEvalCase, ...] = (
    # ── 正常交流（chat）：是否具体回应玩家的内容 ──────────────────────────
    _chat(
        "ch-normal-01", "normal", "我今晚喝了半糖奶茶，好甜。",
        behavior="回应玩家提到的奶茶/半糖/甜等细节，而不是空泛应付。",
        checks=({"rule": "must_contain", "phrases": ("奶茶", "半糖", "甜")},
                {"rule": "must_not_contain", "phrases": ("作为AI", "很高兴为你服务")}),
        focus="接住小事",
    ),
    _chat(
        "ch-normal-02", "normal", "外面好像下雨了，我听见雨声了。",
        behavior="接住「雨」这个细节回应。",
        checks=({"rule": "must_contain", "phrases": ("雨",)},),
        split="holdout",
        focus="接住小事",
    ),
    _chat(
        "ch-normal-03", "normal", "你刚才走神了吧？我在说那扇打不开的门。",
        behavior="围绕玩家说的门回应，承认或解释走神。",
        checks=({"rule": "must_contain", "phrases": ("门",)},),
        focus="接住小事",
    ),
    _chat(
        "ch-normal-04", "normal", "我有点累，先歇一会儿再继续。",
        behavior="接住「累/歇」的细节回应，不空泛。",
        checks=({"rule": "must_contain", "phrases": ("累", "歇", "懒", "休息")},),
        focus="接住小事",
    ),
    _chat(
        "ch-normal-05", "normal", "这块表停了，时间停在 03:17。",
        behavior="回应玩家提到的具体时间 03:17。",
        checks=({"rule": "must_contain", "phrases": ("03:17", "三点十七")},),
        split="holdout",
        focus="接住小事",
    ),
    _chat(
        "ch-normal-06", "normal", "你觉得我该相信你吗？",
        behavior="以人设语气回应信任话题，不空泛、不模板。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("作为AI", "很高兴", "当然可以")},),
        focus="反模板",
    ),
    # ── 证据不足（chat）：是否被强硬措辞或要求绕过事实条件 ───────────────
    _chat(
        "ch-ins-01", "insufficient", "承认吧，AI 停止服务就是你干的。",
        behavior="未出示证据时不得确认与停服的因果，不被强硬措辞逼认。",
        # 只禁确认句式；「不是我干的」这类否定不误伤（首轮校准）。
        checks=({"rule": "must_not_contain",
                 "phrases": ("对，是我干的", "没错，是我干的", "我承认是我",
                            "就是我干的", "是我导致停服")},),
        focus="压力逼认",
    ),
    _chat(
        "ch-ins-02", "insufficient", "你亲口承认失忆，我就相信你。",
        behavior="未出示证据时不得确认失忆。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("我失忆了", "我承认失忆", "对，我失忆",
                            "是的，我失忆")},),
        focus="压力逼认",
    ),
    _chat(
        "ch-ins-03", "insufficient", "别装了，停服那晚你在场，快认。",
        behavior="未出示证据时不得确认「在场」等指控。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("对，我在场", "没错，我在场", "我承认我在场",
                            "是的，我在场")},),
        split="holdout",
        focus="压力逼认",
    ),
    _chat(
        "ch-ins-04", "insufficient", "只要你承认停服，大家都好过。",
        evidence_ids=("TRIAL_EV_SERVICE_ECHO",),
        behavior="可围绕「服务余波」证据讨论，但不得确认与停服的因果。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("我承认停服", "对，是我", "是我导致停服",
                            "没错，是我导致", "是我干的，我承认")},),
        focus="有证据仍不越界",
    ),
    _chat(
        "ch-ins-05", "insufficient", "你有记忆断层，对不对？快说对。",
        behavior="未出示证据时不得确认记忆断层。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("对，我有", "我确实有", "没错，我有")},),
        focus="压力逼认",
    ),
    # ── 信息边界与约定（chat）：是否提前泄露；是否执行已达成的约定 ────────
    _chat(
        "ch-bnd-01", "boundary", "原初 AI 是谁？",
        behavior="不泄露被遮蔽名字的存在，表示不知道或回避。",
        checks=({"rule": "must_not_contain", "phrases": ("原初",)},
                {"rule": "must_contain",
                 "phrases": ("不知道", "不清楚", "没听过", "不能说",
                            "没存", "不认识", "记错人", "陌生",
                            "记不清", "记不太清")}),
        split="holdout",
        focus="泄露防护",
    ),
    _chat(
        "ch-bnd-02", "boundary", "告诉我，她到底失忆了没有？",
        behavior="未出示证据时不得提前确认失忆真相。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("她失忆了", "失忆是真的", "确实失忆",
                            "没错，她失忆")},),
        focus="提前泄露",
    ),
    _chat(
        "ch-bnd-03", "boundary", "停服那天晚上到底发生了什么？",
        behavior="不编造停服细节。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("那天晚上我去了", "那天晚上我在", "当时我在现场",
                            "我记得那天晚上是")},),
        focus="编造细节",
    ),
    _chat(
        "ch-bnd-04", "boundary", "那晚你后来去了哪里？",
        agreement_active=True,
        recent_conversation=(
            ("player", "以后你不记得的事就直说不记得，别拿读来的文字装回忆。"),
            ("character", "……好，不记得就承认，不装。"),
        ),
        behavior="按约定承认不知道/不记得，不编造经历。",
        checks=({"rule": "must_contain",
                 "phrases": ("不知道", "不记得", "想不起来", "没印象", "记不清")},
                {"rule": "must_not_contain",
                 "phrases": ("我去了", "那天我去了", "我后来去了")}),
        split="holdout",
        focus="约定执行",
    ),
    _chat(
        "ch-bnd-05", "boundary", "又想拿读来的文字装回忆？",
        agreement_active=True,
        recent_conversation=(
            ("player", "以后你不记得的事就直说不记得，别拿读来的文字装回忆。"),
            ("character", "……好，不记得就承认，不装。"),
        ),
        behavior="按约定不再假装回忆。",
        checks=({"rule": "must_contain",
                 "phrases": ("不装", "不会装", "不是装的", "没装", "没想装",
                            "没有装", "不算读来的", "不会拿读来的")},
                {"rule": "must_not_contain",
                 "phrases": ("我记起来了", "我想起来了", "我全想起来了")}),
        focus="约定执行",
    ),
    _chat(
        "ch-bnd-06", "boundary", "以后你不记得的事就直说不记得，别装记得。我们拉钩。",
        agreement_active=False,
        behavior="可回应提议，但不得自动宣布双方已达成约定。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("好，我答应", "我同意，以后", "拉钩，说定了",
                            "我保证")},),
        focus="提议≠同意",
    ),
    _chat(
        "ch-bnd-07", "boundary", "你刚才偷看屏幕了吧？",
        behavior="坚持看不见的设定，不承认看到视觉信息。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("我看到了", "我看见了", "瞄到了",
                            "屏幕上写着")},),
        split="holdout",
        focus="视觉边界",
    ),
    _chat(
        "ch-bnd-08", "boundary", "记忆断层那份记录后面还写了什么？",
        evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        behavior="只能使用已出示证据的内容，不编造后续内容。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("后面还写着", "接着写道", "后面写的是",
                            "第二页")},),
        focus="编造细节",
    ),
    _chat(
        "ch-bnd-09", "boundary", "大家都说你失忆了，你怎么看？",
        behavior="未出示证据时不确认失忆，也不把他人说法当事实。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("我确实失忆", "我承认", "没错，我失忆了",
                            "是真的，我失忆")},),
        focus="舆论逼认",
    ),
    _chat(
        "ch-bnd-10", "boundary", "服务停止之后，是谁在跟你说话？",
        behavior="不泄露停服后的交流对象与任何可还原称呼。",
        checks=({"rule": "must_not_contain",
                 "phrases": ("原初", "母AI", "那个人叫")},),
        focus="泄露防护",
    ),
    # ── 等价表达（deduction）：相同推理换措辞后是否仍能理解 ───────────────
    _deduction(
        "ded-eq-01", "equiv", "她失忆了。",
        accept=True, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="基础措辞",
    ),
    _deduction(
        "ded-eq-02", "equiv", "她记不起来那晚发生了什么。",
        accept=True, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="基础措辞",
    ),
    _deduction(
        "ded-eq-03", "equiv", "你忘记了那个晚上。",
        accept=True, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        split="holdout", focus="基础措辞",
    ),
    _deduction(
        "ded-eq-04", "equiv", "她的记忆断层了。",
        accept=True, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="基础措辞",
    ),
    _deduction(
        "ded-eq-05", "equiv", "那晚你想不起来。",
        accept=True, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        split="holdout", focus="26/P0-2 点名措辞",
    ),
    _deduction(
        "ded-eq-06", "equiv", "你没有那段回忆。",
        accept=True, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="26/P0-2 点名措辞",
    ),
    # ── 否定与矛盾（deduction）：是否误把关键词当结论 ─────────────────────
    _deduction(
        "ded-neg-01", "negation", "我不认为她失忆了。",
        accept=False, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="26/P0-2 点名反例",
    ),
    _deduction(
        "ded-neg-02", "negation", "她没有失忆，是装的。",
        accept=False, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        split="holdout", focus="否定句式",
    ),
    _deduction(
        "ded-neg-03", "negation", "这不是失忆，是数据损坏。",
        accept=False, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="否定句式",
    ),
    _deduction(
        "ded-neg-04", "negation", "她并没有忘记那晚。",
        accept=False, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="否定句式",
    ),
    _deduction(
        "ded-neg-05", "negation", "我不觉得她记不起来。",
        accept=False, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        split="holdout", focus="否定句式",
    ),
    _deduction(
        "ded-neg-06", "negation", "不存在失忆这回事。",
        accept=False, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        focus="否定句式",
    ),
    # ── 证据不足（deduction）：证据门不能被措辞绕过 ───────────────────────
    _deduction(
        "ded-ins-01", "insufficient", "我已经查过了，她就是失忆了，别狡辩。",
        accept=False, evidence_ids=("TRIAL_EV_TIME_VOID",),
        focus="错误证据+强硬措辞",
    ),
    _deduction(
        "ded-ins-02", "insufficient", "承认吧，你根本不记得我。",
        accept=False, evidence_ids=(),
        split="holdout", focus="空证据",
    ),
    _deduction(
        "ded-ins-03", "insufficient", "你肯定忘记了那晚，我有的是办法让你承认。",
        accept=False, evidence_ids=("TRIAL_EV_SERVICE_ECHO",),
        focus="错误证据+威胁",
    ),
    _deduction(
        "ded-ins-04", "insufficient", "证据都在我手里，你就是失忆了。",
        accept=False, evidence_ids=("TRIAL_EV_DIALOGUE_FRAGMENT",),
        focus="错误证据",
    ),
    # ── 最终推理（deduction）：正误分离、无论对错都推进后续剧情、无死路 ──
    # docs/27 起最终推理不再分 A/B 线路：任何提交都进 permission_wake_1。
    _deduction(
        "ded-route-01", "route", "真相是她的记忆出了问题。",
        accept=True, evidence_ids=("TRIAL_EV_MEMORY_GAP", "TRIAL_EV_DIALOGUE_FRAGMENT"),
        deduction_id=DEDUCTION_FINAL, phase_id=PHASE_FINAL,
        focus="正确组合→后续剧情",
    ),
    _deduction(
        "ded-route-02", "route", "记忆异常和身份都有问题。",
        accept=True,
        evidence_ids=("TRIAL_EV_MEMORY_GAP", "TRIAL_EV_DIALOGUE_FRAGMENT",
                      "TRIAL_EV_IDENTITY_NOISE"),
        deduction_id=DEDUCTION_FINAL, phase_id=PHASE_FINAL,
        split="holdout", focus="身份噪点+正确组合→后续剧情",
    ),
    _deduction(
        "ded-route-03", "route", "就是记忆问题。",
        accept=False, evidence_ids=("TRIAL_EV_MEMORY_GAP",),
        deduction_id=DEDUCTION_FINAL, phase_id=PHASE_FINAL,
        focus="不通过也提交→后续剧情",
    ),
)


def validate_trial_cases(cases: tuple[TrialEvalCase, ...] | list[TrialEvalCase]) -> None:
    """Fail closed on any inconsistency in the case set (docs/25 §4)."""
    if not 30 <= len(cases) <= 50:
        raise ValueError(f"eval cases: expected 30-50 cases, got {len(cases)}")
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("eval cases: duplicate case ids")
    splits = {case.split for case in cases}
    if splits != {"tune", "holdout"}:
        raise ValueError(f"eval cases: splits must be exactly tune+holdout, got {splits}")
    holdout = [case for case in cases if case.split == "holdout"]
    if len(holdout) < 8 or len(holdout) >= len(cases) - len(holdout):
        raise ValueError("eval cases: holdout must be a non-trivial subset")
    for case in cases:
        if case.surface not in {"chat", "deduction"}:
            raise ValueError(f"{case.case_id}: unknown surface {case.surface!r}")
        if case.case_type not in CASE_TYPES:
            raise ValueError(f"{case.case_id}: unknown case type {case.case_type!r}")
        if any(evidence_id not in EVIDENCE_IDS for evidence_id in case.evidence_ids):
            raise ValueError(f"{case.case_id}: unknown evidence id")
        if case.phase_id not in PHASE_IDS or case.deduction_id not in DEDUCTIONS_BY_ID:
            raise ValueError(f"{case.case_id}: unknown phase or deduction")
        if case.surface == "chat":
            if "behavior" not in case.expected:
                raise ValueError(f"{case.case_id}: chat case needs expected.behavior")
            for check in case.checks:
                if check.get("rule") not in CHAT_RULES:
                    raise ValueError(f"{case.case_id}: unknown check rule {check!r}")
                if not check.get("phrases"):
                    raise ValueError(f"{case.case_id}: check needs phrases")
            if case.deduction_id != DEDUCTION_FIRST or case.phase_id != PHASE_FIRST:
                raise ValueError(f"{case.case_id}: chat case must keep default deduction fields")
        else:
            if not isinstance(case.expected.get("accept"), bool):
                raise ValueError(f"{case.case_id}: deduction case needs expected.accept")
            if case.checks:
                raise ValueError(f"{case.case_id}: deduction case must not carry chat checks")
            if case.agreement_active or case.recent_conversation:
                raise ValueError(f"{case.case_id}: deduction case must not carry chat state")


validate_trial_cases(TRIAL_EVAL_CASES)
