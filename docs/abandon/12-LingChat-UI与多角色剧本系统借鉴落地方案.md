# 12 — LingChat UI 与多角色剧本系统借鉴落地方案

> **文档状态：** Active  
> **适用阶段：** 第一章调查主线可玩化 / Gal 表现层升级  
> **文档职责：** 指导当前项目借鉴 LingChat 的 Gal UI、多角色舞台与数据驱动剧本机制，并将其重新实现到现有 Next.js + FastAPI 架构中。  
> **不负责：** 重写第一章剧情内容、重新定义 Evidence / Claim / Contradiction / Inference、实现 Recovery 小游戏、开发可视化剧本编辑器、复制 LingChat 源码或素材。

---

# 1. Agent 读取规则

本文件是：

**LingChat 借鉴落地阶段的开发指导文档。**

Agent 执行本阶段任务时必须同时遵守：

1. `01 — MVP Requirements.md`
2. `02 — System Architecture.md`
3. `04 — Character Runtime.md`
4. `05 — Memory Design.md`
5. `10 — 第一章调查内容配置.md`
6. `11 — 第一章调查主线落地说明.md`

优先级：

```text
现有项目真相源
>
本文件
>
LingChat 的实现方式
```

LingChat 仅作为：

```text
UI交互参考
+
多角色舞台参考
+
剧本数据模型参考
```

不得因为 LingChat 已经存在某种实现，就改变当前项目已经冻结的核心架构边界。

---

# 2. 本阶段目标

本阶段目标不是“把 LingChat 搬进来”。

目标是：

> **吸收 LingChat 已验证的 Gal 表现层和多角色剧本组织方式，独立实现一套适合当前 AI Galgame 的 Presentation Runtime + Script Content Layer。**

最终应解决三个当前问题：

```text
① 多角色同时出现在同一场景时，立绘位置、表情、显示隐藏和动画缺少统一管理。

② 固定剧情节点、AI自由对话、调查解锁、角色登场目前容易散落在代码中。

③ 第一章越来越复杂，需要把“剧情内容配置”与“运行时逻辑”进一步分开。
```

本阶段完成后，应得到：

```text
GameStage
+
统一角色舞台
+
统一 Presentation Action
+
轻量 Script DSL
+
第一章 Script Content
+
Narrative Runtime Gate
```

并让以下链路可以被数据驱动地表现：

```text
03:17事件
↓
环境异常
↓
Claude出现
↓
固定台词
↓
Player自然语言调查
↓
AI角色回应
↓
Evidence / Claim / Gate推进
↓
后续角色登场
```

---

# 3. 明确不做什么

本阶段禁止扩张为完整 Galgame Engine。

暂不实现：

```text
可视化剧本编辑器
节点拖拽编辑器
通用分支树编辑器
复杂 Timeline
角色骨骼动画
Live2D
完整语音系统
复杂摄像机系统
插件系统
独立剧本 IDE
```

尤其不要因为 LingChat 已经存在 Script Editor，就在当前阶段复制其编辑器能力。

当前最重要的是：

> **先让第一章调查主线稳定可玩。**

---

# 4. 借鉴原则

## 4.1 可以借鉴

可以借鉴 LingChat 的：

- 画面分层思想；
- 多角色统一舞台；
- 根据在场人数自动分配角色位置；
- 角色独立 offset / scale；
- 表情变化时切换立绘；
- 角色淡入淡出；
- 剧本使用结构化事件而不是散落硬编码；
- 剧本文件与角色配置分离；
- 事件类型有限且可校验；
- 固定台词与 AI 对话并存；
- 通过数据控制角色 show / hide / emotion；
- Script Content 与 Runtime 分层。

## 4.2 不直接复制

不得直接复制：

- LingChat Vue 组件源码；
- CSS / Tailwind 片段的大段逐行改写；
- Rust / Tauri Script Runtime；
- LingChat 的角色 Prompt；
- 剧情对白；
- 角色卡；
- 图片；
- 音乐；
- 音效；
- 字体；
- 其他来源不明确的 bundled asset。

