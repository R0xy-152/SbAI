# 02 — System Architecture

> **文档状态：** Active  
> **适用阶段：** 轻量技术验证阶段  
> **文档职责：** 定义系统总体技术架构、组件边界、数据流、运行时依赖与部署边界。  
> **不负责：** 剧情规则、角色人格、Prompt设计、Memory内部算法、具体数据库表结构、具体API字段、测试用例。

---

# 1. Agent 读取规则

本文件是：

**系统架构真相源。**

Agent 在进行架构设计或代码实现时，应遵循：

1. 本文件定义组件职责与依赖方向。
2. 不得因为实现方便随意跨越组件边界。
3. 本文件不定义组件内部业务规则。
4. Narrative具体规则读取 `03-narrative-runtime.md`。
5. Character具体运行机制读取 `04-character-runtime.md`。
6. Memory具体机制读取 `05-memory-design.md`。
7. 当前MVP需求读取 `01-mvp-requirements.md`。
8. 未在本文件定义的内部实现细节，可以在不破坏组件边界的情况下自行决定。
9. 如果实现需要改变核心组件关系，应先修改本文件。

---

# 2. 架构目标

当前架构优先满足以下目标：

1. 快速完成轻量技术验证。
2. 支持标准 Galgame Web UI。
3. 支持多个不同角色运行时。
4. 支持生成式AI角色与剧本角色共存。
5. 保证LLM与确定性游戏逻辑解耦。
6. 支持对话上下文与后续Memory扩展。
7. 支持基础剧情状态推进。
8. 支持流式文本输出。
9. 支持基础动画与后续高级Meta UI演出。
10. 支持Docker化运行。
11. 避免当前阶段不必要的基础设施复杂度。

---

# 3. 总体架构

当前采用：

# Web Client + Application Backend + Relational Database

总体结构：

```text
┌──────────────────────────────────────────────┐
│                  Browser                     │
│                                              │
│              Web Game Client                 │
│                                              │
│  Background / Character / Dialogue / UI      │
│  Animation / Input / History / Effects       │
└──────────────────────┬───────────────────────┘
                       │
                 HTTP / Streaming
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                Backend API                   │
│                                              │
│             Game Orchestrator                │
│                       │                      │
│       ┌───────────────┼───────────────┐      │
│       ▼               ▼               ▼      │
│ Narrative Runtime Character Runtime Memory   │
│       │               │               │      │
│       │        ┌──────┼──────┐        │      │
│       │        ▼      ▼      ▼        │      │
│       │     DeepSeek ChatGPT Claude   │      │
│       │        │      │      │        │      │
│       │        └──────┼──────┘        │      │
│       │               ▼               │      │
│       │          LLM Providers        │      │
│       │                               │      │
│       │        豆包 → Script Runtime   │      │
│       │                               │      │
│       └───────────────┼───────────────┘      │
│                       │                      │
│                 State / Session              │
└───────────────────────┬──────────────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │   PostgreSQL    │
               │                 │
               │ Session         │
               │ Messages        │
               │ Game State      │
               │ Memory          │
               └─────────────────┘
```

---

# 4. 技术路线

当前轻量技术验证阶段采用以下技术方向。

## 4.1 Frontend

```text
Next.js
React
TypeScript
```

职责：

- 游戏画面
- Galgame UI
- 玩家文本输入
- 对话展示
- 角色立绘
- 背景
- 基础动画
- History
- Loading / Error状态
- 后续Meta UI演出

---

## 4.2 Backend

```text
Python
FastAPI
Pydantic
```

职责：

- 接收Player输入
- 管理Game Session
- 调用Game Orchestrator
- 调用角色Runtime
- 调用LLM Provider
- 组织上下文
- 校验结构化结果
- 管理游戏状态
- 调用Memory
- 向Frontend返回结果

---

## 4.3 Database

```text
PostgreSQL
```

当前阶段作为统一持久化数据库。

负责保存：

- Session
- Messages
- Game State
- Character State
- Memory
- 基础恢复数据

---

## 4.4 Deployment

```text
Docker
Docker Compose
```

当前阶段不引入：

- Kubernetes
- Service Mesh
- Kafka
- 独立Redis集群
- 独立Vector Database
- 微服务拆分

---

# 5. Frontend Architecture

