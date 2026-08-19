# frontend-vue — Gal 游戏 Vue 3 表现层

docs/13 定义的正式前端。职责：**Presentation Layer**，不持有 Game Truth；所有剧情 / 状态变化以 Backend（FastAPI Game Orchestrator）为准。

## 技术栈

Vue 3 · Vite 6 · TypeScript · Pinia · TailwindCSS v4 · Vue Router 5 —— 与 LingChat 同 major 依赖（docs/13 Task 1）。

无任何 `@tauri-apps/*` 依赖（docs/13 §8 去 Tauri 化）。

## 结构

```
src/
├── app/          # router + bootstrap
├── api/          # game / saves / assets（UI 禁止散落 fetch）
├── adapters/     # presentation-adapter / asset-resolver / lingchat-compat
├── stores/       # game / presentation / saves / settings / ui（Pinia）
├── components/
│   ├── game/standard/   # Task 2 迁入 LingChat Standard Game UI
│   ├── title/ save/ system/   # Task 5/7 占位
├── views/        # Title / Game / Load / Settings
├── types/        # Presentation State 等
└── assets/       # 本项目自己的资源（不使用 LingChat bundled assets）
```

## 常用命令

```bash
npm install
npm run dev        # vite dev，端口 5173，/api 代理到 127.0.0.1:8000
npm run build      # vue-tsc 类型检查 + vite build
npm run preview    # 预览构建产物
```

Dev 前需先启动后端（`cd ../backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000`）。

## Docker

```bash
cd ..
docker compose up --build    # 需本机装有 Docker；见根 docker-compose.yml
```

## 任务状态（T2review P2-7：校准 docs 漂移）

- [x] docs/13 Task 0-9 全部完成（含 Task 9 视觉回归与 **旧前端 Cutover**——
  本项目无 React，旧前端是 vanilla HTML/JS，现冻结于 frontend-deprecated/）
- [x] docs/14 选项功能 T0-T4 全部完成（OptionsPanel 气泡条 + 出示/推理/
  私审/Recovery/Security Review 全链路，E2E 覆盖）

验证入口：`npm run test:unit` / `test:visual` / `test:e2e`（后端需
`GAL_PROVIDER=mock`；Playwright webServer 自起，默认不复用既有服务）。
