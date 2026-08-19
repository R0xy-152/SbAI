# 13 — LingChat 前端源码迁移、开始界面与存档系统落地方案

> **文档状态：** Active  
> **版本：** v1.0  
> **日期：** 2026-08-19  
> **适用阶段：** 第一章可玩化后的前端表现层重构 / 正式 Galgame 外壳补全  
> **文档职责：** 定义如何直接复用并修改 LingChat 的 Vue Gal 表现层源码，将现有前端从 React / Next.js 迁移为 Vue 3，并接入当前 FastAPI / PostgreSQL / Game Orchestrator；同时实现 Title Screen、Continue、Load、Manual Save、Auto Save。  
> **不负责：** 重写第一章剧情真相、重新设计 Evidence / Claim / Contradiction / Inference、替换 Character Runtime、替换 Memory 语义、引入 Tauri / Rust 后端、实现 Recovery 小游戏本体、复制 LingChat 剧情或角色素材。

---

# 0. 决策摘要

本文件确认以下技术决策，Agent 不得再次自行改回：

```text
1. 前端正式从 Next.js / React 迁移到 Vue 3 + Vite。
2. 旧 React 前端先冻结保留，Vue 核心链路验收通过后再删除。
3. 允许直接复制并修改 LingChat 的白名单 UI 源码。
4. 不迁移 LingChat 的 Tauri / Rust / AI Runtime / DB / Script Authority。
5. 开始界面 MVP：开始游戏 / 继续游戏 / 读取存档 / 设置。
6. 存档：1 个自动存档 + 6 个手动存档位。
7. 无账号系统；浏览器生成匿名 player_id，存档保存在 PostgreSQL。
8. 整个项目代码仓库按 AGPL-3.0 开源，并保留 LingChat 归属说明。
9. LingChat 图片 / 音乐 / 字体 / 角色 Prompt / 剧情文本不因代码 AGPL 自动视为可复用素材。
10. Backend 仍是唯一 Game Truth Authority；Vue 只是 Presentation Layer。
```

---

# 1. Agent 读取规则

执行本文件前，必须同时读取：

1. `01 — MVP Requirements.md`
2. `02 — System Architecture.md`
3. `04 — Character Runtime.md`
4. `05 — Memory Design.md`
5. `10 — 第一章调查内容配置.md`
6. `11 — 第一章调查主线落地说明.md`
7. `12 — LingChat UI 与多角色剧本系统借鉴落地方案.md`

## 1.1 优先级

本阶段优先级调整为：

```text
01 / 04 / 05 / 10 / 11 的业务与运行时边界
>
本文件的前端迁移与存档决策
>
02 中旧的 Next.js / React 技术选型
>
12 中“不得复制 LingChat 源码”的旧限制
>
LingChat 自身的 Runtime / Backend 设计
```

本文件**只覆盖** `02` 和 `12` 的以下部分：

- `02` 中 Frontend 技术栈 `Next.js + React + TypeScript`；
- `12` 中 Clean-room only / 不得直接复制 LingChat Vue 组件源码；
- `12` 中“按 React Presentation Layer 重写”的迁移策略。

本文件**不覆盖**：

- Backend authoritative；
- LLM 不直接写 Game State；
- Narrative Runtime / Character Runtime / Memory 的职责边界；
- 第一章调查解锁顺序；
- 角色知识与 Memory 隔离。

## 1.2 首个文档同步动作

开始编码前，Agent 应先同步修改 `02 — System Architecture.md` 的 Frontend 技术路线，使其变为：

```text
Frontend:
Vue 3
Vite
TypeScript
Pinia
TailwindCSS
```

总体架构仍然保持：

```text
Browser
↓ HTTP / Streaming
FastAPI
↓
Game Orchestrator
├─ Narrative Runtime
├─ Character Runtime
├─ Memory
└─ State / Session
↓
PostgreSQL
```

禁止因为前端迁移而把 Game Truth 搬回浏览器。

---

# 2. 为什么现在允许直接复用 LingChat 源码

上一阶段采用 Clean-room Reimplementation，目标是降低许可证与技术耦合风险。

实际落地后出现新的工程事实：

> 当前 React 版虽然能够实现相似功能，但视觉表现、角色舞台细节、动效与整体 Gal 感仍未达到 LingChat 参考效果。

因此，本阶段目标从：

```text
“借鉴 LingChat 的设计思想”
```

调整为：

```text
“在接受 AGPL-3.0 开源义务的前提下，直接复用其已验证的 Vue Presentation 源码，并把 Tauri / LingChat Runtime 依赖替换为本项目 Adapter。”
```

这不是整体 Fork LingChat。

最终仍然是：

```text
LingChat-derived Vue Presentation
            ↓
      Project Adapter Layer
            ↓
     Existing FastAPI Backend
            ↓
      Existing Game Runtime
```

---

# 3. LingChat 参考基线

本文件基于 2026-08-19 检查到的 LingChat `main` 分支结构制定。

仓库：

```text
SlimeBoyOwO/LingChat
```

当前前端核心依赖包括：

```text
Vue 3
Pinia
TailwindCSS
Vite
Tauri 2
```

可确认的 Gal 表现层目录：

```text
src/components/game/standard/
├── GameBackground.vue
├── GameDialog.vue
├── GameExtraUI.vue
├── GameRoleAvatar.vue
├── GameRolesStage.vue
├── TouchAreas.vue
├── avatar-animation.css
├── animations/
├── particles/
└── extra/
```

开始界面相关：

```text
src/components/views/MainMenu.vue
src/components/views/menu/
```

LingChat 自身还存在：

```text
Tauri invoke(...)
Rust backend
SeaORM
save_repo.rs
Script Runtime
AI Service
```

这些不是本项目迁移目标。

---

# 4. 许可证与源码使用规则

