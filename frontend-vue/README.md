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

## 任务状态

- [x] Task 1 骨架（本目录即产物）
- [ ] Task 2 迁入 LingChat Standard Game UI
- [ ] Task 3 去 Tauri / LingChat Runtime 依赖
- [ ] Task 4 接入现有 FastAPI Game Runtime
- [ ] Task 5 Title Screen
- [ ] Task 6 Backend Save Snapshot
- [ ] Task 7 Save / Load UI
- [ ] Task 8 Auto Save
- [ ] Task 9 视觉回归与 React Cutover