Frontend定位为：

# Game Presentation Layer

它负责：

> 如何把当前游戏状态表现给Player。

它不负责：

> 决定剧情应该如何推进。

---

# 6. Frontend Layer结构

推荐逻辑结构：

```text
Game Client

├── Scene Layer
│   └── Background
│
├── Character Layer
│   ├── Character Sprite
│   ├── Expression
│   └── Character Animation
│
├── Effect Layer
│   ├── Fade
│   ├── Shake
│   └── Basic Effects
│
├── UI Layer
│   ├── Dialogue Box
│   ├── Character Name
│   ├── Player Input
│   ├── History
│   └── System UI
│
└── Meta Effect Layer
    └── 后续扩展
```

---

# 7. Frontend职责边界

Frontend可以：

- 根据Backend结果显示角色
- 根据Backend结果切换表情
- 播放允许的动画
- 显示背景
- 展示流式文本
- 展示Loading
- 展示错误状态
- 提交Player输入
- 请求History
- 恢复Session UI

Frontend不能自行决定：

- 某剧情是否完成
- 某Fact是否已获得
- Claude是否应该出现
- 某章节是否解锁
- 某角色是否知道某事实
- Player是否达成结局

这些属于Backend Game State。

---

# 8. Animation Architecture

动画采用：

# Named Animation Action

Frontend预定义有限动画集合。

例如：

```text
idle
fade_in
fade_out
shake
strong_shake
move_left
move_right
zoom_in
zoom_out
```

Backend只传递：

```text
animation = shake
```

Frontend负责：

> `shake`具体如何播放。

---

## 8.1 动画边界

Backend不应发送：

```text
x = -17
rotate = 31°
duration = 483ms
```

之类的任意动画代码。

原因：

> Game Logic应该触发动画语义，而不是直接控制浏览器渲染细节。

---

# 9. Meta UI扩展边界

后续允许增加：

```text
UI_CRACK
UI_GLITCH
UI_SHATTER
UI_HIDE
SCREEN_DISTORT
CLAUDE_UI_OVERRIDE
```

这些仍然应表现为：

# Named Effect

而不是让LLM直接修改DOM或执行Frontend代码。

---

# 10. Backend Architecture

Backend定位为：

# Authoritative Game Runtime

它是当前游戏状态的权威来源。

Frontend属于表现层。

LLM属于生成组件。

Backend负责最终决定：

> 当前游戏实际上发生了什么。

---

# 11. Backend主要模块

当前逻辑架构：

```text
Backend

├── API Layer
│
├── Game Orchestrator
│
├── Narrative Runtime
│
├── Character Runtime
│
├── Memory Service
│
├── Session / State Service
│
├── Provider Layer
│
└── Persistence Layer
```

这些属于逻辑模块。

当前阶段：

**不拆成独立微服务。**

全部运行在同一个Backend Application中。

---

# 12. API Layer

API Layer负责：

- 接收客户端请求
- 参数基本校验
- 用户Session定位
- 调用Game Orchestrator
- 返回普通响应
- 返回Streaming响应
- 标准化错误响应

API Layer不负责：

- Prompt构建
- 剧情判断
- Memory选择
- Character Persona
- Fact判断

---

# 13. Game Orchestrator

Game Orchestrator是一次Player交互的总协调器。

它负责：

> 将一次Player输入交给正确模块处理，并组织最终结果。

逻辑流程：

```text
Player Input
    ↓
Game Orchestrator
    ↓
读取 Session / Game State
    ↓
确定当前 Character Runtime
    ↓
准备所需 Context
    ↓
调用 Character Runtime
    ↓
获得 Character Response
    ↓
Narrative Runtime 校验
    ↓
更新允许的 Game State
    ↓
写入 Messages / Memory
    ↓
返回 Frontend
```

---

# 14. Game Orchestrator不负责

Game Orchestrator不应该直接包含：

- DeepSeek人格Prompt
- Claude人格Prompt
- 具体谜题规则
- Memory检索算法
- 数据库SQL细节
- Frontend动画代码

它只协调模块。

---

# 15. Narrative Runtime

Narrative Runtime负责：

> 确定生成内容能否对Game State产生影响。

主要涉及：

- 当前Scene
- 当前剧情阶段
- Flags
- 后续Fact系统
- Event
- Transition
- Narrative Validation

