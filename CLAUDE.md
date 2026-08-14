# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

《完蛋，我被AI娘包围了》—— AI-native Galgame / 对话式悬疑解谜游戏。玩家唯一主动交互是**与角色进行自然语言对话**；固定选项、战斗、自由地图、物品栏等均不是核心玩法。

当前阶段是**轻量技术验证（Lightweight Tech Validation）**，目标是打通一条 Vertical Slice 链路（Gal UI → 自然语言输入 → 生成式角色 → 角色隔离 → 确定性 Narrative State → 对话驱动剧情 → Session 恢复），共 TV-01 ~ TV-16 十六项，按依赖顺序执行。

**已经完成**：TV-01（Gal UI Shell，PASS）、TV-02（Basic Presentation Action，PASS_WITH_LIMITATION）、TV-03（Backend Round Trip，PASS）、TV-04（DeepSeek Provider + 真实模型链路，PASS）、TV-05（Structured Character Response，PASS）、TV-06（Validate Before Present，PASS）、TV-07（Short-term Context，PASS）、TV-08（DeepSeek Blindness，PASS）、TV-09（Second Character Isolation，PASS）、TV-10（Narrative Signal，PASS）。当前工作起点是 TV-11（Deterministic Narrative Event）。每项 TV 的验证记录在 `validation-results/TV-xx/result.md`。

## 文档是真相源（Docs-first）

`/docs` 是项目的事实来源，**代码若与文档冲突，以文档为准，停下实现并先修正文档**。按任务范围只读取相关文档，不要默认读完全部：

- `docs/00 — Project Scope.md` — 项目边界 / 冻结设定，最高优先级
- `docs/01 — MVP Requirements.md` — 当前阶段需求 / 验收标准
- `docs/02 — System Architecture.md` — 系统架构、组件边界、数据流
- `docs/03 — Narrative Runtime.md` — 剧情运行规则：自由语言 + 确定性剧情（Generative Dialogue + Deterministic Narrative），Narrative State / Signal / Event / Fact / Validation / State Commit
- `docs/04 — Character Runtime.md` — 角色运行（Persona、Knowledge 权限、Structured Response、Validation）
- `docs/05 — Memory Design.md` — Memory 分层、角色隔离、可见性
- `docs/06 — Tech Validation Plan.md` — TV 执行顺序、PASS/FAIL 标准、失败归因

`AGENT.MD` 规定开发行为约束，必须遵守，核心几条：

- 完成任务输出至少说明：完成了什么 / 修改了哪些文件 / 如何验证 / 结果是 PASS、PASS_WITH_LIMITATION 还是仍有问题 / 已知限制或下一项阻塞。
- 执行细节不明确时**必须向用户提问并追问，不能自做主张**。
- 修改范围尽量小，不顺手重构无关代码；不提前扩展当前 TV 不需要的功能。

## 常用命令

前端是纯静态页面（HTML + CSS + 原生 JS），无 build step；测试是手写 DOM stub 的 `.cjs` 文件（无 jest/vitest/jsdom），新 TV 测试沿用同样模式。资源（立绘、背景）以相对仓库根目录的路径引用。

```bash
node --check frontend/app.js
node frontend/tests/tv01-send.test.cjs
node frontend/tests/tv02-presentation.test.cjs
node frontend/tests/tv03-roundtrip.test.cjs
```

后端是 FastAPI（Python 3.12.9 venv，依赖见 `backend/requirements.txt`）。venv 命令要用绝对路径（Windows/Git Bash 下后台运行尤其如此）：

