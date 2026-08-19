# docs/13 Task 1 — Vue 3 Web Frontend

> **状态：** PASS_WITH_LIMITATION（见「已知限制」：Docker Compose 本机无法实跑，改用等价 vite 验证）
> **日期：** 2026-08-19
> **执行依据：** `docs/13-LingChat前端源码迁移、开始界面与存档系统落地方案.md` §25 Task 1 / §35

---

## 1. 做了什么

建立了 `frontend-vue/` Vue 3 Web Frontend 骨架（docs/13 §6 目标结构），并落好 Task 1 验收所需的配置。

### 新增文件

**工程骨架**
- `frontend-vue/package.json` — Vue 3 · Vite 6 · TypeScript · Pinia · Vue Router 5，**无任何 @tauri-apps 依赖**（与 LingChat package.json 对齐后剔除全部 Tauri 项）
- `frontend-vue/index.html`、`vite.config.ts`（含 `/api` → 127.0.0.1:8000 代理）、`tsconfig.json`、`env.d.ts`、`.gitignore`
- `frontend-vue/src/main.ts`、`style.css`（Tailwind v4 入口）、`App.vue`（挂载后探测后端 health）

**docs/13 §6 结构**
- `src/app/router/index.ts` — Title / Game / Load / Settings 四路由
- `src/app/bootstrap/index.ts` — 占位
- `src/api/game.ts`（health probe + createOpening）、`saves.ts`（存档契约类型）、`assets.ts`（character+emotion→URL）
- `src/adapters/presentation-adapter.ts`、`asset-resolver.ts`、`lingchat-compat.ts`
- `src/stores/game.ts`、`presentation.ts`、`saves.ts`、`settings.ts`、`ui.ts`
- `src/views/TitleView.vue`、`GameView.vue`、`LoadView.vue`、`SettingsView.vue`
- `src/components/{game/standard,title,save,system}/README.md`、`src/assets/README.md`（占位，Task 2/5/7 填充）
- `frontend-vue/README.md`、`Dockerfile`、`nginx.conf`（静态服务 + /api 反向代理）、`.gitignore`

**可运行配置**
- `frontend-vue/Dockerfile`（node build → nginx serve）+ `nginx.conf`（/api 反代 backend）
- 根 `docker-compose.yml`（frontend-vue:8080→80；backend/postgres 待 Task 6 接入）
- `.claude/launch.json` 增 `gal-vue-vite` 配置（5173）

**后端最小改动**
- `backend/app/main.py`：新增 `GET /api/health`（`{"status":"ok"}`，不触任何游戏运行时状态），供 Vue liveness 探测。

### 关键依赖版本（对齐 LingChat 同 major）

vue ^3.5.13、pinia ^3.0.4、vite ^6.0.3、@vitejs/plugin-vue ^5.2.1、vue-tsc ^2.1.10、tailwindcss ^4.3.0、@tailwindcss/vite ^4.3.0、typescript ~5.6.2。

**vue-router 固定 5.0.6 而非 ^5.0.6**：`^5.0.6` 会解析到 5.1.0+，其 vite peer 要求 `^7.0.0 || ^8.0.0`，与本项目 vite 6 冲突（实测 ERESOLVE）；`5.0.6` 无 vite peer 要求，与 vite 6 兼容，且正是 LingChat 的 `^5.0.6` 实际锁到的 5.0.x。

---

## 2. 为什么这样改

- docs/13 Task 1 要求「初始版本优先采用与 LingChat 兼容的同 major 依赖，避免一开始就同时做框架升级」→ 依赖版本直接取自 2026-08-19 抓取的 LingChat `package.json`，剔除全部 `@tauri-apps/*`。
- docs/13 §6 明确目标目录结构（api/adapters/stores/components/views/types/assets）与「UI 组件禁止散落 fetch('/api/...')」→ 统一经 `src/api/`；本 Task 已按该结构落地。
- 验收「Vue 可请求 FastAPI health」→ 后端当前无 health 端点，故新增最小 `GET /api/health`。
- 验收「无 Tauri 依赖」→ 依赖清单与源码均无 Tauri 引用；`lingchat-compat`/`asset-resolver` 为后续 Task 3 去 Tauri 预置，但当前不引入任何 Tauri 能力。
- `vite server.proxy` 让 dev 期 Vue 与后端同源请求 `/api`，符合 docs/13 §8.2「Adapter 层统一封装」的端到端意图。

