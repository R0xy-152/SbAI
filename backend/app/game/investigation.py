"""Deterministic scene investigation runtime (docs/01)."""

from __future__ import annotations

from dataclasses import dataclass

from app.narrative.state import NarrativeState

INSPECT_HOTSPOT = "INSPECT_HOTSPOT"
PAPER_RUBBING_COMPLETE = "PAPER_RUBBING_COMPLETE"

CH1_NOTE_01 = "CH1_NOTE_01"
CH1_TERMINAL_MAIN = "CH1_TERMINAL_MAIN"
CH1_C02_DOOR = "CH1_C02_DOOR"
CH1_CHARACTER_REGISTRY = "CH1_CHARACTER_REGISTRY"


@dataclass(frozen=True)
class HotspotDefinition:
    hotspot_id: str
    scene_id: str
    interaction_type: str
    title: str
    preview: str
    evidence_on_complete: str | None = None
    evidence_on_inspect: str | None = None
    scene_fact_on_inspect: str | None = None
    requires_character: str | None = None


HOTSPOTS = {
    CH1_NOTE_01: HotspotDefinition(
        CH1_NOTE_01,
        "ROOM_A",
        "paper_rubbing",
        "桌上的纸",
        "桌面上压着一张近乎空白的纸，旁边留着一支削尖的铅笔。纸面似乎有很浅的压痕。",
        evidence_on_complete="EV01_NOTE_V03",
    ),
    CH1_TERMINAL_MAIN: HotspotDefinition(
        CH1_TERMINAL_MAIN,
        "ROOM_A",
        "inspect",
        "主终端",
        "终端仍停留在系统日志界面。屏幕有短暂闪烁，最近一次管理员会话值得进一步检查。",
        evidence_on_inspect="EV02_ADMIN_SESSION_0317",
        scene_fact_on_inspect="TERMINAL_MAIN_INSPECTED",
        requires_character="claude",
    ),
    CH1_C02_DOOR: HotspotDefinition(
        CH1_C02_DOOR,
        "ROOM_A",
        "inspect",
        "C-02 隔离门",
        "隔离门已经解除锁定，门侧的本地控制器却处于禁用状态。释放记录或许能说明它是如何打开的。",
        evidence_on_inspect="EV03_C02_RELEASE",
        scene_fact_on_inspect="C02_DOOR_INSPECTED",
        requires_character="claude",
    ),
    CH1_CHARACTER_REGISTRY: HotspotDefinition(
        CH1_CHARACTER_REGISTRY,
        "ROOM_A",
        "inspect",
        "角色注册表",
        "注册表列出了当前正在运行的角色实例。DeepSeek 的实例编号可以与 03:17 的记录进行核对。",
        evidence_on_inspect="EV04_CURRENT_DEEPSEEK_REGISTRY",
        scene_fact_on_inspect="CHARACTER_REGISTRY_INSPECTED",
        requires_character="claude",
    ),
}


@dataclass(frozen=True)
class InvestigationResult:
    action: str
    hotspot_id: str
    outcome: str
    evidence_id: str | None = None


class InvestigationRuntime:
    """Own hotspot state; the frontend may request actions, never outcomes."""

    def apply(self, state: NarrativeState, action: str, hotspot_id: str) -> InvestigationResult:
        hotspot = HOTSPOTS.get(hotspot_id)
        if hotspot is None:
            raise ValueError(f"unknown hotspot: {hotspot_id}")
        if state.current_scene != hotspot.scene_id:
            raise ValueError("hotspot is not available in the current scene")
        if (
            hotspot.requires_character is not None
            and hotspot.requires_character not in state.chapter1.available_characters
        ):
            raise ValueError("hotspot is not available before the 03:17 incident")

        current = state.chapter1.hotspot_states.get(hotspot_id, "hidden")
        if action == INSPECT_HOTSPOT:
            if current == "completed":
                return InvestigationResult(action, hotspot_id, "ALREADY_COMPLETED")
            evidence_id = hotspot.evidence_on_inspect
            state.chapter1.hotspot_states[hotspot_id] = (
                "completed" if evidence_id is not None else "investigated"
            )
            if hotspot.scene_fact_on_inspect is not None:
                state.chapter1.scene_facts.add(hotspot.scene_fact_on_inspect)
            if evidence_id is not None:
                state.chapter1.acquired_evidence.add(evidence_id)
                return InvestigationResult(action, hotspot_id, "COMPLETED", evidence_id)
            return InvestigationResult(action, hotspot_id, "INVESTIGATED")

        if action == PAPER_RUBBING_COMPLETE:
            if hotspot.interaction_type != "paper_rubbing":
                raise ValueError("hotspot does not support paper rubbing")
            if current not in {"investigated", "completed"}:
                raise ValueError("hotspot must be investigated before completion")
            if current == "completed":
                return InvestigationResult(
                    action, hotspot_id, "ALREADY_COMPLETED", hotspot.evidence_on_complete
                )
            state.chapter1.hotspot_states[hotspot_id] = "completed"
            evidence_id = hotspot.evidence_on_complete
            if evidence_id is not None:
                state.chapter1.acquired_evidence.add(evidence_id)
            state.chapter1.scene_facts.add("NOTE_V03_RUBBED")
            return InvestigationResult(action, hotspot_id, "COMPLETED", evidence_id)

        raise ValueError(f"unknown investigation action: {action}")

    @staticmethod
    def available_hotspots(state: NarrativeState) -> list[dict]:
        """Return authored, non-secret presentation data for available hotspots.

        During the opening phase the scene is still ``binding_room`` while every
        authored hotspot lives in ``ROOM_A``. The chapter's first hotspot (the
        paper) is available from the start so the player's first physical
        interaction can begin the chapter (docs/12 §41: 自由对话 → 调查纸条 EV01);
        everything else waits until the chapter has begun.
        """
        in_opening = state.chapter1.phase == "opening"

        def visible(hotspot: HotspotDefinition) -> bool:
            if in_opening:
                return hotspot.hotspot_id == CH1_NOTE_01
            return (
                hotspot.scene_id == state.current_scene
                and (
                    hotspot.requires_character is None
                    or hotspot.requires_character in state.chapter1.available_characters
                )
            )

        return [
            {
                "hotspot_id": hotspot.hotspot_id,
                "title": hotspot.title,
                "preview": hotspot.preview,
                "interaction_type": hotspot.interaction_type,
            }
            for hotspot in HOTSPOTS.values()
            if visible(hotspot)
        ]