实现方式应采用：

# Clean-room Reimplementation

即：

```text
理解它解决了什么问题
↓
抽象出行为与数据模型
↓
按照当前项目架构重新设计
↓
独立编写代码
```

---

# 5. 为什么不能直接移植 LingChat

LingChat 当前主要技术栈为：

```text
Vue 3
Pinia
TailwindCSS
Vite
Tauri 2
Rust
```

当前项目冻结技术栈为：

```text
Frontend:
Next.js + React + TypeScript

Backend:
FastAPI + Python + Pydantic

Persistence:
PostgreSQL
```

两者运行边界不同。

因此不要做：

```text
LingChat Vue Component
↓
机械翻译 React
```

而应做：

```text
LingChat交互行为
↓
提取需求
↓
按当前 React Presentation Layer 重写
```

---

# 6. 目标 Frontend 结构

当前 `02 — System Architecture` 已定义 Frontend 是：

# Game Presentation Layer

本阶段将其进一步整理为：

```text
GameStage
│
├── BackgroundLayer
│
├── CharacterStage
│   ├── CharacterSprite
│   ├── CharacterSprite
│   └── CharacterSprite
│
├── EffectLayer
│
├── InteractionLayer
│   └── Hotspots
│
└── UILayer
    ├── DialoguePanel
    ├── PlayerInput
    ├── EvidencePanel
    ├── InvestigationUI
    └── History
```

职责必须明确。

---

# 7. GameStage

`GameStage` 是整个游戏画面的容器。

它只接受经过 Backend / Game State 确认后的 Presentation State。

逻辑输入可以抽象为：

```ts
interface GamePresentationState {
  scene: ScenePresentation;
  characters: CharacterPresentation[];
  dialogue?: DialoguePresentation;
  effects: PresentationEffect[];
  inputMode: InputMode;
}
```

具体字段名允许根据现有代码调整。

关键原则：

> Frontend 不计算“谁应该出现”。

Frontend只负责：

> “Backend告诉我谁当前在场，我就如何表现。”

---

# 8. BackgroundLayer

负责：

```text
背景图片
背景淡入淡出
基础明暗变化
Glitch覆盖层
场景切换
```

当前阶段只需要有限能力。

建议 Action：

```text
SET_BACKGROUND
FADE_BACKGROUND
SCENE_GLITCH
```

禁止让 LLM 返回任意 CSS 或 DOM 操作。

---

# 9. CharacterStage

这是本阶段最值得借鉴 LingChat 的部分。

CharacterStage 统一管理所有当前可见角色。

建议状态结构：

```ts
interface CharacterPresentation {
  characterId: CharacterId;
  visible: boolean;
  emotion: string;
  spriteKey: string;
  scale?: number;
  offsetX?: number;
  offsetY?: number;
  slot?: CharacterSlot;
  animation?: CharacterAnimation;
}
```

Frontend不得读取 Persona、Memory、Knowledge 决定表现。

这些属于 Backend / Character Runtime。

---

# 10. 多角色自动站位

LingChat 的一个可借鉴思路是：

> 根据当前在场角色数量和角色序号，自动把角色均匀分布在舞台横向位置。

当前项目可独立实现更简单的版本。

基础算法：

```text
position(i, n) = (i + 1) / (n + 1)
```

例如：

```text
1人：
50%

2人：
33% / 67%

3人：
25% / 50% / 75%

4人：
20% / 40% / 60% / 80%
```

然后允许：

```text
offsetX
offsetY
scale
```

进行角色级微调。

## 10.1 自动布局只负责默认值

如果 Script 明确指定：

```text
LEFT
CENTER_LEFT
CENTER
CENTER_RIGHT
RIGHT
```

则优先使用明确 Slot。

优先级：