## 4.1 项目许可证

本项目代码仓库统一采用：

```text
AGPL-3.0
```

仓库至少应包含：

```text
/LICENSE
/NOTICE.md
/THIRD_PARTY_LICENSES.md
```

## 4.2 NOTICE 最低要求

`NOTICE.md` 至少说明：

```text
本项目包含基于 LingChat 修改的部分代码。

Original project:
SlimeBoyOwO/LingChat

License:
GNU Affero General Public License v3.0

本项目对相关源码进行了适配、删减与修改，主要用于 Web Galgame Presentation Layer。
```

## 4.3 复制源码时的要求

直接复制 LingChat 源文件时：

- 不删除已有 copyright / license header；
- 若原文件没有 header，可在修改后的文件顶部增加简短 `Adapted from LingChat` 注释；
- 不伪装为完全原创代码；
- 记录原文件路径与本项目目标路径；
- 后续修改仍提交到公开源码仓库。

## 4.4 素材不是自动白名单

即使仓库代码使用 AGPL，也不能因此默认以下素材均可自由再发布：

```text
角色立绘
背景图
音乐
音效
字体
Logo
角色 Prompt
剧情文本
第三方模型文件
```

本项目默认：

> **只复用明确白名单的代码；游戏素材继续使用本项目自己的资源。**

若某素材未来需要复用，必须单独确认其来源和许可。

---

# 5. 迁移范围

## 5.1 允许直接复用的白名单

第一批只允许迁移：

```text
GameBackground.vue
GameDialog.vue
GameExtraUI.vue
GameRoleAvatar.vue
GameRolesStage.vue
avatar-animation.css
animations/ 中实际被上述组件依赖的文件
particles/ 中实际被场景使用的文件
MainMenu.vue
views/menu/ 中 MainMenu 必需的基础组件
```

按依赖最小化原则迁移。

如果某文件只是被 LingChat 的：

```text
Pet Mode
Pomodoro
Workshop
Script Editor
Schedule
LAN Sync
Resource Sync
```

使用，则不要迁移。

## 5.2 默认不迁移

```text
TouchAreas.vue
```

当前第一章没有身体触摸玩法，不要为了“源码完整”带入无关功能。

后续确有需求再单独评估。

## 5.3 严禁迁移

```text
src-tauri/
LingChat Rust Backend
LingChat SeaORM DB
LingChat AI Service
LingChat Memory Runtime
LingChat Script Runtime authority
LingChat Script Editor
LingChat SaveRepo backend
LingChat 角色剧情
LingChat 角色 Persona / Prompt
```

---

# 6. 目标前端架构

迁移完成后的前端定位仍然是：

# Game Presentation Layer

推荐结构：

```text
frontend-vue/
├── src/
│   ├── app/
│   │   ├── router/
│   │   └── bootstrap/
│   │
│   ├── api/
│   │   ├── game.ts
│   │   ├── saves.ts
│   │   └── assets.ts
│   │
│   ├── adapters/
│   │   ├── presentation-adapter.ts
│   │   ├── asset-resolver.ts
│   │   └── lingchat-compat.ts
│   │
│   ├── stores/
│   │   ├── game.ts
│   │   ├── presentation.ts
│   │   ├── saves.ts
│   │   ├── settings.ts
│   │   └── ui.ts
│   │
│   ├── components/
│   │   ├── game/
│   │   │   └── standard/
│   │   ├── title/
│   │   ├── save/
│   │   └── system/
│   │
│   ├── views/
│   │   ├── TitleView.vue
│   │   ├── GameView.vue
│   │   ├── LoadView.vue
│   │   └── SettingsView.vue
│   │
│   ├── types/
│   └── assets/
│
└── package.json
```

具体目录名可按现有仓库调整，但职责必须保留。

---

# 7. 旧 React 前端处理策略

## 7.1 第一阶段：冻结，不删除

迁移开始时：

```text
existing React / Next frontend
状态 = frozen
```

规则：

- 不再新增 UI 功能；
- 不再继续针对 LingChat 做视觉仿写；
- 只允许修复阻塞当前运行的 P0 bug；
- 不删除；
- 保持当前可运行 commit 可回退。

## 7.2 Vue 验收前禁止删除 React

只有当 Vue 完成以下链路：

```text
Title
↓
New Game
↓
Opening
↓
Player Input
↓
FastAPI
↓
Character Response
↓
角色显示 / 表情 / 动画
↓
03:17 Narrative Event
↓
Claude 出现
↓
Save
↓
Reload Browser
↓
Load
↓
状态正确恢复
```

才允许进入 React 删除阶段。

## 7.3 回滚条件

以下任一成立时，禁止删除 React：

- Vue 无法稳定连接现有 backend；
- 角色知识隔离出现回归；
- Session restore 失效；
- 第一章主线无法正常推进；
- Load Save 后 Evidence / Memory / Narrative State 不一致；
- Vue 视觉表现仍没有明显优于当前 React。

---

# 8. Tauri 去依赖策略

这是源码迁移最重要的技术工作。

LingChat Vue 组件中可能存在：

```ts
invoke(...)
convertFileSrc(...)
@tauri-apps/api/*
```

本项目 Web 版本必须全部去除。

## 8.1 总体替换

```text
LingChat:
Vue → Tauri IPC → Rust

本项目:
Vue → HTTP / Streaming → FastAPI
```

## 8.2 API 调用替换

原逻辑：

```ts
invoke('load_save', { saveId })
```

目标逻辑：

```ts
saveApi.load(saveId)
```

`saveApi` 内部再调用 FastAPI。

禁止在 UI 组件里散落：

```ts
fetch('/api/...')
```

必须通过 `src/api/` 或 Adapter 层统一封装。

## 8.3 本地文件路径替换

