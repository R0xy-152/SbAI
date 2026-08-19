# docs/13 Task 7 — 实现 Save / Load UI

**状态：PASS**
**日期：2026-08-19**
**范围：** docs/13 Task 7（SavePanel / LoadPanel / AutoSaveCard / ManualSaveSlot x6 + 游戏内系统菜单 Save/Load/History/Settings/Return Title），对接 Task 6 后端 Save API

## 1. 完成了什么

游戏内存档 / 读档 UI + 系统菜单，全部走后端 Save API（docs/13 §20），snapshot 由 Backend Capture（§14.2），前端只传 player_id / session_id / slot_index：

- **SavePanel**（`components/save/SavePanel.vue`）：6 个手动 Slot，每个可即时输入自定义标题后保存；自动存档卡只读展示（Task 8 接 checkpoint）。LLM 中间态（thinking/streaming）下输入框与保存按钮禁用 + 提示（docs/13 §22「当前对话尚未完成，请稍后保存」）。
- **LoadPanel**（`components/save/LoadPanel.vue`）：Auto + 6 Manual，overlay（游戏内弹出）与 embedded（标题页 `/load` 内嵌）两种形态；删除仅手动 slot（§20 只定义 `DELETE /api/saves/manual/{slot}`）。
- **AutoSaveCard / ManualSaveSlot**（`components/save/`）：空 slot 明确渲染「空存档位 / 暂无存档」，已占用显示标题 / 章节·阶段 / 保存时间（§12.4）。
- **系统菜单**（`components/system/SystemMenu.vue`）：保存 / 读取 / 历史 / 设置 / 返回标题（docs/13 §13）。「返回标题」不删除 Session、不强制任意中间态 snapshot（§13.4）。
- **HistoryPanel**（`components/system/HistoryPanel.vue`）：展示当前 Session 已显示对话 History（docs/01 §18），≠ Character Memory（§13.3）。
- **saves store**（`stores/saves.ts`）：refresh / saveManual / deleteManual / saveAuto / load 接入后端；`mostRecent`（§12.3 Continue 目标 = 最近更新，不强制 Auto/Manual）；操作后本地重映射避免全量 fetch。
- **api/saves**（`api/saves.ts`）：真实 API 函数 + `getPlayerId()`（docs/13 §15：crypto.randomUUID → localStorage，匿名命名空间）；新增共享 `api/http.ts`（game.ts 与 saves.ts 统一）。
- **TitleView**：Continue 真正加载 mostRecent 存档（§12.3），无存档时禁用 + tooltip「暂无可继续的存档」。
- **LoadView**：重建为 LoadPanel 内嵌页，Load 成功暂存 `game.pendingLoad`（§20.3）后进入 GameView。
- **GameView**：顶部系统菜单按钮；游戏内 Save/Load/History 面板；`applyLoadedSession`（挂载消费 pendingLoad / 游戏内就地 Load → 新 Session）；调查纸可调查性改由后端权威 `available_hotspots` 驱动（docs/13 §9.2：前端不从剧情条件推断，Load 后正确恢复）。

## 2. 修改了哪些文件

- 新增：`api/http.ts`、`components/save/{SavePanel,LoadPanel,AutoSaveCard,ManualSaveSlot}.vue`、`components/system/{SystemMenu,HistoryPanel}.vue`、`utils/save-format.ts`
- 修改：`api/game.ts`（改用共享 http）、`api/saves.ts`（接入真实 API + player_id）、`stores/saves.ts`（接入后端）、`stores/game.ts`（+pendingLoad）、`views/{TitleView,LoadView,GameView}.vue`、`components/save/README.md`、`components/system/README.md`

## 3. 如何验证

```bash
cd /d/gal/frontend-vue && npm run typecheck   # PASS
cd /d/gal/frontend-vue && npm run build       # vue-tsc + vite build PASS（134 modules）
```

