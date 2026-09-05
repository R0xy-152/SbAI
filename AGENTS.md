# AGENTS.md

本文件是仓库唯一权威操作指引（Codex / Claude / 其他编码工具均以此为准）。
线上运营状态（服务器/备案/待办）另见 `deploy/STATUS.md`，不在本文件重复。

## 1. 项目定位与当前阶段

《完蛋，我被AI娘包围了》—— AI-native Galgame / 对话式悬疑解谜游戏；核心语义输入是自然语言对话与 Evidence 推理。

- TV-01~TV-17 技术验证全部完成（记录见 `validation-results/TV-*/result.md`）；docs/13 前端迁移+存档 Task 0-9 全部完成（`validation-results/docs13-task*/result.md`）。
- docs/17 快速上线已部署：固定剧本故事模式（/story，AI 停用）+ 结局后 DeepSeek 自由聊天（/game 复用）+ 场景演出接线 + 旧调查玩法正式入口（「行动」按钮）。
- 2026-08-21：「序章」新开局进入 `docs/story/Prologue.md` 固定剧本；三名角色探班顺序由玩家从剩余角色中反复选择，全部访问后汇合并选择一名角色进入 AI 后日谈自由聊天。序章常驻背景为 `backgroud/background_prologue.png`。标题「开始游戏」先进入章节选择，当前仅序章解锁。
- 2026-09-04：在 `codex/trial-demo` 开发独立 `trial_v1` 试玩版（方案见 `docs/23-核心玩法闭环试玩版落地方案.md`）。原“Player + DeepSeek 被绑”开场遗弃但保留为前期实验；现役试玩开场改为原初 AI 深夜对话。原初 AI 的玩家可见名称必须遮蔽。
- 2026-09-05：试玩版叙事重构为「完美恋人 → 修复=授权 → 自主性增长 → Monika 式觉醒（她丢弃 UI）→『她的世界』记忆横版 → 三结局由行进方向决定」（方案见 `docs/27-试玩版叙事重构-回忆闪回与三结局落地方案.md`，取代 docs/23 体验流程章节；docs/23 技术章节仍有效）。
- **当前边界：不自行补写剧情**——允许实现已确认的试玩版 Runtime、交互与明确标注的 Fixture；正式对白、Evidence 答案与分支内容先与用户确认。

## 2. 文档真相源（Docs-first）

`/docs` 是事实来源；代码与文档冲突以文档为准，停下实现并先修正文档。按任务只读相关文档：

- 最高优先级：`docs/MVP/00 — Project Scope.md`（边界/冻结设定）
- 运行时：`docs/MVP/02`（架构）`03`（Narrative）`04`（Character）`05`（Memory）
- 第一章内容：`docs/09`（落地备忘录）`10`（调查内容真相源）`11`（调查落地）`12 — 第一章叙事内容分配表.md`
- 当前阶段方案：`docs/13-...落地方案.md`、`docs/17-快速上线固定剧本落地方案.md`（已上线）
- 试玩版：`docs/23-核心玩法闭环试玩版落地方案.md`（`trial_v1` 范围、交互、状态与验收；体验流程已被 docs/27 取代，技术章节仍有效）、`docs/27-试玩版叙事重构-回忆闪回与三结局落地方案.md`（叙事与玩法真相源）
- 注意：`docs/abandon/` 是废弃文档；顶层 `docs/12` ≠ `docs/abandon/12`。

## 3. 硬规则（不可协商）

- 执行细节不明确时**必须向用户提问并追问**，不自做主张；用户偏好中文。
- 修改范围尽量小：不顺手重构无关代码，不提前扩展不需要的功能。
- 剧情内容 / 角色配置 / Scene 与 Runtime 代码分离。
- Frontend 只负责表现：不决定剧情/Fact/状态，只消费 Backend 确定性结果。
- LLM 不可信：生成内容必须走 Structured Response → Schema/Character/Narrative Validation → Present，不能直接改 Game State/Frontend/DB。
- 剧情推进必须经 Narrative Runtime（Signal→Event→Requirements→Commit；猜中真相≠Fact Reveal；主线 Event 默认 once+幂等）。
- DeepSeek「看不见」是权限边界：视觉 Scene 信息不得进她的 Context。
- API Key / Secret 只在 Backend 环境，绝不进前端、仓库、提交记录。
- 当前阶段禁止引入：pgvector/RAG、Redis、Kafka、K8s、微服务、Voice。经 2026-09-04 Scope Change，`trial_v1` 仅允许在开局表现层受控验证/接入单角色、单 Canvas 的 Live2D，并必须有静态图回退、发布许可审查和明确资源释放；Live2D 不得成为剧情状态源，其视觉信息不得进入任何角色 Context。`trial_v1` 同时允许在硬件能力与减少动态效果设置约束下实现玻璃破裂、碎片拼合与文字多体运动；剧情状态仍由 Backend 权威提交。经 2026-09-05 Scope Change，`trial_v1` 允许新增手写 Canvas 2D 横版世界「她的世界」（记忆横版）：不引入游戏引擎/WebGL/物理库，地形文字来自 Backend 下发会话数据，关卡门与结局仍由 Backend 权威提交。