```text
explicit slot
>
manual offset
>
auto layout
```

## 10.2 当前阶段不要做复杂碰撞布局

不需要：

- 自动检测人物身体宽度；
- AI 自动构图；
- 运行时视觉识别；
- 动态人物避让算法。

第一章角色数量最多有限，手工配置足够。

---

# 11. CharacterSprite

每个角色独立组件负责：

```text
立绘
表情差分
淡入淡出
位置
缩放
角色动画
```

最小动画集合继续遵守现有架构“Named Animation Actions”的原则。

推荐：

```text
fade_in
fade_out
shake
small_jump
slide_in_left
slide_in_right
none
```

不要允许 Script 写：

```text
animation: "translateX(17px) rotate(...) ..."
```

只能使用预定义枚举。

---

# 12. DialoguePanel

LingChat 的对话框功能较复杂，但当前项目只借鉴它的布局职责，不复制完整功能。

本阶段 DialoguePanel 只需要稳定支持：

```text
Character Name
Dialogue Text
逐字显示
继续提示
Loading状态
错误状态
History入口
```

Player自由输入继续保持独立的 `PlayerInput`。

不要把核心流程改成固定选项点击。

因为 `01 — MVP Requirements` 已明确：

> Player 自然语言输入是当前核心输入方式。

---

# 13. Presentation Action

为避免 Backend 直接传 CSS / DOM 指令，本阶段建立有限的 Presentation Action。

建议：

```text
CHARACTER_SHOW
CHARACTER_HIDE
CHARACTER_EMOTION
CHARACTER_ANIMATION
BACKGROUND_SET
BACKGROUND_FADE
SCREEN_SHAKE
SCREEN_GLITCH
DIALOGUE_FOCUS
INPUT_LOCK
INPUT_UNLOCK
```

示例：

```json
{
  "type": "CHARACTER_SHOW",
  "character_id": "claude",
  "emotion": "serious",
  "slot": "RIGHT",
  "animation": "fade_in"
}
```

Frontend只执行已注册 Action。

任何未知 Action：

```text
拒绝执行
+
记录日志
+
不得影响 Game State
```

---

# 14. Script DSL 的定位

本项目需要的 Script DSL 不是完整剧情引擎。

它只解决：

> **确定性内容如何被配置，而不是散落在 Python / TypeScript 条件分支中。**

Script DSL 不拥有最终剧情权限。

真正的权威仍是：

# Narrative Runtime

关系必须是：

```text
Script Content
↓
Script Runtime读取
↓
提出“应播放什么 / 应请求谁回应”
↓
Narrative Runtime验证当前是否允许
↓
Game Orchestrator执行
↓
Frontend表现
```

不是：

```text
Script YAML
↓
直接修改Game State
```

---

# 15. Script DSL 第一版事件类型

第一版只实现第一章真正需要的事件。

建议事件集合：

```text
background
character_show
character_hide
character_update
script_dialogue
player_input
ai_dialogue
presentation
narrative_gate
unlock
phase_transition
```

暂时不要实现 `choices`。

---

# 16. background

用于声明确定性背景变化。

示例：

```yaml
- type: background
  background: room_dark
  transition: fade
```

它只能影响 Presentation State。

---

# 17. character_show

示例：

```yaml
- type: character_show
  character: claude
  emotion: serious
  slot: right
  animation: fade_in
```

执行前必须检查：

```text
Character Availability
```

如果 Claude 尚未被 Narrative Runtime 解锁：

```text
不得仅因为Script写了show就让Claude提前出现。
```

---

# 18. character_hide

示例：

```yaml
- type: character_hide
  character: claude
  animation: fade_out
```

只控制当前 Presentation。

不等于：

```text
角色死亡
角色离开剧情
Character Availability = false
```

这些必须由 Narrative State 决定。

---

# 19. character_update

用于改变：

```text
emotion
slot
offset
scale
animation
```

示例：