具体规则：

→ `03-narrative-runtime.md`

---

# 16. Character Runtime

Character Runtime负责：

> 给定当前允许上下文后，某角色应该如何产生回应。

逻辑结构：

```text
Character Runtime
│
├── Generative Character
│   ├── DeepSeek
│   ├── ChatGPT
│   └── Claude
│
└── Scripted Character
    └── 豆包
```

具体定义：

→ `04-character-runtime.md`

---

# 17. Provider Layer

Provider Layer负责屏蔽不同LLM API之间的差异。

逻辑接口：

```text
LLM Provider
│
├── DeepSeek Provider
├── OpenAI Provider
└── Anthropic Provider
```

Character Runtime不应直接处理：

- 不同供应商HTTP格式
- 不同鉴权格式
- 不同错误结构
- Provider特有请求字段

这些由Provider Layer统一处理。

---

# 18. Provider Architecture原则

角色与模型Provider必须解耦。

例如：

```text
ChatGPT Character
        ↓
OpenAI Provider
```

这是当前配置。

但系统结构不能写成：

```text
if character == chatgpt:
    调用某固定HTTP请求
```

Character Runtime只依赖统一Provider Interface。

---

# 19. Script Runtime

Script Runtime用于确定性角色。

当前：

```text
豆包
↓
Script Runtime
```

Script Runtime与LLM Provider并列存在。

豆包不会通过LLM Provider产生自由回复。

具体Script行为：

→ `04-character-runtime.md`

---

# 20. Memory Service

Memory Service负责：

> 为Character Runtime提供当前需要的历史上下文。

它与Game State分离。

Memory属于：

- 对话历史
- 角色经历
- 历史信息

Game State属于：

- 当前场景
- 当前阶段
- Flag
- 游戏状态

两者不得混为同一系统。

具体Memory结构：

→ `05-memory-design.md`

---

# 21. Session / State Service

负责保存当前Session确定性状态。

至少包括：

```text
session_id
current_scene
current_character
game_flags
character_states
```

具体字段允许后续调整。

本文件只规定：

> Game State必须由Backend持有并具备持久化能力。

---

# 22. Persistence Layer

Persistence Layer负责：

> Backend与PostgreSQL之间的数据访问。

其他业务模块不应大量散布直接数据库操作。

推荐逻辑：

```text
Game Logic
    ↓
Repository / Persistence Service
    ↓
PostgreSQL
```

---

# 23. Database职责

PostgreSQL是当前阶段唯一必须的持久化基础设施。

主要承担：

```text
Game Session
Messages
Game State
Character State
Memory
```

当前阶段：

**不要求独立Vector Database。**

---

# 24. pgvector状态

当前状态：

# Optional / P1

轻量技术验证阶段不依赖pgvector才能完成MVP。

如果后续Memory验证确认需要语义检索：

```text
PostgreSQL
+
pgvector
```

可以在当前数据库体系内扩展。

不需要因此修改总体架构。

---

# 25. Redis状态

当前状态：

# Not Required

当前阶段不引入Redis作为必要组件。

只有后续出现明确需求时再评估，例如：

- 多Backend实例
- 高频Cache
- Job Queue
- 分布式Session
- Rate Limit

---

# 26. 数据流：普通对话

一次普通DeepSeek对话：

```text
Player
  ↓
Frontend
  ↓
Backend API
  ↓
Game Orchestrator
  ↓
读取Game State
  ↓
Memory Service
  ↓
Character Runtime
  ↓
DeepSeek Provider
  ↓
DeepSeek Model
  ↓
Structured Character Response
  ↓
Validation
  ↓
保存Message
  ↓
Frontend Streaming
  ↓
Player
```

---

# 27. 数据流：剧情推进

如果Player输入可能推动剧情：

```text
Player Input
    ↓
Character Runtime
    ↓
Character Response
    ↓
Narrative Proposal
    ↓
Narrative Runtime
    ↓
Validate
   / \
PASS REJECT
 │      │
 ▼      ▼
State   保持原State
Change
 │
 ▼
Persistence
 │
 ▼
Frontend
```

核心原则：

> Character生成内容不能绕过Narrative Runtime直接修改Game State。

---

# 28. 数据流：豆包