LingChat 可能通过：

```ts
invoke('get_avatar_file')
convertFileSrc(path)
```

解析本地角色图片。

本项目改为：

```text
character_id
+
emotion
↓
assetResolver
↓
HTTP/static asset URL
```

例如：

```text
/characters/claude/serious.png
```

或者现有 asset endpoint。

Frontend 不访问宿主机绝对路径。

## 8.4 Tauri-only 能力

以下能力如果只为桌面端存在，直接删除：

```text
打开系统文件夹
本地文件选择器专属逻辑
桌面更新器
桌面通知
原生窗口控制
Tauri plugin API
```

不要为兼容 LingChat 而在 Web 游戏中重新实现无用能力。

---

# 9. Presentation Store 数据模型

不要让 LingChat 原 Store 成为新的 Game Truth。

Vue Store 只保存“当前应如何展示”。

推荐 Presentation State：

```ts
interface PresentationState {
  scene: {
    backgroundId: string | null
    lighting?: SceneLighting
  }

  characters: Record<string, PresentedCharacter>
  presentCharacterIds: string[]

  dialogue: {
    speakerId: string | null
    speakerName: string | null
    text: string
    mode: 'script' | 'ai' | 'system'
  }

  status: 'idle' | 'thinking' | 'streaming' | 'transitioning'

  effects: PresentationEffect[]
}
```

角色表现模型：

```ts
interface PresentedCharacter {
  characterId: string
  visible: boolean
  emotion: string
  scale: number
  offsetX: number
  offsetY: number
  animation?: string | null
}
```

## 9.1 自动站位

可直接保留 LingChat 已验证的自动站位思想：

```text
position = ((index + 1) / (count + 1)) * 100%
```

再叠加：

```text
offsetX
offsetY
scale
```

但最终角色位置仍应可以由 backend Presentation Directive 覆盖。

## 9.2 禁止 Store 做剧情判断

错误：

```ts
if (evidence.includes('EV05')) {
  claude.visible = true
}
```

正确：

```text
Narrative Runtime
↓
produces presentation directive
↓
Presentation Adapter
↓
Store
↓
Claude visible
```

---

# 10. Backend → Vue 的 Presentation Contract

本阶段不要求为了 Vue 重写 Game Orchestrator。

优先复用现有 backend response，并通过 Adapter 归一。

逻辑上至少需要表达：

```text
current scene
current speaker
text / stream
present characters
character emotion
show / hide
animation
background change
basic effect
player input availability
```

建议 Vue 内部统一转换为：

```ts
interface GameViewState {
  sessionId: string
  presentation: PresentationState
  interaction: {
    canInput: boolean
  }
}
```

若 backend 当前字段名不同：

> 在 Adapter 转换，不要为了 UI 组件强迫 backend 全量改名。

---

# 11. LingChat UI 迁移原则

## 11.1 目标是“保留视觉行为”，不是“保留所有产品功能”

对于迁入组件：

```text
保留：
布局
层级
动画
角色淡入淡出
立绘切换
多角色自动站位
光照叠层
对话框视觉结构
必要粒子效果

删除：
LingChat产品专属按钮
宠物模式
Workshop入口
Script Editor入口
无关音频控制
Tauri-only功能
```

## 11.2 GameRoleAvatar

重点保留：

```text
自动站位
scale / offset
窄屏与宽屏补偿
emotion → avatar
image cross-fade
animation class
lighting filter
```

重点替换：

```text
useGameStore 数据来源
useUIStore 数据来源
invoke('get_avatar_file')
convertFileSrc
LingChat emotion vocab
```

本项目必须建立自己的：

```text
characterId + emotion → asset URL
```

## 11.3 GameRolesStage

保留：

```text
遍历在场角色
统一舞台
lighting overlay
层级结构
```

音频如果当前项目尚无完整语音系统：

> 可以先移除或降级，不得让语音阻塞 UI 迁移。

## 11.4 GameDialog

`GameDialog.vue` 功能较重。

第一轮迁移只保留：

```text
speaker name
text area
typing / streaming display
player input
send
auto / history / settings 的必要入口
loading / thinking state
```

暂时删除或隐藏：

```text
Screenshot
Mic
LingChat 专属交互
与当前项目无关的控制项
```

## 11.5 MainMenu

MainMenu 可以复用：

```text
背景层
粒子层
人物层
视差
菜单切换 transition
Logo / title 区域
```

但原 LingChat 菜单项必须重构。

最终只显示：

```text
开始游戏
继续游戏
读取存档
设置
```

不出现：

```text
Game Mode
Script Mode
Workshop
Script Editor
```

MainMenu 原有角色图片（例如项目专属人物素材）必须替换为本项目自己的 Title Art / Character Art。

---

# 12. Title Screen 产品行为

## 12.1 页面结构

```text
TitleView
│
├── Background
├── Decorative Effects
├── Optional Character Art
├── Game Logo / Title
└── Menu
    ├── New Game
    ├── Continue
    ├── Load
    └── Settings
```

## 12.2 New Game

点击：

```text
开始游戏
```

执行：

```text
POST create game session
↓
获得 session_id
↓
初始化 Opening
↓
进入 GameView
```

如果本浏览器已有旧存档：

- 不删除旧存档；
- 可以直接创建新 Session；
- 不需要首版实现复杂确认弹窗，除非会覆盖唯一自动存档。

## 12.3 Continue

Continue 定义为：

> **加载该匿名 player_id 最近更新的有效存档。**

优先级：

```text
最新更新时间
```

不强制优先 Auto Save 或 Manual Save。

如果没有任何存档：

```text
Continue disabled
```

或者点击后明确提示：

```text
暂无可继续的存档
```

不得创建空 Session 冒充 Continue。

## 12.4 Load

进入存档选择界面。

显示：