```yaml
- type: character_update
  character: deepseek
  emotion: surprised
  animation: shake
```

不能在这里修改：

```text
Knowledge
Memory
Relationship
Evidence
Narrative Phase
```

---

# 20. script_dialogue

用于固定台词。

适用于：

- 开场固定句；
- 系统提示；
- 关键剧情句；
- 豆包固定输出；
- 必须确定性出现的角色反应。

推荐不要在章节 YAML 中直接堆大量长对白。

可使用：

```yaml
- type: script_dialogue
  character: claude
  node: CLAUDE_0317_OPENING
```

实际文本放在独立 Script Node Content 中。

这样方便：

- 本地化；
- 文本修改；
- 台词复用；
- 测试 Node ID；
- 避免主流程 YAML 过长。

---

# 21. player_input

表示：

> 当前剧情允许 Player 进行自由自然语言输入。

示例：

```yaml
- type: player_input
  mode: investigation
```

它不是一个“等待玩家输入任意一句后自动进入下一事件”的简单 pause。

Narrative Runtime仍需要判断：

```text
Player本轮输入
↓
Intent / Topic / Evidence Interaction
↓
是否达到剧情推进条件
```

因此：

> Player 没有问到指定问题，也不能导致主线永久卡死。

关键剧情必须通过 Narrative Gate 与可发现交互保证可达。

---

# 22. ai_dialogue

用于请求某个生成式角色进行自由回应。

示例：

```yaml
- type: ai_dialogue
  character: claude
  directive: CLAUDE_PUBLIC_INVESTIGATION
```

实际调用链：

```text
Script Runtime
↓
Game Orchestrator
↓
Narrative Runtime生成最小 narrative_context
↓
Character Runtime
↓
Memory Selection
↓
Provider
↓
Character Response Validation
↓
Narrative Validation
↓
Frontend
```

`ai_dialogue` 不得把 Prompt 全文直接写在第一章 YAML 中。

应传：

```text
directive id
```

由 Character Runtime / Narrative Content 获取正式约束。

---

# 23. presentation

用于播放不改变剧情真相的演出。

示例：

```yaml
- type: presentation
  action: screen_glitch
  intensity: medium
```

第一版允许参数必须使用 schema 白名单。

---

# 24. narrative_gate

这是当前项目与普通 Galgame Script 最大的区别之一。

示例：

```yaml
- type: narrative_gate
  condition: CT01_CONFIRMED
```

Gate 本身不计算条件。

它只是询问 Narrative Runtime：

```text
当前 condition 是否成立？
```

如果 false：

```text
Script不能向后推进受保护事件。
```

---

# 25. unlock

用于执行已经由 Narrative Runtime 判定合法的确定性解锁。

示例：

```yaml
- type: unlock
  target: PRIVATE_INTERVIEW_CLAUDE
```

但必须区分两种情况。

## 25.1 内容声明

Script声明：

```text
当走到这里时，希望解锁 X。
```

## 25.2 真正执行

Narrative Runtime再次验证：

```text
X当前是否满足正式Gate？
```

只有通过后才改变 Game State。

---

# 26. phase_transition

用于章节 / 调查阶段变化。

示例：

```yaml
- type: phase_transition
  to: INVESTIGATION_CLAUDE
```

同样必须由 Narrative Runtime 验证。

---

# 27. 不使用 LingChat 的 choices 作为主流程

LingChat 支持 `choices` 是合理的，因为它需要通用剧本能力。

当前项目不同。

当前已经明确：

```text
Player自由自然语言
=
核心输入
```

因此本阶段：

```text
不建立 A / B / C 固定选项主线
```

如果未来需要：

- Security Review；
- Admin选择；
- DELETE确认；
- 明确系统操作；

可以单独建立：

```text
System Decision UI
```

而不是把普通调查重新改成传统视觉小说选项树。

---

# 28. 建议内容目录

不要直接照搬 LingChat 的目录。