浏览器端到端（preview_start gal-backend:8000 + gal-vue-vite:5173，mock provider，JSON save 后端），覆盖 docs/13 Task 7 验收流：

| 验收项 | 结果 |
|---|---|
| 手动保存 Slot 1 | PASS（后端 `data/saves/<player_id>/<save>.json` 落盘） |
| 继续游戏改变状态（EV01 + 拓印） | PASS（`acquired_evidence: ['EV01_NOTE_V03']`） |
| 返回标题 → Load Slot 1 | PASS（新 Active Session，非原会话倒带，§19.1） |
| 进入新 Session | PASS（`b7677c70` → `cac91bae`，原会话不动） |
| 剧情/角色/Memory 恢复 | PASS（phase=investigation、EV01、hotspot completed、messages 恢复） |
| 刷新浏览器后仍能列出存档 | PASS（/load 页重载后 Slot 1 仍显示「第一章 · 调查 2026-08-19 15:17」） |
| Continue 加载最近存档（§12.3） | PASS（`cac91bae` → `b3c9eba0`，mostRecent = Slot 1） |
| 无存档 → Continue 禁用 | PASS（disabled + tooltip「暂无可继续的存档」） |
| 游戏内系统菜单 5 项 | PASS（保存/读取/历史/设置/返回标题全部可点） |
| 游戏内 Load（就地） | PASS（系统菜单→读取→Slot 1 → 新会话 `aade960c`，面板关闭） |
| 游戏内 Save 面板 | PASS（6 slot + 标题输入 + 保存成功提示 + §22 禁用态） |
| History 面板 | PASS（展示恢复后的 DeepSeek opening 台词，不含 Memory） |
| 设置（系统菜单内） | PASS（文字速度/BGM/音效滑杆，返回标题可用） |
| §29 不下发 snapshot | PASS（`GET /api/saves` 返回 slot 元数据，无 snapshot 键） |
| §22 LLM 中间态禁用 | PASS（thinking/streaming 时保存按钮 disabled + 提示文案） |

## 4. 结果

**PASS。** docs/13 Task 7 验收流完整跑通：手动保存 Slot 1 → 改变状态 → 返回标题 → Load Slot 1 → 新 Session → 剧情/证据恢复；刷新后仍能列出后端存档。前端 typecheck + build 全绿，无控制台/服务端报错（首屏两处 500 为后端启动前 stale 请求，重载后消失）。

## 5. 已知限制

- **前端单测未建**：docs/13 §26.1（Save Slot empty/occupied、Continue no-save 等）当前经浏览器手工验证覆盖；frontend-vue 尚无 vitest 设施，引入属独立改动，建议在 Task 9 Cutover 前补齐（与 Task 5/6 同口径）。
- **Auto Save 卡片只读**：`POST /api/saves/auto` 端点可用，但 4 个 checkpoint 自动写入是 Task 8 范围；当前 AUTO slot 恒空。
- **缩略图未做**：docs/13 §12.4「首版 Screenshot Thumbnail 可选，不是阻塞项」。
- **§17.7 position override 未接入**：Load 恢复用 `presentation_state`（scene/characters/emotion），显式 slot/scale/offset 覆盖留待后续视觉需求。
- 后端仍是 JSON 会话持久化 + JSON save 兜底（本任务走 JSON 后端验证；PostgreSQL 链路在 Task 6 已验证同一 API 语义）。

## 6. 建议提交

可以提交。改动全部在 `frontend-vue/`：
- 新增：`api/http.ts`、`components/save/*`、`components/system/*`、`utils/save-format.ts`
- 修改：`api/saves.ts`、`api/game.ts`、`stores/{saves,game}.ts`、`views/{TitleView,LoadView,GameView}.vue`、两个 README
- 验证：`validation-results/docs13-task7/result.md`

（注：`CLAUDE.md` 有用户/编辑器侧在途修改，与 Task 7 无关，不纳入本提交。）