```text
Auto Save
Slot 1
Slot 2
Slot 3
Slot 4
Slot 5
Slot 6
```

每个已占用 Slot 至少显示：

```text
存档标题
章节 / 阶段
保存时间
```

首版 Screenshot Thumbnail 为可选，不是阻塞项。

## 12.5 Settings

首版至少允许：

```text
文字速度
BGM音量（若已有）
音效音量（若已有）
```

如果音频系统尚未正式接入：

> Settings 可以先只有文字速度与基础显示选项，不要为了菜单完整而扩张范围。

---

# 13. 游戏内系统菜单

游戏内提供一个轻量系统菜单。

首版：

```text
保存
读取
历史
设置
返回标题
```

系统菜单属于 UI，不得影响 Narrative State，除非调用明确的 Save / Load 行为。

## 13.1 保存

打开 6 个手动 Slot。

## 13.2 读取

允许读 Auto + 6 Manual。

## 13.3 历史

展示当前 Session 合法的已显示对话 History。

History ≠ Character Memory。

不要把所有 Memory 内容显示给 Player。

## 13.4 返回标题

返回 Title Screen 不自动删除 Session。

是否自动保存：

- 如果当前位置刚好是合法 Auto Save Checkpoint，可正常触发 Auto Save；
- 不要因为点击“返回标题”就在任意 LLM 中间状态强制 snapshot。

---

# 14. 存档系统核心原则

本项目的 Save 不是简单保存前端画面。

必须恢复：

```text
Narrative State
Script / deterministic runtime cursor
Game State
Character State
Character Knowledge progression reference
Character Memory
Message History
Evidence
Claim
Contradiction
Inference
Private Interview progress
Current Scene
Presentation State
角色在场状态
```

## 14.1 Save != localStorage

禁止：

```ts
localStorage.setItem('save', JSON.stringify(gameStore))
```

原因：

- Frontend 不是 Game Truth；
- 无法完整保存角色 Memory；
- 容易绕过 backend gate；
- 无法保证角色可见性隔离；
- schema 升级难处理。

`localStorage` 只允许保存：

```text
anonymous player_id
非敏感 UI settings
已显示过性能提示之类的本地 UI 标记
```

## 14.2 Save 由 Backend Capture

正确流程：

```text
Vue
↓ save request
FastAPI
↓
SaveSnapshotService.capture(session_id)
↓
从权威 Runtime / Persistence 读取状态
↓
生成不可歧义 snapshot
↓
PostgreSQL
```

Frontend 不提交“我认为当前 Evidence 是什么”作为权威存档内容。

---

# 15. 匿名 Player 身份

本阶段不实现账号系统。

第一次打开游戏时：

```ts
crypto.randomUUID()
```

生成：

```text
player_id
```

并保存到：

```text
localStorage
```

之后所有 Save API 带上该 `player_id`。

## 15.1 定位

`player_id` 只是：

> 匿名浏览器存档命名空间。

它不是：

```text
登录凭据
强认证 token
权限系统
```

因此：

- 不存敏感信息；
- 不把它当安全边界；
- 换浏览器 / 清 localStorage 后默认无法自动找回旧存档；
- 跨设备同步留给未来账号系统。

---

# 16. Save 数据模型

推荐新增逻辑实体：

# GameSave

最小字段：

```text
id
player_id
slot_type          AUTO | MANUAL
slot_index         null for AUTO, 1..6 for MANUAL
title
source_session_id
schema_version
snapshot
chapter_id
phase
created_at
updated_at
```

其中：

```text
snapshot = JSONB
```

可选：

```text
thumbnail_path
playtime_seconds
```

首版不强制。

## 16.1 唯一约束

逻辑上保证：

```text
(player_id, AUTO) → 最多 1 个
(player_id, MANUAL, slot_index) → 每个 slot 最多 1 个
```

覆盖保存时更新对应 Slot，而不是无限创建重复 Slot。

## 16.2 schema_version

必须从第一版就保存：

```json
{
  "schema_version": 1
}
```

后续 Game State / Memory / Script DSL 发生结构变化时，必须通过：

```text
Save Migration
```

处理。

禁止未来偷偷改变 JSON 结构而让旧存档静默损坏。

---

# 17. Snapshot 内容

逻辑 snapshot 至少包含：

```json
{
  "schema_version": 1,
  "narrative": {},
  "script": {},
  "game_state": {},
  "characters": {},
  "memory": {},
  "messages": {},
  "investigation": {},
  "presentation": {}
}
```

## 17.1 narrative

包括当前正式剧情状态，例如：

```text
current chapter
phase
narrative flags
availability
unlocks
```

## 17.2 script

若当前存在 deterministic Script Runtime，保存其：

```text
current node / cursor
script variables
pending deterministic event
```

不得保存“正在执行到一半的异步 LLM future”。

## 17.3 characters

逐角色保存：

```text
character_state
availability
known fact references
current emotion
临时 deterministic status
```

## 17.4 memory

必须保持 per-character scope。

例如：

```json
{
  "deepseek": {},
  "claude": {},
  "chatgpt": {},
  "doubao": {}
}
```

恢复时禁止合并成一个 shared memory。

## 17.5 messages

保存当前剧情线需要恢复的消息历史或可确定恢复消息的 snapshot/cursor。

必须保留：

```text
speaker
content
visibility / perception scope
order
必要 metadata
```

否则加载后可能产生“角色突然知道没听见的私聊”问题。

## 17.6 investigation

保存：

```text
Evidence obtained
Claim Store
Contradiction confirmed
Inference confirmed
Private Interview unlock / completion
Investigation hotspot state
```

这些仍然属于 backend authoritative data。

## 17.7 presentation

保存恢复画面所需的最小状态：

```text
background
present characters
emotion
position override
basic effect stable state
current displayed dialogue reference
```