按当前项目重新建立：

```text
content/
│
├── characters/
│   ├── deepseek/
│   ├── claude/
│   ├── chatgpt/
│   └── doubao/
│
├── scenes/
│   └── chapter_01/
│
├── scripts/
│   └── chapter_01/
│       ├── opening.yaml
│       ├── incident_0317.yaml
│       ├── claude_investigation.yaml
│       ├── gpt_arrival.yaml
│       ├── doubao_investigation.yaml
│       └── final_reveal.yaml
│
├── dialogue_nodes/
│   └── chapter_01/
│
└── narrative/
    └── chapter_01/
```

现有项目如果已经存在类似目录，应优先合并到现有结构，不要为了匹配本文件强制重构目录名。

---

# 29. 第一章 03:17 的接入方式

第一章当前主线要求：

```text
03:17事件
↓
Claude出现
↓
EV02 / EV03 / EV04
```

这里需要明确：

> `03:17` 是剧情世界中的确定性事件条件，不应该简单等于“玩家现实等待到电脑本地时间03:17”。

推荐实现为 Narrative Clock / Story Trigger。

例如：

```text
EV01_NOTE_V03 acquired
↓
INCIDENT_0317 eligible = true
↓
满足安全的推进条件
↓
Narrative Runtime触发 INCIDENT_0317
```

安全推进条件应避免依赖玩家必须问出某一句指定问题。

第一版推荐：

```text
EV01获得后
+
至少完成一次后续有效调查/对话交互
↓
触发03:17事件
```

或者由现有 Narrative Runtime 使用固定 `story_tick` / `interaction_count` 推进。

重点不是具体字段，而是保证：

```text
玩家会自然遇到03:17
且
玩家不问“现在几点”也不会卡死
```

---

# 30. 03:17 Script 示例

以下仅作为结构示例，不是最终字段合同：

```yaml
script_id: CH01_INCIDENT_0317

steps:
  - type: narrative_gate
    condition: INCIDENT_0317_READY

  - type: presentation
    action: screen_glitch
    intensity: medium

  - type: script_dialogue
    speaker: system
    node: SYS_0317_WARNING

  - type: presentation
    action: screen_shake

  - type: character_show
    character: claude
    emotion: serious
    slot: right
    animation: fade_in

  - type: script_dialogue
    character: claude
    node: CLAUDE_0317_OPENING

  - type: phase_transition
    to: INVESTIGATION_CLAUDE

  - type: player_input
    mode: investigation
```

注意：

`Claude Availability` 必须先由 Narrative Runtime 合法开启。

不能只靠 `character_show` 创造剧情事实。

---

# 31. 第一章完整映射

建议将 `docs/11` 中的主线映射为以下 Script / Narrative 协作：

```text
03:17事件
→ incident_0317.yaml

Claude出现
→ character_show + Availability Gate

EV02 / EV03 / EV04
→ Hotspot / Investigation Runtime

Claude Claim
→ Character Runtime + Claim Detection

CT01
→ Contradiction Runtime

Claude私审
→ Private Interview Runtime

EV05
→ Narrative Unlock

INF01
→ Inference Runtime

EV06
→ Narrative Unlock + Investigation Content

GPT出现
→ gpt_arrival.yaml

GPT Summary
→ deterministic Evidence creation + Character presentation

豆包出现
→ doubao_arrival / scripted runtime

豆包私审
→ Private Interview Runtime

EV08
→ Narrative Unlock

GPT第二次Summary
→ deterministic Evidence creation

CT04
→ Contradiction Runtime

GPT私审
→ Private Interview Runtime

EV09
→ Narrative Unlock

INF03
→ Inference Runtime

SANDBOX INTEGRITY FAILURE
→ final_reveal.yaml + Presentation Actions

RECOVERY REQUIRED
→ phase_transition
```

---

# 32. Script Runtime 与 Character Runtime 边界

必须保持：

