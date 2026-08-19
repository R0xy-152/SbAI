# docs/13 Task 5 — 实现 Title Screen

**状态：PASS**
**日期：2026-08-19**
**范围：** docs/13 §12 / Task 5（TitleView：开始游戏 / 继续游戏 / 读取存档 / 设置；替换 LingChat Logo / 素材 / Workshop / Script Editor / Game Mode / Script Mode）

## 1. 完成了什么

基于 Task 1 已有的 TitleView 骨架，实现完整 Title Screen 行为：

- **首次进入落 Title**（非直接落入对话场景）：路由根路径 `/` 为 TitleView，GameView 仅在进入 `/game` 后才渲染对话场景。
- **开始游戏（New Game）**：显式新建会话 —— 清掉 localStorage `gal_session_id` 后 `router.push('/game')`，GameView 走 `createOpening` → Opening 台词打字机（docs/13 §12.2）。不删除旧存档。
- **继续游戏（Continue）**：无任何存档时按钮 `disabled` + 提示「暂无可继续的存档」（docs/13 §12.3：不得创建空 Session 冒充）；`hasAnySave` 由 saves store 计算（Task 6 接入后端后填充）。
- **读取存档 / 设置**：分别路由到 `/load`、`/settings`（Task 7 / 设置面板后续完善）。
- **Back to Title**：GameView 顶部条新增「返回标题」按钮，可正常回到标题（docs/13 Task 5 验收）。
- **视觉与游戏内一致**：标题复用游戏内同一张背景（`/backgroud/background1.png` + 暗化遮罩），临时文字 Logo（docs/13 Task 5 第一轮：无需先生成最终 KV），按钮样式与游戏内 UI 同款（深蓝边框 + 悬停高亮）。
- **resize 不溢出**：按钮固定宽度 + `max-width:80vw` + 文本截断，窄屏（360px 验证）下主菜单不溢出、无横向滚动。

## 2. 修改了哪些文件

- `frontend-vue/src/views/TitleView.vue`（重构）：背景 + 临时 Logo + 四按钮菜单；New Game / Continue 行为；后端连接状态展示。
- `frontend-vue/src/views/GameView.vue`：顶部条新增「返回标题」按钮（`router.push('/')`），并引入 `useRouter`。
- `frontend-vue/src/stores/game.ts`（精简）：移除 `createOpening` / `lastResponse` / `canInput`（Task 4 起 GameView 自持会话生命周期）；保留 `sessionId` / `busy` / `error`。
- `frontend-vue/src/stores/saves.ts`：新增 `hasAnySave`（Continue 可用依据）+ `refresh()`（Task 6 接入后端列表后填充）。
- `validation-results/docs13-task5/verify-task5.mjs`（新增）：headless Chrome CDP 验收脚本（9 项断言）。
- `validation-results/docs13-task5/result.md`（本文件）。

## 3. 如何验证

```bash
cd /d/gal/frontend-vue && npm run build      # vue-tsc + vite build PASS
cd /d/gal/backend && .venv/Scripts/python -m pytest -q   # 338 passed
cd /d/gal && node validation-results/docs13-task5/verify-task5.mjs
```

headless Chrome CDP 实测 9 项断言（后端 8000 + vite 5175，GAL_PROVIDER=mock）：

| 验收项（docs/13 Task 5） | 结果 |
|---|---|
| 首次进入落 Title（非对话场景） | PASS（h1 + 4 按钮，无 #inputMessage） |
| 菜单含 开始/继续/读取/设置 | PASS |
| 无存档时 Continue 禁用 | PASS（disabled + 「暂无可继续的存档」） |
| 背景图加载（与游戏内一致） | PASS（naturalWidth=1672） |
| New Game 创建新 Session + Opening | PASS（新 sid + Opening 台词） |
| Opening 说话者 = DeepSeek | PASS |
| Back to Title 按钮存在 | PASS |
| Back to Title 回到标题 | PASS |
| resize 时主菜单不溢出 | PASS（360×640 无横向滚动/溢出） |

## 4. 结果

**PASS。** 9/9 浏览器断言 + `npm run build`（vue-tsc + vite）通过 + 后端 338 passed 无回归。

## 5. 已知限制

- **Continue 尚未真正加载存档**：Task 6/7 之前后端无 Save API，`hasAnySave` 恒为 false → Continue 恒禁用（符合 docs/13 §12.3「无存档禁用」）。接入后端后把 `refresh()` 改为 fetch 真实存档列表即可。
- **New Game 清 localStorage `gal_session_id`**：符合「显式新建会话」，不删除旧存档（存档在后端，Task 6 起）；但若用户想「继续」一个仅存在于 localStorage 的旧 session（无 Save 快照），Start New Game 会丢弃该引用 —— 与 docs/13 §12.2「不删除旧存档，可直接创建新 Session」一致。
- **Back to Title 后再次 New Game**：会新建全新会话（不保留刚回标题的会话），属预期（开始新游戏语义）。
- **设置页仅文字速度 + 音量滑块**（docs/13 §12.5：音频未接入前不扩张范围）；LoadView 仍是 Task 7 前的骨架。
- 标题 Logo 为临时文字（docs/13 Task 5 第一轮明确不要求最终 KV）。

## 6. 建议提交

可以提交。改动：
- `frontend-vue/src/views/TitleView.vue`、`frontend-vue/src/views/GameView.vue`、`frontend-vue/src/stores/game.ts`、`frontend-vue/src/stores/saves.ts`（业务）
- `validation-results/docs13-task5/*`（验证 + result.md）

（注：`CLAUDE.md` 有用户/编辑器侧的在途修改，与 Task 5 无关，未纳入本提交。）