不要保存瞬时动画帧。

---

# 18. Save Capture 的一致性要求

一个 Save 必须是同一逻辑时间点的完整 Snapshot。

禁止出现：

```text
Narrative 已经到 Phase B
但 Memory 还是 Phase A
```

或者：

```text
EV05 已获得
但 Claim Store 没保存对应 Claim
```

## 18.1 事务

Backend Capture 应使用数据库事务或等价一致性机制：

```text
begin
↓
read/capture canonical state
↓
upsert save slot
↓
commit
```

Capture 失败：

```text
整个 Save 失败
```

不得写入半个存档。

---

# 19. Load 语义

## 19.1 不建议原地“倒带”当前 Session

推荐：

> **Load Save 创建一个新的 Active Session，并从 Snapshot 恢复。**

逻辑：

```text
Save A
↓
restore
↓
New Session B
↓
继续游戏
```

而不是：

```text
直接修改旧 Session A 的历史行
```

这样可以避免：

- 后续消息需要物理删除；
- Memory 已经写入未来信息；
- 分支历史难清理；
- 调试时无法追踪 Load 前后时间线。

## 19.2 Restore 顺序

推荐：

```text
validate schema_version
↓
create new session
↓
restore deterministic game/narrative state
↓
restore per-character state
↓
restore per-character memory
↓
restore message history + visibility
↓
restore investigation state
↓
restore presentation stable state
↓
run integrity validation
↓
return GameViewState
```

## 19.3 Restore 后必须再次校验

至少检查：

```text
character availability 与 Narrative State 一致
Evidence / Claim 关系合法
Inference 不可能早于所需 Evidence
Memory scope 没有跨角色泄漏
current scene 存在
script cursor 合法
```

校验失败：

```text
LOAD_FAILED_INVALID_SAVE
```

不要“尽量恢复然后继续玩”。

---

# 20. Save API

具体 URL 可适配现有 API 命名，但逻辑能力必须存在。

推荐：

```text
GET    /api/saves
POST   /api/saves/manual/{slot}
POST   /api/saves/auto
POST   /api/saves/{save_id}/load
DELETE /api/saves/manual/{slot}
```

以及：

```text
POST /api/game/sessions
```

用于 New Game。

## 20.1 List Saves

返回至少：

```json
{
  "auto": {},
  "manual": [
    {"slot": 1},
    {"slot": 2},
    {"slot": 3},
    {"slot": 4},
    {"slot": 5},
    {"slot": 6}
  ]
}
```

空 Slot 也应能由前端明确渲染。

## 20.2 Manual Save

请求至少带：

```text
player_id
session_id
slot_index
```

但 snapshot 内容由 Backend 自己 Capture。

## 20.3 Load

Load 成功返回：

```text
new_session_id
+
initial GameViewState
```

Frontend 随后进入 GameView。

---

# 21. Auto Save 设计

首版只保留 1 个 Auto Save。

每次合法自动存档：

```text
覆盖 AUTO slot
```

## 21.1 禁止每轮 AI 对话自动存档

原因：

- AI 输出期间可能处于中间态；
- Narrative Event 可能尚未 commit；
- Memory write 可能未完成；
- 频繁 DB snapshot 没有必要。

## 21.2 Auto Save 只在 Deterministic Checkpoint

第一章推荐 checkpoint：

```text
AS_CH1_OPENING_COMPLETE
AS_CH1_0317_TRIGGERED
AS_CH1_CLAUDE_APPEARED
AS_CH1_CT01_CONFIRMED
AS_CH1_CLAUDE_PRIVATE_COMPLETE
AS_CH1_INF01_CONFIRMED
AS_CH1_GPT_INTRO_COMPLETE
AS_CH1_DOUBAO_PRIVATE_COMPLETE
AS_CH1_CT04_CONFIRMED
AS_CH1_GPT_PRIVATE_COMPLETE
AS_CH1_INF03_CONFIRMED
AS_CH1_RECOVERY_ENTRY
```

不要求一次性全部接入。

第一批至少接：

```text
Opening Complete
Claude Appeared
INF01 Confirmed
INF03 Confirmed / Recovery Entry
```

然后根据稳定性补齐。

## 21.3 Auto Save 必须在状态 commit 后

正确：

```text
Narrative transition commit
↓
Memory / Evidence writes commit
↓
checkpoint reached
↓
Auto Save capture
```

错误：

```text
先存档
↓
再更新 Evidence
```

---

# 22. LLM 运行期间的 Save 行为

当：

```text
status = thinking / streaming
```

手动 Save 默认：

```text
disabled
```

并显示：

```text
当前对话尚未完成，请稍后保存。
```

不要尝试 snapshot：

```text
半句 streaming text
未完成 provider request
未校验 Character Response
```

Load 同理：

- 可以让用户先取消当前前端 stream；
- backend 对未完成请求必须有 session request id / stale response 防护；
- Load 后旧请求返回时不得写入新 Session。

---

# 23. 第一章主线与存档兼容

`11 — 第一章调查主线落地说明` 定义的核心链：

```text
03:17
↓
Claude
↓
EV02 / EV03 / EV04
↓
CT01
↓
Claude Private Interview
↓
EV05
↓
INF01
↓
EV06
↓
GPT
↓
Doubao
↓
EV08
↓
EV07
↓
CT04
↓
GPT Private Interview
↓
EV09
↓
INF03
↓
SANDBOX INTEGRITY FAILURE
↓
Recovery Entry
```

任何一个允许 Save 的位置，Load 后必须继续满足同一 Gate。

例如在：

```text
INF01 完成后
```

保存。

Load 后必须仍然满足：

```text
当前 DeepSeek 主要嫌疑已解除
EV06 已按规则解锁
Claude 私审结果仍存在
DeepSeek 不会突然获得不应知道的私人对话
```

