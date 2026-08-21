## 项目概览

《完蛋，我被AI娘包围了》—— AI-native Galgame / 对话式悬疑解谜游戏。玩家唯一主动交互是**与角色进行自然语言对话**；固定选项、战斗、自由地图、物品栏等均不是核心玩法。

**已完成**：TV-01（Gal UI Shell，PASS）、TV-02（Basic Presentation Action，PASS_WITH_LIMITATION）、TV-03（Backend Round Trip，PASS）、TV-04（DeepSeek Provider + 真实模型链路，PASS）、TV-05（Structured Character Response，PASS）、TV-06（Validate Before Present，PASS）、TV-07（Short-term Context，PASS）、TV-08（DeepSeek Blindness，PASS）、TV-09（Second Character Isolation，PASS）、TV-10（Narrative Signal，PASS）、TV-11（Deterministic Narrative Event，PASS）、TV-12（State-dependent Response，PASS）、TV-13（Important Memory，PASS）、TV-14（Session Restore，PASS）、TV-15（Failure Recovery，PASS）、TV-16（End-to-End Stability，Final Gate，PASS），TV-17（对话输出双模式 / Scripted Opening + ON_EVENT lines，后端 `backend/app/script/`，PASS）。**TV-01 ~ TV-17 技术验证计划已全部完成**。

**当前阶段**：进入 **docs/13（LingChat 前端源码迁移、开始界面与存档系统落地方案）**，前端从旧静态 UI 迁移到 Vue 3，并实现 Title Screen / Save-Load / Auto Save。Task 0-9 均已完成并有验证记录（Task 0/1 PASS_WITH_LIMITATION，其余 PASS；记录见 `validation-results/docs13-task*/result.md`）。随后执行了 docs/17 快速上线固定剧本（停用 AI、07 固定剧本 StoryView 已部署服务器：结局后 DeepSeek 自由聊天 + 场景演出接线 + 旧玩法正式入口）。2026-08-21 用户需求：AI 对话玩法新开局删除前置剧情（不播「你醒了，别怕」开场白、不自动弹「选择行动」窗口，直接自由对话，会话由首个玩家消息创建），常驻背景图替换为用户提供的新图 `backgroud/background_ai.png`（故事模式背景不变；见 docs/17 §2.5.2）。

## 文档是真相源（Docs-first）

`/docs` 是项目的事实来源，**代码若与文档冲突，以文档为准，停下实现并先修正文档**。写文档时尽量使用中文。按任务范围只读取相关文档，不要默认读完全部：

**基础 / MVP 文档（原 `docs/00..06` 已迁至 `docs/MVP/`）：**

- `docs/MVP/00 — Project Scope.md` — 项目边界 / 冻结设定，最高优先级
- `docs/MVP/01 — MVP Requirements.md` — 当前阶段需求 / 验收标准
- `docs/MVP/02 — System Architecture.md` — 系统架构、组件边界、数据流（§4.1：Vue 3 + Vite + TypeScript + Pinia + TailwindCSS；旧 `frontend/` 已冻结）
- `docs/MVP/03 — Narrative Runtime.md` — 剧情运行规则：自由语言 + 确定性剧情（Generative Dialogue + Deterministic Narrative），Narrative State / Signal / Event / Fact / Validation / State Commit
- `docs/MVP/04 — Character Runtime.md` — 角色运行（Persona、Knowledge 权限、Structured Response、Validation）
- `docs/MVP/05 — Memory Design.md` — Memory 分层、角色隔离、可见性
- `docs/MVP/06 — Tech Validation Plan.md` — TV 执行顺序、PASS/FAIL 标准、失败归因

**第一章功能文档（docs 顶层，均 Active）：**

- `docs/00-第一章功能文档索引.md` — 第一章八个功能文档（01-08）索引与「Backend 权威」跨切规则
- `docs/09-第一章开发落地备忘录.md` — 第一章落地备忘录（ACCS / 门禁漏洞 / Familiarity Residual 已废弃，改为封闭空间调查 + 证词 + 私审 + Recovery）
- `docs/10-第一章调查内容配置.md` — 第一章调查内容配置真相源（Evidence / Claim / Contradiction / Disclosure / Private Interview 内容）
- `docs/11-第一章调查主线落地说明.md` — docs/10 如何接入可运行 Runtime
- `docs/12 — 第一章叙事内容分配表.md` — 第一章各剧情节点内容分配（确定性 Script vs 生成式 Character Runtime vs Narrative Directive），止于 RECOVERY REQUIRED

**当前阶段计划：**

- `docs/13-LingChat前端源码迁移、开始界面与存档系统落地方案.md` — docs/13 前端迁移 + Title Screen + 存档系统，Task 0-9 执行与验收标准