```bash
# 跑后端测试（fixture 已固定 GAL_PROVIDER=mock，无需 API key 和网络）
cd /d/gal/backend && .venv/Scripts/python -m pytest -q

# 启动后端（用真实 DeepSeek，需要 DEEPSEEK_API_KEY；key 只存在于环境变量，绝不入库）
cd /d/gal/backend && DEEPSEEK_API_KEY=sk-xxx .venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Provider 选择由环境变量 `GAL_PROVIDER` 控制：`mock | deepseek | auto`（默认 `auto`：设置了 `DEEPSEEK_API_KEY` 就用 deepseek，否则 mock）。`DEEPSEEK_API_KEY` 缺失时 DeepSeekProvider 抛 `ProviderConfigError`。

## 架构：目标与当前实际的差距

**目标架构**（见 `docs/02`，尚未实现）：Browser → Next.js Web Client → FastAPI Backend（Game Orchestrator → Narrative / Character / Memory / State）→ PostgreSQL，Docker Compose 部署。Backend 是 Authoritative Game State，Frontend 只是 Presentation Layer。

**当前实际**：`frontend/` 有静态 UI（Gal UI Shell + 已接入 `/api/chat` 的聊天框）。`backend/` 已有 FastAPI 骨架：`POST /api/chat`（见 `backend/app/api/chat.py`）→ `GameOrchestrator.handle_turn`（`backend/app/game/orchestrator.py`，解析 session、记 player message、调角色 Runtime、记 character message）→ `DeepSeekRuntime`（`backend/app/characters/deepseek.py`，Persona prompt）→ `LLMProvider`（`backend/app/providers/`，`mock` 确定性 mock / `deepseek` 真实模型）。`SessionStore` 非持久化（有意为之，TV-14 才接持久化）。无 Docker/PostgreSQL。TV-05 起 Character Response 变成结构化 JSON（emotion/animation_proposal 等），带 Schema 校验 + Repair + Safe Fallback。

关键架构原则（后续实现必须遵守）：

- **Frontend 只负责表现**，不能自行决定剧情推进、Fact、状态变化；只消费 Backend 的确定性结果。
- **动画用 Named Animation Action**（`fade_in` / `fade_out` / `shake` 等），Backend 只传语义名，不传 DOM 动画参数。TV-02 已实现 `window.galPresentation.apply({ character, animation, expression })`，返回 `{ applied, reason }`；TV-03 将把指令来源换成 Backend。
- **LLM 是不可信生成组件**：不能直接修改 Game State / Frontend / Database。生成内容必须走 `Structured Character Response → Schema Validation → Character Validation → Narrative Validation → Present`（Validate Before Present）。
- **剧情推进必须经过 Narrative Runtime**（见 `docs/03`）：Player 输入和 LLM 输出都只是 Proposal/Utterance，不能直接改 Game State；`Signal → Event → Requirements → State Commit`，无法可靠判断意图时 Fail Closed（不推进剧情）；主线 Event 默认 once + 幂等；玩家猜中真相 ≠ Fact Reveal。
- **DeepSeek「看不见」是权限边界而非 Prompt 自觉**：不能把视觉 Scene 信息放进她的 Context。
- **每个角色独立 Memory Scope / Knowledge**，跨角色信息不自动同步。

## 角色（当前只涉及 DeepSeek 和 Claude）

- DeepSeek（生成式）：可爱、看不见、贪 Token、偷懒、没心机；**禁止给她未授权的视觉信息**。
- Claude（生成式）：高智商、强推理、**主线反派**、傲娇（傲娇不能削弱威胁感）。
- 豆包：完全 Scripted，**不得调用 LLM**。ChatGPT：正派 + 隐藏病娇。二者当前 MVP 暂不正式接入。

## 验证与证据约定

- 每项 TV 完成后结果写入 `validation-results/TV-xx/result.md`，记录状态、日期、环境、测试用例、结果、失败、限制、证据；**不要**把实验日志写回 `/docs`。
- 验证状态只有：`NOT_STARTED / IN_PROGRESS / PASS / PASS_WITH_LIMITATION / FAIL / BLOCKED`。
- 一次运行成功不等于 PASS；PASS 必须基于可复现证据。
- 允许临时 Fixture / Mock / 占位美术，但必须明确 **Fixture ≠ Production Content**；核心风险（真实生成链路、Validation、角色隔离、Narrative State Commit、Session Restore）不允许长期 Mock。
- 失败归因按层定位：UI/动画 → Frontend；调用 → Provider/API；格式 → Character Response/Validation；Persona → Character Runtime；知道不该知道的信息 → Context/Knowledge/Memory Scope；剧情错误推进 → Narrative；状态丢失 → Session/Persistence。不要一个问题同时改多个层。
- 当前阶段禁止主动引入：pgvector/RAG、Redis、Kafka、K8s、微服务、Live2D、Voice、高级特效等扩展。

## 代码约定

- Commit message 用 Conventional Commits，scope 是 TV 编号，如 `feat(tv-03): ...`。
- API Key / Secret 只能存在于 Backend 环境，不得进前端、仓库或提交记录。
- 剧情内容、角色配置、Scene 与 Runtime 代码分离；新依赖必须有当前任务直接理由。

当你执行一项任务发现有任何执行细节不明确时，你必须向我提问，而不是自做主张。
在我回答之后仍有不明确的执行细节时，你需要向我追问，直到了解了所有细节。
你可以在提问前查阅你需要了解的所有代码，并在了解了代码逻辑后再向我提问。