正式接入豆包后：

```text
Player Input
    ↓
Game Orchestrator
    ↓
Character = 豆包
    ↓
Script Runtime
    ↓
根据当前状态选择剧本响应
    ↓
Narrative Validation
    ↓
Frontend
```

此流程：

**不经过LLM Provider。**

---

# 29. Streaming

当前MVP需要：

**渐进式角色文本反馈。**

系统架构需支持：

```text
Backend
↓
Streaming Response
↓
Frontend
```

当前交互模型主要是：

```text
Player发送一次
↓
Server返回一次角色回复
```

因此不要求当前阶段采用双向实时Socket架构。

---

# 30. Session架构

每次游戏运行必须存在：

```text
session_id
```

用于关联：

- Messages
- Game State
- Character State
- Memory

刷新页面后：

```text
session_id
↓
Backend
↓
读取Persistence
↓
恢复基本游戏状态
```

---

# 31. 前后端状态原则

## Backend

保存：

**Authoritative State**

例如：

- current_scene
- current_story_state
- flags
- character_state

---

## Frontend

保存：

**Presentation State**

例如：

- 当前动画是否播放中
- History面板是否展开
- 输入框内容
- 临时Loading状态
- 当前UI过渡状态

---

## 原则

Frontend状态丢失：

> 可以重新从Backend恢复游戏事实。

Backend状态丢失：

> 可能破坏Session。

因此：

**Backend State > Frontend State**

---

# 32. 错误处理边界

Provider调用失败不能直接污染Game State。

流程：

```text
调用LLM
↓
失败
↓
不提交Narrative State Change
↓
不产生错误Memory
↓
向Frontend返回可恢复错误
↓
Player Retry
```

---

# 33. Structured Output边界

Generative Character输出应进入：

```text
LLM
↓
Structured Response
↓
Schema Validation
↓
Narrative Validation
↓
Game State
```

不能采用：

```text
LLM自由文本
↓
直接修改数据库
```

的架构。

具体Character Response Schema：

→ `04-character-runtime.md`

---

# 34. Content与Code分离

长期目标要求：

> 剧情内容不应全部硬编码进业务代码。

建议逻辑分离：

```text
Code
├── Runtime
├── Validation
├── Provider
└── State

Content
├── Character Config
├── Scene Config
├── Script
└── Narrative Config
```

当前轻量验证阶段可以只实现最小Content结构。

---

# 35. 推荐仓库结构

逻辑结构建议：

```text
project-root/

├── frontend/
│
├── backend/
│
├── content/
│
├── docs/
│
├── tests/
│
├── docker-compose.yml
└── README.md
```

---

# 36. Frontend内部逻辑结构

```text
frontend/

├── app/
├── components/
│
├── game/
│   ├── scene/
│   ├── character/
│   ├── dialogue/
│   └── effects/
│
├── api/
├── state/
└── public/
    ├── backgrounds/
    └── characters/
```

属于推荐结构。

可以在不违反职责边界的情况下调整。

---

# 37. Backend内部逻辑结构

```text
backend/

└── app/

    ├── api/

    ├── game/
    │   ├── orchestrator
    │   ├── narrative
    │   └── state

    ├── characters/

    ├── providers/

    ├── memory/

    ├── persistence/

    └── models/
```

本目录结构不是绝对API契约。

真正必须遵守的是：

> 模块职责边界。

---

# 38. Content结构

建议：

```text
content/

├── characters/
├── scenes/
├── scripts/
└── narrative/
```

角色人格、Scene内容、豆包剧本、正式剧情数据可以逐步从代码中外置。

---

# 39. Docker运行边界

当前开发环境目标：

```text
docker compose up
```

能够启动：

```text
frontend
backend
postgres
```

逻辑：

```text
Docker Compose
│
├── frontend
├── backend
└── postgres
```

外部LLM Provider通过网络API访问。

---

# 40. 当前不采用微服务

当前所有Backend核心模块：

```text
Narrative
Character
Memory
State
Provider
```

运行于：

**同一个Backend应用进程体系。**

原因不是否认未来拆分可能性，而是：

> 当前阶段没有足够复杂度证明微服务带来的额外成本合理。

---

# 41. 当前不采用游戏引擎

轻量验证阶段Frontend采用Web技术。

当前不要求：