注意：`docs/abandon/` 下是被废弃/取代的旧文档（第一章前身 `01/02/03`，以及被 docs/13 取代的 `12-LingChat-UI与多角色剧本系统借鉴落地方案.md`——其文件头仍标「Active」属过时残留）。docs/abandon/12 的 Script DSL 落地实现已迁入代码 `backend/app/script/`，不要与顶层 Active 的 `docs/12 — 第一章叙事内容分配表.md` 混淆。

`AGENT.MD` 规定开发行为约束，必须遵守，核心几条：

- 完成任务输出至少说明：完成了什么 / 修改了哪些文件 / 如何验证 / 结果是 PASS、PASS_WITH_LIMITATION 还是仍有问题 / 已知限制或下一项阻塞。
- 执行细节不明确时**必须向用户提问并追问，不能自做主张**。
- 修改范围尽量小，不顺手重构无关代码；不提前扩展当前任务不需要的功能。

## 常用命令

**现役前端 `frontend-vue/`（Vue 3 + Vite + TypeScript + Pinia + TailwindCSS）：**

```bash
cd /d/gal/frontend-vue && npm run dev        # vite dev（需 backend:8000；proxy /api、/char、/backgroud、/frontend → 127.0.0.1:8000）
cd /d/gal/frontend-vue && npm run build      # vue-tsc --noEmit --skipLibCheck && vite build
cd /d/gal/frontend-vue && npm run typecheck  # vue-tsc --noEmit --skipLibCheck
```

**旧前端 `frontend/`（已冻结，只修 P0 bug，不删、可回退）**：纯静态 HTML + CSS + 原生 JS，无 build step；测试是手写 DOM stub 的 `.cjs` 文件（无 jest/vitest/jsdom）。仍可运行：

```bash
node --check frontend/app.js
node frontend/tests/tv01-send.test.cjs   # 共 8 个 .cjs（tv01/02/03/14/16/17/18/ch1），node 直接运行
```

后端是 FastAPI（Python 3.12.9 venv，依赖见 `backend/requirements.txt`）。venv 命令要用绝对路径（Windows/Git Bash 下后台运行尤其如此）：

```bash
# 跑后端测试（fixture 已固定 GAL_PROVIDER=mock，无需 API key 和网络）
cd /d/gal/backend && .venv/Scripts/python -m pytest -q

# 启动后端（用真实 DeepSeek，需要 DEEPSEEK_API_KEY；key 只存在于环境变量，绝不入库）
cd /d/gal/backend && DEEPSEEK_API_KEY=sk-xxx .venv/Scripts/python -m uvicorn app.main:app --port 8000
```

Provider 选择由环境变量 `GAL_PROVIDER` 控制：`mock | deepseek | auto`（默认 `auto`：设置了 `DEEPSEEK_API_KEY` 就用 deepseek，否则 mock）。`DEEPSEEK_API_KEY` 缺失时 DeepSeekProvider 抛 `ProviderConfigError`。

**Docker**：仓库根 `docker-compose.yml` 定义三服务（frontend-vue nginx / backend / postgres，均 restart: unless-stopped）；服务器部署即用此文件（见 deploy/DEPLOY.md 与 docs/17）。本机无 Docker 时用 `npm run dev` + backend:8000 等价验证（docs/13 Task 1 采用此路径）。

## 架构：目标与当前实际的差距

**目标架构**（见 `docs/MVP/02 §4.1` 与 `docs/13`）：Browser → **Vue 3 Web Client**（`frontend-vue/`，Vite + TypeScript + Pinia + TailwindCSS）→ FastAPI Backend（Game Orchestrator → Narrative / Character / Memory / State）→ PostgreSQL，Docker Compose 部署（frontend-vue / backend / postgres）。Backend 是 Authoritative Game State，Frontend 只是 Presentation Layer。

**当前实际**：`backend/` 已有完整 FastAPI：`POST /api/chat`（`backend/app/api/chat.py`）→ `GameOrchestrator.handle_turn`（`backend/app/game/orchestrator.py`）→ 按角色构建的 Character Runtime（`backend/app/main.py` `build_provider` + runtimes `{deepseek, claude, chatgpt, doubao}`）→ `LLMProvider`（`backend/app/providers/`，mock / deepseek / anthropic）。orchestrator 接入 `NarrativeInterpreter`、`Chapter1InquiryInterpreter`、`SpeakerSelector`、`JsonSessionRepository`、`ScriptService` + `ScriptRuntime`，并带 availability 门控（claude/chatgpt/doubao 依赖 `*_has_appeared` 事件）。第一章调查系统在 `backend/app/game/`（investigation / evidence / deduction / private_interview / recovery / security_review / scene / speaker_selector）；Script DSL 在 `backend/app/script/`（schema / conditions / registry / chapter1 / runtime / service）；展示指令在 `backend/app/presentation/actions.py`（PresentationAction 11 种命名动作 + directive_to_actions 兼容旧 SHOW_CHARACTER）。已实现端点：`POST /api/chat`、`POST /api/chat/opening`、`GET /api/chat/history`，`/api/game/action|state|evidence|present|deduction|private-interview|recovery|security-review`，存档 `/api/saves*`（PostgreSQL，docs/13 Task 6 已接入），快速上线故事端点 `GET /api/story/current` / `POST /api/story/advance|choose`（docs/17）。会话持久化用 `JsonSessionRepository`（`backend/data/sessions/`，每会话一个 JSON，原子写，已 gitignore；docs/MVP/02 §22 Persistence Layer）。