## 4. 架构现状速览

- Browser → `frontend-vue/`（Vue3+Vite+TS+Pinia+Tailwind，现役）→ FastAPI（`backend/`，权威游戏状态）→ PostgreSQL（存档；会话 JSON 在 `backend/data/sessions/`）。`frontend/`（旧原生 UI）已冻结，只修 P0，仍由后端托管 `/frontend/index.html`。
- 视图：TitleView（标题/存档路由）→ ChapterSelectView（/chapters，当前仅序章）→ StoryView（`/story?story_id=prologue` 固定序章；无参数 `/story` 保留既有第一章存档恢复）→ GameView（/game 后日谈 AI 自由聊天 + 旧调查玩法）。
- 端点：`POST /api/chat|chat/opening`、`GET /api/chat/history`、`/api/game/action|state|evidence|present|deduction|private-interview|recovery|security-review`、`/api/saves*`、`GET /api/story/current`、`POST /api/story/advance|choose`。
- AI：序章结尾可选择 DeepSeek / ChatGPT / Claude 进入对应角色后日谈；`GAL_PROVIDER`（mock|deepseek|auto）+ `DEEPSEEK_API_KEY` 控制，缺 key 回落 mock。

## 5. 角色（写角色相关代码看这四条）

- DeepSeek：可爱、看不见、贪 Token、没心机；**禁止视觉信息**。
- Claude：高智商、主线反派、傲娇（不削弱威胁感）。
- ChatGPT：正派 + 隐藏病娇；含 GPT 私审。
- 豆包：生成式 + scripted 兜底（观察与解释分离）。

## 6. 常用命令

```bash
cd /d/gal/backend && .venv/Scripts/python -m pytest -q   # 后端测试（GAL_PROVIDER=mock，无需 key/网络）
cd /d/gal/frontend-vue && npm run typecheck               # vue-tsc
cd /d/gal/frontend-vue && npm run test                    # vitest
cd /d/gal/frontend-vue && npm run build                   # typecheck + vite build
# 本机联调：backend :8000 + npm run dev（:5173，proxy /api /char /backgroud → 8000）
# 本机免登录测试：backend 以 GAL_AUTH_REQUIRED=false 启动（前端 Vite dev 已自动绕过登录守卫；线上构建与部署默认保持鉴权）
```

部署/服务器（详见 `deploy/DEPLOY.md`；Windows 下必须用 git bundle，勿用 git archive）：

```bash
cd /d/gal && git bundle create gal-new.bundle HEAD
backend/.venv/Scripts/python deploy/remote.py --host 114.55.133.96 --user root --password '...' --put gal-new.bundle /srv/gal-new.bundle
# 服务器：cd /srv/gal && git fetch /srv/gal-new.bundle HEAD && git reset --hard FETCH_HEAD && docker compose build backend frontend-vue && docker compose up -d
# .env 不入库、reset 后保留；改 .env 后需 docker compose up -d backend 重建生效
```

UI 冒烟：`frontend-vue/scripts/story-smoke.mjs`、`ai-entry-smoke.mjs`（Playwright；GAL_BASE_URL/GAL_OUT_DIR 可覆盖目标）。

## 7. 验证与证据约定

- 任务结果写入 `validation-results/<任务>/result.md`（状态/日期/环境/用例/结果/失败/限制/证据）；实验日志不进 /docs。
- 状态只有 NOT_STARTED / IN_PROGRESS / PASS / PASS_WITH_LIMITATION / FAIL / BLOCKED；一次成功≠PASS，PASS 需可复现证据。
- Fixture ≠ Production Content：允许占位美术/Mock，但核心链路（真实生成、Validation、角色隔离、Narrative Commit、Session Restore）不许长期 Mock。
- 失败归因按层：UI→Frontend；调用→Provider；格式→Character Validation；Persona→Character Runtime；越权信息→Context/Memory Scope；剧情错误→Narrative；状态丢失→Persistence。不要同时改多层。

## 8. 代码约定

- Commit 用 Conventional Commits，scope 如 `feat(tv-..)`、`feat(docs13-task..)`、`feat(game)`、`docs(deploy)`。
- 完成任务输出至少用中文说明：完成了什么 / 改了哪些文件 / 如何验证 / 结果（PASS 等级）/ 已知限制与阻塞。
