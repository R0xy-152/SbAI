# docs/13 Task 0 — 迁移基线记录

> **状态：** PASS_WITH_LIMITATION（见「已知限制」）
> **日期：** 2026-08-19
> **执行依据：** `docs/13-LingChat前端源码迁移、开始界面与存档系统落地方案.md` §35

---

## 1. 做了什么

docs/13 Task 0（建立迁移基线）的六项动作：

1. **记录当前可运行 commit / branch**
   - branch：`main`
   - HEAD：`1c8f439`（fix(ch1): 更新纸面拓印线索文案）
   - 可回退基线成立。

2. **确认现有 frontend / backend 启动命令**
   - Backend：`cd /d/gal/backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000`
   - Frontend：**无独立启动**。纯静态页面，由 Backend 通过 `StaticFiles(directory=REPO_ROOT, html=True)` 挂载服务，浏览器访问 `http://localhost:8000/frontend/index.html`。
   - 仓库**不存在 docker-compose.yml**（Glob 无结果）。docs/02 §39 / docs/13 的 Docker Compose 目标当前未落地。
   - 开发预览配置：`.claude/launch.json` 提供 `gal-backend`(8000) 与 `gal-preview`(8001) 两个 uvicorn 配置。

3. **跑现有 tests（迁移前基线）**
   - Backend：`cd /d/gal/backend && .venv/Scripts/python -m pytest -q` → **338 passed**（1 warning，starlette/httpx 弃用提示，非失败）。
   - Frontend：`node --check frontend/app.js` → OK；`for t in frontend/tests/*.cjs; do node "$t"` → 8 个测试全部 PASS：
     - tv01-send / tv02-presentation / tv03-roundtrip / tv14-session-restore / tv16-endtoend / tv17-script-opening / tv18-character-stage / ch1-investigation-ui
   - 测试均无需 API key / 网络（GAL_PROVIDER=mock fixture）。

4. **对当前前端关键画面截图留档**（本目录）
   - `TASK0_OPENING.png` / `.jpg`（1350x621，896KB）— 开场 room_reveal 阶段
   - `TASK0_DEEPSEEK_SINGLE.png` / `.jpg`（1350x621，612KB）— 开场结束后单角色 DeepSeek
   - `TASK0_CLAUDE_DOUBLE.png` / `.jpg`（1350x621，1041KB）— 恢复走查会话 73c4a56d 后的 Claude + DeepSeek 双角色
   - 截图由 `capture-baseline.mjs`（headless Chrome + CDP）生成并落盘。PNG 签名与尺寸已验证有效；画面内容由脚本日志的 DOM 状态佐证：
     - 开场阶段 = `room_reveal`
     - 单角色 = 开场完成、player input enabled、新 session `6180d8bc...`
     - 双角色 = `#character-stage figure[data-character="claude"]` 存在、deepseek 锚点可见、presentation_state 含 claude+deepseek

5. **标记旧前端 frozen**
   - 在 `docs/MVP/02 — System Architecture.md` §4.1 增补迁移状态说明：现有 `frontend/` 冻结，不再新增 UI 功能，仅修复阻塞运行的 P0 bug，保持可回退；Vue 链路验收通过后再删除。
   - 未删除、未重构任何前端代码。

6. **更新 docs/MVP/02 Frontend 技术路线**
   - §4.1：`Next.js / React / TypeScript` → `Vue 3 / Vite / TypeScript / Pinia / TailwindCSS`（docs/13 §1.2 指定文案）。
   - §50 Agent 最小上下文摘要：`Next.js Web Client` → `Vue 3 Web Client`。
   - 全文已无 Next.js / React 残留引用。
   - Browser → FastAPI → Game Orchestrator → PostgreSQL 的总体关系未改动。

---

## 2. 为什么这样改