```text
Script Runtime
负责“固定事件与固定内容如何播放”
```

```text
Character Runtime
负责“角色如何回应”
```

例如：

```text
Claude登场第一句
→ script_dialogue
```

玩家追问：

```text
“你怎么知道是DeepSeek开的门？”
→ ai_dialogue
→ Claude Character Runtime
```

玩家获得 Claim：

```text
→ Narrative / Claim Runtime
```

不要把三层混在一起。

---

# 33. Script Runtime 与 Narrative Runtime 边界

这是最重要的验收边界。

Script Runtime不能决定：

```text
Evidence acquired
Claim confirmed
Contradiction confirmed
Inference confirmed
Private Interview unlocked
Character Availability
Narrative Phase
Ground Truth Reveal
```

这些全部属于 Backend 权威状态。

Script Runtime最多产生：

```text
Script Intent
```

例如：

```json
{
  "intent": "unlock",
  "target": "PRIVATE_INTERVIEW_CLAUDE"
}
```

Narrative Runtime校验后才变成：

```text
Game State Change
```

---

# 34. LLM边界

LLM同样不能控制 Script Runtime。

LLM可以建议：

```text
emotion
animation
```

但最终只允许映射到白名单 Presentation Action。

LLM不得返回：

```text
next_script
unlock_evidence
set_phase
show_character
```

并直接生效。

角色生成输出必须继续经过：

```text
Schema Validation
↓
Character Validation
↓
Narrative Validation
↓
Presentation Mapping
```

---

# 35. Memory边界

Script事件不能直接写角色长期 Memory。

例如固定事件：

```text
Claude出现
```

不等于：

```text
DeepSeek automatically remembers Claude appeared
```

Memory写入仍应遵守：

```text
Message Visibility
Character Memory Scope
Memory Write Gate
```

特别是 DeepSeek 的视觉权限限制不能因为新的 CharacterStage 被绕过。

UI看见Claude：

```text
≠
DeepSeek角色上下文自动看见Claude
```

这是必须专门测试的边界。

---

# 36. Schema 与校验

LingChat 的“有限事件类型 + schema 单一真相源”值得借鉴。

当前项目第一版建议由 Backend Pydantic 定义 Script Event Schema。

原因：

```text
Backend本来就是权威
+
FastAPI/Pydantic已有结构化校验能力
```

建议逻辑：

```text
YAML
↓
Python parser
↓
Pydantic Script Event Models
↓
Validation
↓
Runtime
```

Frontend不单独解析 YAML。

Frontend只接收：

```text
JSON Presentation State / Actions
```

这样避免前后端出现两套剧本解释器。

---

# 37. Script加载失败策略

Script属于关键内容。

因此：

```text
Fail Closed
```

发现以下问题时：

- 未知 event type；
- 缺少必填字段；
- character_id 不存在；
- dialogue node 不存在；
- condition 不存在；
- transition target 不存在；
- animation 不在白名单；

不得静默跳过。

开发环境：

```text
明确报错
+
指出script_id
+
step index
+
错误字段
```

生产环境：

```text
阻止非法剧情推进
+
返回可恢复错误
+
记录日志
```

---

# 38. 不做可视化 Script Editor

LingChat 已经做了相当完整的 Script Editor，但当前项目不应跟进。

原因：

```text
第一章内容仍在快速调整
+
当前主要风险是Runtime正确性
+
可视化编辑器不会直接提升核心玩法验证
```

当前流程保持：

```text
开发者 / Agent编辑 YAML
↓
Schema校验
↓
自动测试
↓
游戏运行
```

未来第一章稳定后，如果内容量显著扩大，再单独立项：

```text
Script Authoring Tool
```

---

# 39. 实施顺序

## Task 1 — Presentation State统一

目标：

建立统一的：

```text
Scene Presentation
Character Presentation
Dialogue Presentation
Presentation Action
```

验收：