---

## 3. 运行了哪些测试 / 验证

| 项目 | 命令 | 结果 |
|---|---|---|
| 前端类型检查 + 构建 | `npm run build`（= vue-tsc --noEmit + vite build） | ✅ 94 模块，dist/ 产出（JS gzip 57.8 kB） |
| 依赖审计 | `npm install` | ✅ 138 包，0 漏洞 |
| 后端全量（health 改动后） | `pytest -q` | ✅ 338 passed |
| 后端 health 直连 | `curl 127.0.0.1:8000/api/health` | ✅ `{"status":"ok","service":"gal-backend"}` |
| Vite 代理 health | `curl localhost:5173/api/health` | ✅ 同 ok |
| 浏览器渲染（headless Chrome） | `verify-vue.mjs` | ✅ 页面渲染、4 菜单项、`后端已连接`、**无 Tauri 引用** |
| 截图 | `TASK1_VUE_TITLE.jpg` | ✅ JPEG 有效（SOI/EOI OK） |

---

## 4. 验收对照（docs/13 Task 1）

| 验收项 | 结果 |
|---|---|
| Docker Compose 可启动 Vue Frontend | ⚠️ 本机无 Docker，未实跑；已提供 `docker-compose.yml` + `Dockerfile`/`nginx.conf`，并以 vite dev server（等价前端服务）实跑通过 |
| 浏览器可访问 | ✅ localhost:5173 HTTP 200，TitleView 渲染 |
| Vue 可请求 FastAPI health | ✅ `/api/health` 经 vite 代理返回 ok |
| 无 Tauri 依赖 | ✅ package.json 无 @tauri-apps，源码无 Tauri 引用 |

**结论：PASS_WITH_LIMITATION**（唯一未实跑项是 Docker Compose，因环境缺 Docker）。

---

## 5. 已知限制 / 需用户决策

1. **Docker Compose 未实跑**：本机未安装 Docker（`docker --version` 无命令）。已提供完整配置（`Dockerfile`、`nginx.conf`、根 `docker-compose.yml`），需在有 Docker 的环境执行 `docker compose up --build` 验证。若你希望在本机装 Docker/WSL2 再验，可后续补。
2. **vue-router 锁定 5.0.6**：因 vite 6 兼容性。若后续升 vite 到 7/8，可同步放开 vue-router 到 ^5。
3. **TitleView / GameView / LoadView / SettingsView 为 Task 1 骨架**：菜单项「开始游戏」已接 `startNewSession`（调 /api/chat/opening）并跳转 GameView；「继续/读取」逻辑、真实存档、设置持久化待 Task 5/7 接入。当前 Title 视觉为目标风格的简化版，非最终（Task 5 基于 LingChat MainMenu 视觉层重建）。
4. **Task 3 去 Tauri** 在 Task 1 已无 Tauri 依赖（骨架天然无）；Task 2 迁入 LingChat 组件后需再次确认无 Tauri 泄漏。

---

## 6. 是否建议 commit

**建议**：单独 commit（scope `docs13`，`feat(docs13): task1 vue3 frontend skeleton`）。内容：`frontend-vue/` 全套 + 根 `docker-compose.yml` + `backend/app/main.py` health 端点 + `.claude/launch.json` + `validation-results/docs13-task1/`（result.md、verify-vue.mjs、截图）。

> 按 docs/13 §34/§35：Task 1 完成后**只报告结果，不自动进入 Task 2**。等待用户确认后开始 Task 2（迁入 LingChat Standard Game UI）。