- Unity
- Unreal
- Godot

现有需求：

```text
固定背景
立绘
Gal UI
基础动画
Meta UI扩展
```

均属于当前Web Client职责范围。

如果未来核心玩法发生变化，再重新评估游戏引擎。

---

# 42. 可扩展动画架构

视觉层预留三个复杂度层级：

```text
基础UI / 角色动画
↓
常规Web Animation
↓
复杂剧情Timeline
↓
高级GPU Effect Layer
```

但当前架构只要求：

> 不阻塞未来增加高级视觉效果。

当前MVP不需要提前实现完整高级特效系统。

---

# 43. 安全边界

LLM Provider API Key：

**只能存在于Backend环境。**

不得：

- 写入Frontend代码
- 发送给Browser
- 存在于公开客户端配置
- 提交到Git仓库

Frontend只能访问自己的Backend。

---

# 44. LLM权限边界

LLM属于：

# Untrusted Generative Component

即使使用高能力模型，也不得视为游戏状态权威来源。

LLM可以生成：

- 对话
- 情绪建议
- 行为建议
- 动画建议
- Memory建议

但最终是否生效必须经过确定性系统。

---

# 45. 架构禁止项

当前阶段Agent不得主动引入：

```text
Kubernetes
Kafka
Service Mesh
微服务拆分
独立Vector DB
复杂消息队列
分布式缓存
事件总线基础设施
Graph Database
多数据库架构
```

除非出现：

> 当前架构无法满足已确认需求

的明确证据。

---

# 46. 核心架构原则

整个系统必须保持以下依赖方向：

```text
Player
  ↓
Frontend
  ↓
Backend API
  ↓
Game Orchestrator
  ↓
Domain Runtime
  ↓
External Provider / Persistence
```

禁止反向控制。

特别禁止：

```text
LLM
↓
直接控制Frontend

LLM
↓
直接写Database

Frontend
↓
自行推进Narrative State
```

---

# 47. 系统权威层级

发生冲突时：

```text
Deterministic Game State
        >
Narrative Runtime
        >
Character Runtime
        >
LLM Generated Content
        >
Frontend Presentation
```

其中：

**Game State 是最高运行时事实来源。**

---

# 48. 当前架构验收条件

当前架构在轻量验证阶段至少必须能够支撑：

```text
1个Web Client

1个Backend Application

1个PostgreSQL

DeepSeek Character Runtime

Claude Character Runtime

至少2个LLM Provider Adapter

Game Session

Game State

Memory最小实现

Streaming

基础Gal表现

刷新恢复
```

不要求此阶段证明大规模扩展能力。

---

# 49. 本文件不解决的问题

## 剧情如何判断玩家是否获得Fact？

→ `03-narrative-runtime.md`

## LLM具体输出什么Schema？

→ `04-character-runtime.md`

## DeepSeek具体Prompt是什么？

→ `04-character-runtime.md`

## Claude如何维持反派人格？

→ `04-character-runtime.md`

## Memory保留多少轮？

→ `05-memory-design.md`

## 是否使用Summary？

→ `05-memory-design.md`

## pgvector什么时候加入？

→ `05-memory-design.md`

## 每个技术验证实验怎么做？

→ `06-tech-validation-plan.md`

---

# 50. Agent最小上下文摘要

如果Agent只需要快速理解总体架构，可使用：

```text
架构：

Browser
→ Next.js Web Client
→ FastAPI Backend
→ PostgreSQL

Backend核心：
API
→ Game Orchestrator
→ Narrative Runtime / Character Runtime / Memory / State
→ Provider / Persistence

角色：
DeepSeek / ChatGPT / Claude = Generative Character
豆包 = Scripted Character

LLM：
只负责生成候选内容；
不是Game State权威。

Narrative Runtime：
决定LLM提出的状态变化是否生效。

Backend：
Authoritative Game State。

Frontend：
Presentation State。

Memory与Game State分离。

LLM Provider：
Adapter隔离不同模型供应商。

MVP：
单体Backend，不拆微服务。

部署：
Docker Compose
frontend + backend + postgres

当前禁止过度设计：
K8s / Kafka / Service Mesh / 独立Vector DB / Redis强依赖。

核心原则：
LLM不能直接控制Frontend、Database或Narrative State。
```