- Frontend不再从剧情条件自行判断角色显示；
- 所有角色 show/hide 由统一状态控制；
- 未知 Animation Action 不执行。

---

## Task 2 — CharacterStage

目标：

实现多角色舞台。

最低能力：

```text
1～4角色同时显示
自动默认站位
slot覆盖
scale
offsetX
offsetY
emotion切换
fade in/out
shake
```

验收：

- DeepSeek + Claude 同屏正常；
- DeepSeek + Claude + GPT 同屏不严重遮挡；
- 四角色同屏仍有可接受布局；
- 表情切换不导致立绘闪成空白；
- 角色隐藏不残留点击区域。

---

## Task 3 — Script Event Schema

目标：

在 Backend 建立第一版事件模型。

只实现：

```text
background
character_show
character_hide
character_update
script_dialogue
player_input
ai_dialogue
presentation
narrative_gate
unlock
phase_transition
```

验收：

- 合法 YAML 可以加载；
- 未知事件无法启动；
- character / node / condition 引用可校验；
- Frontend无需理解 YAML。

---

## Task 4 — Script Runtime

目标：

按顺序执行确定性 Script Event。

必须支持：

```text
执行到 player_input 后暂停
Narrative Gate false 时暂停
ai_dialogue 请求 Character Runtime
Presentation Event 返回 Frontend
```

验收：

- Script不能直接修改 Evidence；
- Script不能绕过 Character Availability；
- Script不能绕过 Narrative Gate。

---

## Task 5 — 03:17迁移

目标：

把当前 Fixture / POC 型固定节点升级为真实第一章节点。

实现：

```text
EV01之后事件eligible
↓
确定性推进条件
↓
03:17 Glitch
↓
Claude正式出现
↓
调查阶段开启
```

验收：

- 玩家不问“03:17是什么”也能遇到事件；
- 获得纸条后不会立刻无演出地出现Claude；
- Claude只能出现一次；
- Session恢复不会重复触发登场。

---

## Task 6 — 第一章角色登场配置化

依次迁移：

```text
Claude
GPT
豆包
```

角色何时“可用”仍由 Narrative Runtime决定。

Script只负责：

```text
登场演出
固定句
表现层变化
```

---

## Task 7 — 第一章调查主线串联

严格按照 `docs/11`：

```text
Phase A
→
Phase B
→
Phase C
→
...
→
Phase J
```

不得在该任务中开发 Recovery 本体。

---

# 40. 自动测试要求

至少补以下测试。

## 40.1 Script Schema

```text
未知event type → fail
缺character → fail
不存在的dialogue node → fail
未知animation → fail
未知condition → fail
```

## 40.2 Narrative Gate

```text
CT01未确认
→
不能进入Claude私审解锁事件
```

```text
INF01未完成
→
不能获得EV06
```

```text
EV01 / EV06 / EV09不完整
→
INF03不能成立
```

## 40.3 Character Availability

```text
GPT未解锁
+
Script错误写character_show GPT
→
GPT不得出现
```

## 40.4 Memory Isolation

```text
Claude视觉上出现
→
不自动将“我看见Claude出现”写入DeepSeek Memory
```

## 40.5 Resume

在以下状态刷新页面：

```text
Claude刚登场
GPT刚登场
豆包私审完成
INF03前
```

恢复后：

- 角色显示正确；
- Script不重复播放一次性关键事件；
- Evidence不重复创建；
- Narrative Phase不回退。

---

# 41. 第一阶段完整验收场景

最终需要进行一次真实人工 walkthrough。

流程：

```text
New Game
↓
开场
↓
与DeepSeek自由对话
↓
调查纸条
↓
获得EV01
↓
正常继续互动
↓
03:17自动进入eligible后的正式事件
↓
Glitch / Claude出现
↓
调查EV02 / EV03 / EV04
↓
与Claude自由对话
↓
CT01
↓
Claude私审
↓
EV05
↓
INF01
↓
EV06
↓
GPT登场
↓
GPT Summary
↓
豆包登场
↓
豆包调查
↓
GPT第二次Summary
↓
CT04
↓
GPT私审
↓
EV09
↓
INF03
↓
SANDBOX INTEGRITY FAILURE
↓
RECOVERY REQUIRED
```