前端双轨：`frontend/`（原生 HTML+CSS+JS 静态 UI，**已冻结**，仍由后端静态托管 `http://localhost:8000/frontend/index.html`）与 `frontend-vue/`（Vue 3 现役 Presentation Layer：views / stores / adapters / components / api）。前端把 `session_id` 存 localStorage，刷新后恢复同一会话。

关键架构原则（后续实现必须遵守）：

- **Frontend 只负责表现**，不能自行决定剧情推进、Fact、状态变化；只消费 Backend 的确定性结果。
- **动画用 Named Animation Action**（`fade_in` / `fade_out` / `shake` 等），Backend 只传语义名，不传 DOM 动画参数。`window.galPresentation.apply({ character, animation, expression })` 返回 `{ applied, reason }`；Vue 侧由 `presentation-adapter` 消费。
- **LLM 是不可信生成组件**：不能直接修改 Game State / Frontend / Database。生成内容必须走 `Structured Character Response → Schema Validation → Character Validation → Narrative Validation → Present`（Validate Before Present）。
- **剧情推进必须经过 Narrative Runtime**（见 `docs/MVP/03`）：Player 输入和 LLM 输出都只是 Proposal/Utterance，不能直接改 Game State；`Signal → Event → Requirements → State Commit`，无法可靠判断意图时 Fail Closed（不推进剧情）；主线 Event 默认 once + 幂等；玩家猜中真相 ≠ Fact Reveal。
- **DeepSeek「看不见」是权限边界而非 Prompt 自觉**：不能把视觉 Scene 信息放进她的 Context。
- **每个角色独立 Memory Scope / Knowledge**，跨角色信息不自动同步。

## 角色（DeepSeek / Claude / ChatGPT / 豆包）

- DeepSeek（生成式）：可爱、看不见、贪 Token、偷懒、没心机；**禁止给她未授权的视觉信息**。
- Claude（生成式）：高智商、强推理、**主线反派**、傲娇（傲娇不能削弱威胁感）。
- ChatGPT（生成式， 隐藏病娇）：已实现接入（`backend/app/characters/chatgpt.py`，含 GPT 私审）。
- 豆包（生成式 + scripted 兜底）：已实现接入（`backend/app/characters/doubao.py`；观察与解释分离，见 docs/MVP/06 §5，带 scripted 兜底行）。

注意：四个角色现均已作为 Runtime 接入 `backend/app/main.py`；豆包/ChatGPT 的 LLM/scripted 边界分别按各自文档约定。

## 验证与证据约定

- 每项任务（TV / docs/13 Task）完成后结果写入 `validation-results/<任务>/result.md`，记录状态、日期、环境、测试用例、结果、失败、限制、证据；**不要**把实验日志写回 `/docs`。
- 验证状态只有：`NOT_STARTED / IN_PROGRESS / PASS / PASS_WITH_LIMITATION / FAIL / BLOCKED`。
- 一次运行成功不等于 PASS；PASS 必须基于可复现证据。
- 允许临时 Fixture / Mock / 占位美术，但必须明确 **Fixture ≠ Production Content**；核心风险（真实生成链路、Validation、角色隔离、Narrative State Commit、Session Restore）不允许长期 Mock。
- 失败归因按层定位：UI/动画 → Frontend；调用 → Provider/API；格式 → Character Response/Validation；Persona → Character Runtime；知道不该知道的信息 → Context/Knowledge/Memory Scope；剧情错误推进 → Narrative；状态丢失 → Session/Persistence。不要一个问题同时改多个层。
- 当前阶段禁止主动引入：pgvector/RAG、Redis、Kafka、K8s、微服务、Live2D、Voice、高级特效等扩展。

## 代码约定

- Commit message 用 Conventional Commits，scope 是 TV 编号、docs13-task 或 feature，如 `feat(tv-03): ...`、`feat(docs13-task2): ...`、`feat(ch1): ...`。
- API Key / Secret 只能存在于 Backend 环境，不得进前端、仓库或提交记录。
- 剧情内容、角色配置、Scene 与 Runtime 代码分离；新依赖必须有当前任务直接理由。

当你执行一项任务发现有任何执行细节不明确时，你必须向我提问，而不是自做主张。
在我回答之后仍有不明确的执行细节时，你需要向我追问，直到了解了所有细节。
你可以在提问前查阅你需要了解的所有代码，并在了解了代码逻辑后再向我提问。