- docs/13 §1.2 / §35 明确要求同步 docs/02 的 Frontend 技术路线，且「总体架构仍然保持 Browser → FastAPI → Game Orchestrator → PostgreSQL」。因此只改 §4.1 与 §50 的技术栈字样，不触碰架构关系与各组件职责边界。
- 冻结旧前端而非直接删除，是 docs/13 §7 的显式要求（Vue 验收前禁止删除 React；本仓库实际为原生 JS 前端，同样适用）。
- 截图使用 headless Chrome + CDP 落盘：预览环境的 Browser pane 当前不可显示导致 preview_screenshot 无法合成帧；该方案直接产出可入库的 PNG/JPEG 基线文件，可复现（`capture-baseline.mjs`）。

---

## 3. 运行了哪些测试 / 验证

| 项目 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `pytest -q` | 338 passed |
| 前端语法 | `node --check frontend/app.js` | OK |
| 前端 8 项 | `node frontend/tests/*.cjs` | 全部 PASS |
| 后端 opening API | `POST /api/chat/opening {session_id:null}` | 200，返回 deepseek |
| 后端 state API | `GET /api/game/state?session_id=73c4a56d...` | 200，claude+deepseek 在场 |

---

## 4. 验收对照

| 验收项 | 结果 |
|---|---|
| 旧前端仍可运行 | ✅ 后端 8000 端口正常服务静态前端，截图脚本实跑通过 |
| 现有测试结果有记录 | ✅ 见上表 |
| 迁移前截图有记录 | ✅ 本目录 3 张 PNG + JPEG |
| docs/02 已同步新 Frontend 技术路线 | ✅ §4.1 + §50 已改为 Vue 3 技术栈，无 React 残留 |
| 没有业务行为变化 | ✅ 未改任何代码，仅文档；测试全绿 |

**结论：PASS_WITH_LIMITATION**（限制见下）。

---

## 5. 已知限制 / 需用户决策

1. **docs/13 中「现有 React / Next.js 前端」与仓库实际不符**：当前前端是原生 HTML+CSS+JS（`frontend/`），不存在 React/Next.js 代码。docs/13 全文按「从 React 迁移」撰写（§7 旧前端策略、§35 等）。本次按「冻结现有原生 JS 前端」等同处理其意图，但建议**修正 docs/13 的相关措辞**（把「React 前端」改为「当前原生 JS 前端」），避免后续 Agent 误解。此项是 Task 0 的最主要差异，未改动 docs/13 正文。
2. **无 Docker / PostgreSQL**：docs/02 目标架构与 docs/13 §30/§33 要求 Docker Compose + PostgreSQL 存档；当前只有 JSON 文件持久化（`backend/data/sessions/`，gitignored，当前 1625 个会话文件）。Task 6（Backend Save Snapshot）将要求引入 PostgreSQL 或先在现有 JSON Repository 上实现，需在 Task 6 前决策。
3. **截图工具链**：本环境预览 pane 不可合成帧，基线截图改由 `capture-baseline.mjs`（headless Chrome）生成，可复现；但 1366x768 之外的 viewport（如 1920x1080）基线未留档（docs/13 §26.2 的 1920x1080 要求属 Task 9 视觉回归范畴）。
4. **docs/13 引用的旧文档路径**：docs/13 §1 要求读取的 `01 — MVP Requirements.md`、`02 — System Architecture.md`、`04 — Character Runtime.md`、`05 — Memory Design.md` 现位于 `docs/MVP/`；`12 — LingChat UI...借鉴落地方案` 已移入 `docs/abandon/`。本次按 `docs/MVP/` 与 `docs/abandon/` 对应读取。

---

## 6. 是否建议 commit

**建议**：单独 commit 本 Task（`docs(docs13): task0 迁移基线` 一类 Conventional Commit；scope 建议 `docs13`）。内容：docs/MVP/02 的两处文档修改 + `validation-results/docs13-task0/` 基线文件（result.md、3 张 PNG/JPEG、capture 脚本）。截图脚本与 PNG 建议一并提交，作为可复现的迁移前证据。

> 按 docs/13 §34/§35：本 Task 完成后**只报告结果与已知限制，不自动进入 Task 1**。等待用户确认后再开始 Task 1（建立 Vue 3 Web Frontend）。