验收要求：

```text
整个流程可以在不输入任何“开发者预设标准句”的情况下完成。
```

也就是说：

Player的自然语言表达可以不同，Narrative Runtime负责理解和门控。

---

# 42. UI视觉验收标准

本阶段不是最终美术验收，但必须达到“标准 Galgame 可用水平”。

至少满足：

1. 背景完整覆盖游戏区域；
2. 角色脚底视觉基线基本一致；
3. 双角色同屏不出现明显挤压；
4. 三角色同屏仍能区分谁正在说话；
5. 当前说话者可使用轻量视觉强调；
6. 非当前说话者不能被完全遮挡；
7. 对话框不遮住角色面部；
8. Player Input与Dialogue区视觉层级明确；
9. Glitch / Shake不能影响输入组件可用性；
10. 窄屏至少不出现角色完全消失或UI溢出。

---

# 43. 许可证与素材边界

截至本方案编写时检查，LingChat 仓库根许可证为：

```text
GNU Affero General Public License v3.0
AGPL-3.0
```

因此本项目默认策略为：

# 不复制 LingChat 源码

而采用：

```text
行为参考
+
架构借鉴
+
独立实现
```

如果未来确实希望直接修改并使用 LingChat 的源码，应单独进行许可证评估，不要把它当作 MIT / BSD 类宽松许可证处理。

同时：

> 仓库根许可证不等于已经确认仓库内每一张图片、字体、音乐、语音、角色设定文本都拥有可安全再授权的来源链。

因此第三方素材默认：

```text
不复制
```

除非单独确认授权。

本节是工程风险控制说明，不替代正式法律意见。

---

# 44. 本阶段最终交付物

完成本方案后，应产生：

```text
1. React GameStage
2. BackgroundLayer
3. CharacterStage
4. CharacterSprite
5. DialoguePanel整理
6. Presentation Action schema
7. Backend Script Event Pydantic schema
8. Script Runtime最小执行器
9. 第一章 Script YAML
10. 第一章 Script Node Content
11. 03:17正式事件
12. Claude / GPT / 豆包登场事件
13. Script / Narrative边界测试
14. Resume / Persistence测试
```

不包括：

```text
Recovery小游戏
Admin权限小游戏
最终Security Review
Bad End
可视化Script Editor
```

---

# 45. Done Definition

只有同时满足以下条件，本阶段才算完成：

```text
UI：
多角色可以稳定同屏、切换表情、显示隐藏和播放有限动画。

Content：
第一章确定性剧情节点已从散落硬编码迁移为结构化Script Content。

AI：
自由对话继续通过Character Runtime，不被Script固定对白替代。

Narrative：
Evidence / Claim / Contradiction / Inference / Availability仍由Backend权威控制。

Memory：
没有因为多角色UI或Script事件造成Cross-character Memory Leakage。

Gameplay：
玩家不需要输入指定标准句，也能从EV01正常走到RECOVERY REQUIRED。

Architecture：
Frontend仍然只是Presentation Layer；LLM仍然是不可信生成组件；Script也不能绕过Narrative Runtime。
```

---

# 46. 给 Agent 的一句话任务定义

> **参考 LingChat 的多角色舞台和数据驱动剧本思想，在不复制其源码、不改变现有 Next.js + FastAPI 架构、不削弱 Narrative Runtime 权威的前提下，独立实现 CharacterStage + 有限 Presentation Actions + 最小 Script DSL，并用它把第一章从 03:17 事件一路接到 `RECOVERY REQUIRED`；不要开发 Recovery 本体和可视化剧本编辑器。**