---

# 24. Vue 与 Memory 的边界

Vue 可以展示：

```text
History
```

但不能拥有：

```text
Character Memory Truth
```

Frontend History：

> Player 实际已经看到过的对话记录。

Character Memory：

> 某角色被允许记住、检索和用于上下文的内容。

两者不能共用一个 Store 当作同一个概念。

尤其 Private Interview 后：

```text
Player 看见了 Claude 私聊
```

不等于：

```text
DeepSeek 也知道 Claude 私聊
```

Load Save 后同样必须保持这个边界。

---

# 25. 开发实施顺序

以下顺序是本文件的正式实施顺序。

---

## Task 0 — 建立迁移基线

### 做什么

1. 记录当前可运行 React commit。
2. 确认现有 frontend/backend 启动命令。
3. 跑现有 tests。
4. 对当前 React 关键画面截图留档。
5. 将 React Frontend 标记为 frozen。
6. 更新 `02 — System Architecture.md` Frontend 技术栈。

### 不做

- 不删除 React；
- 不改 Narrative Runtime；
- 不改第一章 Gate；
- 不动 Provider。

### 验收

```text
React 旧版本仍可启动
Backend tests 保持通过
迁移前截图存在
02 文档已同步 Vue 技术栈
```

---

## Task 1 — 建立 Vue 3 Web Frontend

### 做什么

建立：

```text
Vue 3
Vite
TypeScript
Pinia
TailwindCSS
Vue Router
```

初始版本优先采用与 LingChat 当前代码兼容的同 major dependency，避免一开始就同时做框架升级。

### 验收

```text
Docker Compose 可启动 Vue Frontend
浏览器可访问
Vue 可请求 FastAPI health endpoint
无 Tauri 依赖
```

---

## Task 2 — 迁入 LingChat Standard Game UI

### 做什么

按白名单复制源码。

建立文件来源清单，例如：

```text
LingChat path
→
Project path
→
Modification note
```

先用 Mock Presentation State 驱动。

### 第一轮只要求

```text
背景显示
DeepSeek立绘显示
Claude立绘显示
两角色自动站位
emotion切换
fade
基础动画
Dialogue UI
```

### 验收

在固定 viewport：

```text
1366x768
1920x1080
```

均满足：

- 背景无白边；
- 角色脚底/基线合理；
- 单角色居中；
- 双角色稳定左右布局；
- 表情切换不闪白；
- fade 无明显 layout jump；
- Dialogue 不遮挡主要面部区域；
- 不出现 LingChat 自己的角色/Logo/菜单文案。

---

## Task 3 — 去除 Tauri 与 LingChat Runtime 依赖

### 做什么

搜索并清零：

```text
@tauri-apps
invoke(
convertFileSrc
Tauri-only API
```

建立：

```text
api/
adapters/
asset-resolver
```

### 验收

```text
npm build / equivalent build succeeds
浏览器环境无 Tauri runtime error
角色资源全部通过 Web URL 加载
UI 组件不直接访问本地文件系统
```

---

## Task 4 — 接入现有 FastAPI Game Runtime

### 做什么

打通：

```text
New Session
Player Input
Streaming / Response
Presentation Directive
Character Presence
Emotion
Narrative Event
```

必须跑通：

```text
Opening
↓
DeepSeek对话
↓
03:17
↓
Claude出现
↓
Claude可对话
```

### 验收

- 不使用 Mock Provider state 伪装 Game State；
- LLM 不直接控制 Vue；
- Vue refresh 后现有 Session restore 能工作；
- 角色知识隔离 tests 不回归；
- 第一章 Gate 仍由 Backend 决定。

---

## Task 5 — 实现 Title Screen

### 做什么

基于 LingChat MainMenu 的视觉层与动画层，重建本项目 TitleView。

按钮：

```text
开始游戏
继续游戏
读取存档
设置
```

替换所有 LingChat：

```text
Logo
人物素材
Workshop
Script Editor
Game Mode
Script Mode
```

### 第一轮可使用

```text
现有游戏背景
本项目角色立绘
临时文字 Logo
```

不要求先生成最终 KV。

### 验收

- 首次进入不是直接落入对话场景；
- 无存档时 Continue 正确禁用/提示；
- New Game 创建新 Session；
- Back to Title 可正常工作；
- resize 时主菜单不溢出；
- 视觉风格与游戏内 UI 一致。

---

## Task 6 — 实现 Backend Save Snapshot

### 做什么

新增：

```text
GameSave
SaveSnapshotService
SaveRepository
Save API
Save schema version
```

实现：

```text
1 Auto
6 Manual
```

### 第一轮必须 capture

```text
Narrative State
Game State
Character State
Memory per character
Messages + visibility
Evidence / Claim / Contradiction / Inference
Private Interview progress
Scene / Presence / Emotion
```

### 验收

编写自动化测试：

```text
save → mutate current session → load → restored state == save snapshot
```

至少覆盖：

1. DeepSeek / Claude Memory 不串；
2. Evidence 恢复；
3. Claim 恢复；
4. Narrative phase 恢复；
5. Character availability 恢复；
6. Private Interview progress 恢复；
7. Load 创建新 Active Session；
8. schema_version 不支持时明确失败。

---

## Task 7 — 实现 Save / Load UI

### 做什么

实现：

```text
SavePanel
LoadPanel
AutoSaveCard
ManualSaveSlot x6
```

游戏内系统菜单接：

```text
Save
Load
History
Settings
Return Title
```

### 验收

```text
手动保存 Slot 1
↓
继续游戏改变状态
↓
返回标题
↓
Load Slot 1
↓
进入新 Session
↓
剧情/角色/Memory恢复
```

