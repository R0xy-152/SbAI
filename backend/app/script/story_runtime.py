"""快速上线固定剧本 Runtime（临时，非生产组件）。

对应 docs/story/07-First-Chapter-Script-v2-DeepSeek-Rewrite.md 的临时落地：
AI 回复停用，玩家以「点继续推进、选项点选 A/B/C」的方式走完整个第一章骨架。
与既有的 Script DSL（docs/12，事件触发式）**并行存在、互不依赖**：本 Runtime
只做纯线性节点游标，不触碰 NarrativeState / Evidence / Investigation 等既有
权威状态——旧调查玩法代码原样保留，只是入口隐藏（用户确认）。

边界（用户明确指示）：
- 内容来自评审阶段文稿 docs/story/07，只作快速上线临时采用；
- 音效、缺失立绘、完整剧情一律不在本组件内实现，后续以正式版替换。

节点图结构（链表，非扁平列表）：
- StoryLine —— 一句台词（speaker 可为 system / player / 四角色），携带 next；
- StoryChoice —— 一个选项点，选择后跳入对应分支的第一句；
- 每个分支的最后一句的 next 指向「选项后合并的主线」，分支台词绝不进入
  主线推进序列（避免 advance 走进别的分支造成环）。

持久化：cursor 为 {"node_index": int}，随 PersistedSession.story_cursor 走既有
Session / Save 快照链路，刷新、读档、自动存档都自然携带剧本进度。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.characters.base import ALLOWED_EMOTIONS
from app.script.story_content import SCENE_PRESENTATION, SCENES

# 场景演出允许的命名效果（与前端 ScreenEffects 渲染白名单一致；
# presentation/actions.py 的 SCREEN_GLITCH / SCREEN_SHAKE 同源命名）。
KNOWN_STORY_EFFECTS = frozenset({"SCREEN_GLITCH", "SCREEN_SHAKE"})

# 允许的说话者。chatgpt 在 07 骨架中没有字面台词（只有转述），但保留在集合
# 内以便后续补充对白时无需改校验。
_SPEAKERS = frozenset({"system", "player", "deepseek", "claude", "chatgpt", "doubao"})


class StoryContentError(ValueError):
    """剧本内容载入校验失败（fail closed：坏内容绝不上线）。"""


@dataclass
class StoryLine:
    speaker: str
    text: str
    emotion: str
    scene_id: str
    next_index: int = -1


@dataclass
class StoryChoice:
    choice_id: str
    scene_id: str
    options: tuple[tuple[str, str], ...]  # ((option_id, label), ...)
    first_index_by_option: dict[str, int] = field(default_factory=dict)


class StoryRuntime:
    """每会话一个整数游标，指向当前展示节点（advance 提交后才移动）。"""

    def __init__(self, scenes: list[dict] | None = None) -> None:
        self._scenes = list(scenes if scenes is not None else SCENES)
        self._nodes: list[StoryLine | StoryChoice] = []
        self._cursors: dict[str, int] = {}
        self._scene_titles: dict[str, str] = {}
        self._build()

    # ---- 内容载入与校验（fail closed） ------------------------------------

    def _build(self) -> None:
        if not self._scenes:
            raise StoryContentError("story content is empty")
        seen_scene_ids: set[str] = set()
        seen_choice_ids: set[str] = set()
        for scene in self._scenes:
            if not isinstance(scene, dict):
                raise StoryContentError("scene must be an object")
            scene_id = scene.get("scene_id")
            if not isinstance(scene_id, str) or not scene_id:
                raise StoryContentError("scene_id is required")
            if scene_id in seen_scene_ids:
                raise StoryContentError(f"duplicate scene_id {scene_id!r}")
            seen_scene_ids.add(scene_id)
            title = scene.get("title")
            self._scene_titles[scene_id] = title if isinstance(title, str) else ""
            steps = scene.get("steps")
            if not isinstance(steps, list) or not steps:
                raise StoryContentError(f"[{scene_id}] steps must be a non-empty list")
            for index, step in enumerate(steps):
                self._append_step(scene_id, index, step, seen_choice_ids)
        # 收尾一遍：所有未指定 next 的台词按顺序指向下一个节点（最后一句指向
        # end）；分支末句 / 选项前一句已在 _append_step 内修正过，不在此覆盖。
        for i, node in enumerate(self._nodes):
            if isinstance(node, StoryLine) and node.next_index == -1:
                node.next_index = i + 1
        self._check_scene_presentation(seen_scene_ids)

    def _check_scene_presentation(self, seen_scene_ids: set[str]) -> None:
        """演出配置 fail closed 校验：未知场景 / 未知效果 / 非法光照拒绝启动。"""
        for scene_id, presentation in SCENE_PRESENTATION.items():
            if scene_id not in seen_scene_ids:
                raise StoryContentError(
                    f"SCENE_PRESENTATION references unknown scene {scene_id!r}"
                )
            if not isinstance(presentation, dict):
                raise StoryContentError(
                    f"SCENE_PRESENTATION[{scene_id!r}] must be an object"
                )
            effects = presentation.get("effects", [])
            if not isinstance(effects, list) or any(
                e not in KNOWN_STORY_EFFECTS for e in effects
            ):
                raise StoryContentError(
                    f"SCENE_PRESENTATION[{scene_id!r}] has unknown effects"
                )
            lighting = presentation.get("lighting")
            if lighting is not None and not isinstance(lighting, dict):
                raise StoryContentError(
                    f"SCENE_PRESENTATION[{scene_id!r}] lighting must be an object"
                )

    def _append_step(
        self, scene_id: str, index: int, step, seen_choice_ids: set[str]
    ) -> None:
        def fail(message: str) -> None:
            raise StoryContentError(f"[{scene_id} step:{index}] {message}")

        if not isinstance(step, dict):
            fail("step must be an object")
        if "choice" in step:
            choice_id = step.get("choice")
            if not isinstance(choice_id, str) or not choice_id:
                fail("choice id is required")
            if choice_id in seen_choice_ids:
                fail(f"duplicate choice id {choice_id!r}")
            seen_choice_ids.add(choice_id)
            options = step.get("options")
            if not isinstance(options, list) or not options:
                fail("choice options must be a non-empty list")
            # 选项前的最后一句台词（若有）需要把 next 指到选项节点；必须在
            # 追加分支台词之前记录，否则会误把分支末句当成「选项前一句」。
            pre_line_index: int | None = None
            if self._nodes and isinstance(self._nodes[-1], StoryLine):
                pre_line_index = len(self._nodes) - 1
            parsed: list[tuple[str, str]] = []
            first_index_by_option: dict[str, int] = {}
            branch_last_indices: list[int] = []
            for option in options:
                if not isinstance(option, dict):
                    fail("option must be an object")
                option_id = option.get("id")
                label = option.get("label")
                lines = option.get("lines")
                if not isinstance(option_id, str) or not option_id:
                    fail("option id is required")
                if any(existing_id == option_id for existing_id, _ in parsed):
                    fail(f"duplicate option id {option_id!r}")
                if not isinstance(label, str) or not label:
                    fail("option label is required")
                if not isinstance(lines, list) or not lines:
                    fail("option lines must be a non-empty list")
                parsed.append((option_id, label))
                first_index_by_option[option_id] = len(self._nodes)
                for line_index, line in enumerate(lines):
                    if not isinstance(line, dict) or "choice" in line:
                        fail(f"nested choice is not allowed (option {option_id!r})")
                    self._append_line(scene_id, line, f"{index}.{line_index}", fail)
                branch_last_indices.append(len(self._nodes) - 1)
            # 选项节点追加在分支台词之后（index = choice_index）；分支末句的
            # next 跳过选项节点，直指「选项后合并主线」的第一个节点。
            choice_index = len(self._nodes)
            for last_index in branch_last_indices:
                self._nodes[last_index].next_index = choice_index + 1
            # 选项节点前的最后一句台词，next 指向选项节点。
            if pre_line_index is not None:
                self._nodes[pre_line_index].next_index = choice_index
            self._nodes.append(
                StoryChoice(
                    choice_id=choice_id,
                    scene_id=scene_id,
                    options=tuple(parsed),
                    first_index_by_option=first_index_by_option,
                )
            )
            return
        self._append_line(scene_id, step, str(index), fail)

    def _append_line(self, scene_id: str, step, where: str, fail) -> None:
        speaker = step.get("speaker")
        text = step.get("text")
        emotion = step.get("emotion", "neutral")
        if not isinstance(speaker, str) or speaker not in _SPEAKERS:
            fail(f"unknown speaker {speaker!r} (line {where})")
        if not isinstance(text, str) or not text.strip():
            fail(f"text is required (line {where})")
        if emotion not in ALLOWED_EMOTIONS:
            fail(f"unknown emotion {emotion!r} (line {where})")
        self._nodes.append(
            StoryLine(speaker=speaker, text=text, emotion=emotion, scene_id=scene_id)
        )

    # ---- 游标语义 ---------------------------------------------------------

    @property
    def total_nodes(self) -> int:
        return len(self._nodes)

    def started(self, session_id: str) -> bool:
        return session_id in self._cursors

    def finished(self, session_id: str) -> bool:
        return self.started(session_id) and self._cursors[session_id] >= len(self._nodes)

    def current(self, session_id: str) -> dict:
        """当前展示节点（读操作，不移动游标）。未开始则抛 KeyError。"""
        return self._view(session_id, self._cursors[session_id])

    def advance(self, session_id: str) -> tuple[dict, bool]:
        """移动到下一节点并返回 (view, scene_changed)。

        未开始的会话从第一个节点开始（首次 advance 即「开始游戏」）。当前
        节点是选项时 advance 不合法（必须先 choose，fail closed）。
        """
        previous = self._cursors.get(session_id, -1)
        if previous >= 0 and previous < len(self._nodes):
            node = self._nodes[previous]
            if isinstance(node, StoryChoice):
                raise ValueError("must choose an option before advancing")
            index = node.next_index
        else:
            index = 0 if previous < 0 else previous + 1
        self._cursors[session_id] = index
        view = self._view(session_id, index)
        scene_changed = (
            index >= len(self._nodes)
            or previous < 0
            or (
                self._nodes[index].scene_id
                != self._nodes[previous].scene_id
                if previous < len(self._nodes) and previous >= 0
                else True
            )
        )
        return view, scene_changed

    def choose(self, session_id: str, option_id: str) -> dict:
        """提交一个选项：游标跳到该选项的第一句台词并返回它。"""
        if not self.started(session_id):
            raise ValueError("story has not started")
        index = self._cursors[session_id]
        node = self._nodes[index] if index < len(self._nodes) else None
        if not isinstance(node, StoryChoice):
            raise ValueError("current node is not a choice")
        target = node.first_index_by_option.get(option_id)
        if target is None:
            raise ValueError(f"unknown option {option_id!r}")
        self._cursors[session_id] = target
        return self._view(session_id, target)

    def _view(self, session_id: str, index: int) -> dict:
        if index >= len(self._nodes):
            return {"kind": "end", "scene_id": None}
        node = self._nodes[index]
        if isinstance(node, StoryChoice):
            return {
                "kind": "choice",
                "choice_id": node.choice_id,
                "scene_id": node.scene_id,
                "options": [{"id": option_id, "label": label} for option_id, label in node.options],
            }
        return {
            "kind": "line",
            "speaker": node.speaker,
            "text": node.text,
            "emotion": node.emotion,
            "scene_id": node.scene_id,
        }

    def scene_info(self, scene_id: str | None) -> dict | None:
        """场景标题与演出指令（纯表现数据，不含剧情文字；未知场景返回 None）。"""
        if scene_id is None or scene_id not in self._scene_titles:
            return None
        return {
            "scene_id": scene_id,
            "title": self._scene_titles[scene_id],
            "presentation": SCENE_PRESENTATION.get(scene_id) or {},
        }

    # ---- 持久化 -----------------------------------------------------------

    def snapshot(self, session_id: str) -> dict | None:
        if not self.started(session_id):
            return None
        return {"node_index": self._cursors[session_id]}

    def restore(self, session_id: str, data: dict | None) -> None:
        if data is None:
            self._cursors.pop(session_id, None)
            return
        if not isinstance(data, dict) or not isinstance(data.get("node_index"), int):
            raise StoryContentError("invalid story cursor snapshot")
        self._cursors[session_id] = data["node_index"]