刷新浏览器后仍能列出 PostgreSQL 中的存档。

---

## Task 8 — 接入 Auto Save

### 做什么

先接 4 个稳定 checkpoint：

```text
Opening Complete
Claude Appeared
INF01 Confirmed
Recovery Entry / INF03 Confirmed
```

Auto Save 是 Narrative commit 后的 side effect。

### 验收

每个 checkpoint：

```text
到达
↓
AUTO updated_at 改变
↓
重启前端
↓
Continue
↓
恢复到合法 checkpoint
```

且不会出现：

```text
AI streaming 中间态
半完成 Evidence
跨角色 Memory 泄漏
```

---

## Task 9 — 视觉回归与 React Cutover

### 做什么

对比：

```text
LingChat reference
当前 React implementation
新 Vue implementation
```

重点检查：

```text
多角色舞台
立绘大小
站位
底部基线
Dialogue层级
文字可读性
emotion transition
fade
title screen
resize
```

### Cutover 条件

必须同时满足：

```text
Vue视觉显著优于旧React
第一章主线可运行
Save/Load可运行
backend tests通过
Vue build通过
无Tauri依赖
AGPL notice完成
```

完成后：

- Vue 成为默认 Frontend；
- Docker Compose 默认指向 Vue；
- 旧 React Frontend 可删除或移动到明确 deprecated archive；
- 不再双前端长期维护。

---

# 26. 测试要求

## 26.1 Frontend Unit / Component

至少覆盖：

```text
0角色
1角色
2角色
3角色
emotion变化
show/hide
loading/thinking
Dialogue long text
输入禁用
Save Slot empty/occupied
Continue no-save
```

## 26.2 Visual Regression

建议使用 Playwright screenshot。

至少两个 viewport：

```text
1366x768
1920x1080
```

关键 snapshot：

```text
TITLE_EMPTY_SAVE
OPENING_DEEPSEEK_ONLY
CLAUDE_APPEARS_TWO_ROLE
LONG_DIALOGUE
SAVE_PANEL
LOAD_PANEL
```

## 26.3 Backend Save Tests

至少：

```text
create manual save
overwrite manual save
create/overwrite auto save
list only current player_id saves
load creates new session
delete manual save
invalid save id
invalid schema version
transaction rollback
memory isolation after load
investigation gates after load
```

## 26.4 E2E

最低 E2E：

```text
Title
→ New Game
→ Opening
→ Player input
→ Character response
→ Claude appears
→ Manual Save Slot 1
→ continue state change
→ Return Title
→ Load Slot 1
→ assert restored
```

---

# 27. UI 达标判定

本阶段不能再使用：

> “功能都有了，所以 UI 完成。”

作为验收。

UI 必须同时达到：

## 27.1 结构

```text
全屏背景
角色与背景比例合理
Dialogue 视觉层明确
角色不被错误裁切
角色不会贴边
多人站位有呼吸空间
```

## 27.2 动态

```text
角色出现/消失有 transition
表情切换有 cross-fade
状态变化没有明显闪烁
窗口 resize 不跳位
```

## 27.3 一致性

```text
Title
Game
Save
Load
Settings
```

必须像同一个游戏，而不是五个独立 Web 页面。

## 27.4 参考对比

允许直接使用 LingChat 作为视觉行为参考。

如果迁移后明显出现：

```text
角色更小
站位更僵
对话框更像普通Web表单
动画被删掉
层级感消失
```

则不能以“已经使用 LingChat 源码”为由通过验收。

---

# 28. 性能边界

当前目标是 1 小时左右的 Web Galgame，不做过度优化。

但必须避免：

```text
每次文字更新导致所有角色图片重新加载
每个 stream token 触发整页重渲染
粒子动画压满主线程
隐藏角色仍持续执行昂贵动画
图片无尺寸控制导致巨量 layout shift
```

建议：

- 角色资源预加载；
- emotion 资源切换复用浏览器缓存；
- streaming text 与 Character Stage 分离更新；
- 粒子提供低性能开关；
- Title 动画在离开 Title 后卸载。

---

# 29. 安全边界

Vue Frontend 不得获得：

```text
DeepSeek API Key
OpenAI API Key
Provider secret
Database password
完整隐藏 Ground Truth
所有角色私有 Memory
```

`.env` 前端变量只能包含可公开信息。

所有 Provider Secret 仍只存在 Backend / Docker secret / server env。

Save API 也不得把完整隐藏 Character Memory 下发给浏览器后再上传保存。

---

# 30. Docker 目标

最终本地运行仍使用：

```text
Docker Compose
```

推荐：

```text
frontend-vue
backend
postgres
```

如果已有其他必要服务，保留现状。

迁移完成后不应新增：

```text
Tauri container
Rust service
LingChat DB service
```

Vue build 可通过：

```text
Node build
→ static assets
→ Web server
```

具体 Nginx / Node serving 可根据现有部署方式决定。

---

# 31. 本阶段明确不做

```text
账号系统
云端跨设备同步
Steam Cloud
多用户社交
Live2D
完整语音系统重构
LingChat Script Editor
Workshop
Mod系统
Tauri桌面打包
Rust Backend
Recovery小游戏本体
最终结局重写
```

如果迁移过程中发现上述能力“顺手就能做”，也不要扩张任务。

---

# 32. 常见错误

## 错误 1

```text
为了直接复用 Vue，顺便把 LingChat Rust 后端也搬过来。
```

**禁止。**

---

## 错误 2

```text
把 LingChat Vue 逐行翻译成 React。
```

**禁止。**

本阶段已经决定 Vue 直接承载表现层。

---

## 错误 3

```text
直接复制整个 LingChat src/。
```

**禁止。**

只复制白名单与真实依赖。

---

## 错误 4

```text
为了 UI 方便，让 Pinia 决定 Claude 是否出现。
```

**禁止。**

Claude 出现由 Narrative Runtime 决定。

---

## 错误 5

```text
把 Save 做成 localStorage dump。
```

**禁止。**

---

## 错误 6

```text
Load 时只恢复当前背景和聊天文本。
```

**禁止。**

Memory / Evidence / Narrative / Character State 必须一起恢复。

---

## 错误 7

```text
把 Player History 当成所有角色 Memory。
```

**禁止。**

---

## 错误 8

```text
因为项目整体 AGPL，就直接复制 LingChat 所有图片和字体。
```

**禁止。**

代码与素材授权必须区分。

---

# 33. Definition of Done

本阶段只有同时满足以下条件才算完成。

## 33.1 前端

- [ ] 默认游戏前端为 Vue 3 + Vite + TypeScript。
- [ ] LingChat 白名单 Gal UI 已实际复用并完成 Web Adapter。
- [ ] 无 Tauri runtime dependency。
- [ ] Background / multi-role / emotion / animation / dialogue 正常。
- [ ] 视觉效果明显达到或接近参考目标，而非普通 Web Chat UI。
- [ ] 1366x768 与 1920x1080 无严重布局问题。

## 33.2 游戏链路

- [ ] New Game 创建 Session。
- [ ] Player 自然语言输入仍是核心玩法。
- [ ] DeepSeek 可自由对话。
- [ ] 03:17 事件正常触发。
- [ ] Claude 正常出现。
- [ ] 第一章 Narrative Gate 未被 Frontend 绕过。
- [ ] Character Runtime / Memory 隔离测试不回归。

## 33.3 开始界面

- [ ] 有正式 Title Screen。
- [ ] 有 New Game。
- [ ] 有 Continue。
- [ ] 有 Load。
- [ ] 有 Settings。
- [ ] 无存档时 Continue 行为正确。

## 33.4 存档

- [ ] 1 Auto Save。
- [ ] 6 Manual Save Slots。
- [ ] 存档持久化到 PostgreSQL。
- [ ] Browser refresh 后仍可读取。
- [ ] Load 创建新的 Active Session。
- [ ] Narrative State 恢复。
- [ ] Evidence / Claim / Inference 恢复。
- [ ] Character State 恢复。
- [ ] Character Memory 按角色恢复且不泄漏。
- [ ] Message visibility 恢复。
- [ ] schema_version 存在。
- [ ] 非法/不兼容存档 fail safe。

## 33.5 开源与归属

- [ ] 根仓库含 AGPL-3.0 LICENSE。
- [ ] NOTICE 说明 LingChat 来源。
- [ ] THIRD_PARTY_LICENSES 存在。
- [ ] 复用文件来源有记录。
- [ ] 未未经确认复制 LingChat bundled assets。
- [ ] `.env` / API Key / Secret 未提交。

## 33.6 Cutover

- [ ] Vue E2E 通过。
- [ ] Backend tests 通过。
- [ ] Save E2E 通过。
- [ ] Visual regression 通过。
- [ ] Docker Compose 默认运行 Vue。
- [ ] 旧 React 不再承担生产/默认入口。

---

# 34. 推荐 Agent 执行粒度

不要把本文件一次性作为一个巨大任务交给 Agent。

推荐每次只执行一个 Task：

```text
Task 0
↓ 验收
Task 1
↓ 验收
Task 2
↓ 验收
Task 3
↓ 验收
Task 4
↓ 验收
Task 5
↓ 验收
Task 6
↓ 验收
Task 7
↓ 验收
Task 8
↓ 验收
Task 9
```

每个 Task 完成后输出：

```text
1. 修改了什么
2. 为什么这样改
3. 运行了哪些测试
4. 验收是否 PASS
5. 已知限制
6. 是否建议 commit
```

在前一个 Task 未 PASS 前，不进入下一个 Task。

---

# 35. 第一个可直接交给 Agent 的任务

```text
目标：执行 docs/13 的 Task 0，只建立 Vue 迁移基线，不开始复制 LingChat UI。

要求：
1. 阅读 docs/01、02、04、05、10、11、12、13。
2. 盘点当前 React frontend 的实际目录、启动方式、Docker Compose 配置和现有测试。
3. 记录当前可运行 commit / branch，确保可回退。
4. 将当前 React frontend 标记为 frozen；不要删除、不要重构。
5. 更新 docs/02 中 Frontend 技术路线为 Vue 3 + Vite + TypeScript + Pinia + TailwindCSS，但保持 Browser → FastAPI → Game Orchestrator → PostgreSQL 的总体关系不变。
6. 跑现有 backend/frontend tests 与 build，记录迁移前基线。
7. 对当前游戏 Opening / 单角色 / Claude 双角色画面生成基线截图（若对应场景当前可达）。

禁止：
- 不创建 Tauri/Rust；
- 不删除 React；
- 不改 Narrative Runtime；
- 不改 Character Runtime；
- 不改 Memory；
- 不改第一章剧情 Gate；
- 不开始迁移 LingChat 源码。

验收：
- 旧 React 仍可运行；
- 现有测试结果有记录；
- 迁移前截图有记录；
- docs/02 已同步新 Frontend 技术路线；
- 没有业务行为变化。

完成后只汇报结果与已知限制，不自动进入 Task 1。
```

---

# 36. 最终原则

本次迁移不是：

```text
把项目变成 LingChat
```

而是：

```text
使用 LingChat 已验证的 Gal Presentation
+
保留本项目自己的 AI Gal Runtime
```

最终系统必须始终保持：

```text
LingChat-derived UI
只是“怎么显示”

FastAPI Game Runtime
才决定“世界发生什么”
```

只要这个边界不被破坏，直接复用 LingChat UI 源码就不会削弱当前项目最核心的技术价值。
