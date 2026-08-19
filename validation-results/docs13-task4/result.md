# docs/13 Task 4 — 接入现有 FastAPI Game Runtime

**状态：PASS**
**日期：2026-08-19**
**范围：** docs/13 §27 Task 4（New Session / Player Input / Streaming / Response / Presentation Directive / Character Presence / Emotion / Narrative Event；Opening → DeepSeek 对话 → 03:17 → Claude 出现 → Claude 可对话）

## 1. 完成了什么

将 `frontend-vue` 的 GameView 从「演示用前端内建状态」切换为**消费现有 FastAPI Game Runtime 的真实会话**。前端只做表现，所有剧情/在场/表情/事件推进均来自 Backend（docs/13 §9.2）。

- **New Session**：`createOpening`（GET /api/opening）铸造 session_id，存 localStorage `gal_session_id`；Opening 台词打字机播放，DeepSeek 单立绘在场，玩家点击推进后解锁输入。
- **Player Input → Response**：`sendChat` POST /api/chat（携带 character_id 显式选角）；回复经 `applyChatResponse` 落到 Store，结构化 `presentation_actions` 优先、legacy `presentation` 字符串回退（docs/13 §10 Adapter 归一）。
- **Presentation Directive / Emotion**：Adapter 处理全部 9 种白名单 Action（CHARACTER_SHOW/HIDE/EMOTION/ANIMATION/BACKGROUND_* /SCREEN_SHAKE/SCREEN_GLITCH/INPUT_*），未知 Action 拒绝执行并 `console.warn`（docs/12 §13）。
- **Character Presence**：角色在场**不**由前端剧情条件推断，由 Backend `presentation_state` 权威对账 —— `applyPresentationStateView` 按 `view.characters` 重建在场名单，不在列表即退场（fail-closed）。
- **Narrative Event → 03:17 → Claude**：调查纸入口（INSPECT → PAPER_RUBBING_COMPLETE → EV01 线索「03:17 的笔记」）→ 与 DeepSeek 对话触发 `CH01_INCIDENT_0317` 脚本序列（SCREEN_GLITCH → SYS 警告 → SCREEN_SHAKE → Claude 登场「比上一次慢。」→ DeepSeek 反应）→ `unlock claude` 使 Claude 立即可对话。
- **Script Sequence**：多行剧本演出（`script_sequence`）由 GameView 逐行打字机播放，玩家点击推进，播完解锁输入（LingChat 交互契约 `dialog-proceed`）。
- **Session restore**：页面刷新后从 localStorage 恢复 session_id → `reconcileStage`（fetchGameState）对账权威在场 + `fetchHistory` 恢复最后一句台词；Claude 在场/最后台词在刷新后保持。

## 2. 修改了哪些文件

- `frontend-vue/src/api/game.ts`（重写）：`PresentationAction` / `ChatResponse`（含 `script_sequence`）/ `PresentationStateView` 接口；`sendChat`（POST /api/chat）、`sendInvestigationAction`（POST /api/game/action）、`fetchGameState`（GET /api/game/state）、`fetchHistory`（GET /api/chat/history）。
- `frontend-vue/src/adapters/presentation-adapter.ts`（重写）：`applyPresentationAction`（9 种白名单 Action → Store）、`applyPresentationStateView`（权威在场对账）、`applyChatResponse`（说话者/表情/动画/台词 + presentedCharacter）、`setDialogueLine`、`setInputStatus`。自动站位 `(i+1)/(n+1)` + SLOT_PCT 显式 slot 覆盖（docs/12 §10.1）。
- `frontend-vue/src/views/GameView.vue`（重写）：会话生命周期（Opening / 恢复 / 玩家发送 / 剧本序列播放 / 调查纸 / 角色切换器 / 顶部会话信息）。
- `frontend-vue/vite.config.ts`：去掉硬编码 `port: 5173`（改由 launch.json `autoPort` 分配，避免与本机其他会话端口冲突）。
- `.claude/launch.json`：gal-vue-vite 加 `"autoPort": true`。
- `validation-results/docs13-task4/verify-task4.mjs`（新增）：完整浏览器验收脚本（headless Chrome CDP，15 项断言）。
- `validation-results/docs13-task4/result.md`（本文件）。
- 后端**零改动**（chat.py / game.py / orchestrator.py / investigation.py / presentation / script / speaker_selector 均已就绪）。

## 3. 如何验证

```bash
# 后端全量（fixture 固定 mock，无需 API key/网络）
cd /d/gal/backend && .venv/Scripts/python -m pytest -q          # 338 passed

# 前端类型 + 构建
cd /d/gal/frontend-vue && npm run build                          # vue-tsc + vite build PASS

# 浏览器端到端（后端 8000 + vite 5175，GAL_PROVIDER=mock）
node validation-results/docs13-task4/verify-task4.mjs            # 15/15 PASS
```

headless Chrome CDP 实测 15 项断言：

| 验收项（docs/13 §27） | 结果 |
|---|---|
| New Session mints session_id | PASS |
| Opening line displayed | PASS（「……你醒了。别怕，我们先弄清…」） |
| Opening speaker = DeepSeek | PASS |
| DeepSeek sprite loaded | PASS（1024×1024） |
| Background loaded | PASS |
| Player message sent → response received | PASS（DeepSeek「我是De…」） |
| Investigation entry（调查纸 EV01） | PASS |
| 03:17 → Claude appears（speaker） | PASS |
| Claude speaks（「比上一次慢。」固定句） | PASS |
| Claude interactable（玩家可对话 Claude） | PASS（「我能确认门在 03:17…」） |
| Narrative Event committed（backend state 有 claude） | PASS |
| Claude line in session history | PASS |
| Refresh restores same session_id | PASS |
| Refresh restores Claude on stage | PASS |
| Refresh restores last dialogue | PASS（Claude 最后台词） |

## 4. 结果

**PASS。** 15/15 浏览器断言 + 338/338 后端测试 + vue-tsc/vite build 全绿。

验收标准对照（docs/13 §27）：

- 不使用 Mock Provider state 伪装 Game State —— Backend 全部真实链路（orchestrator → speaker_selector → provider）✓
- LLM 不直接控制 Vue —— 只经 `presentation_actions` / `script_sequence` / `presentation_state` ✓
- Vue refresh 后 Session restore —— 同 session_id + Claude 在场 + 最后台词恢复 ✓
- 角色知识隔离 tests 不回归 —— `pytest 338 passed`（含 test_character_isolation / test_chapter1_claude_truth）✓
- 第一章 Gate 仍由 Backend 决定 —— `unlock claude` 走 Narrative Gate，前端角色切换器只是显式选角 ✓

## 5. 已知限制

- 仓库只有一张背景图（background1.png），Adapter 将 scene 恒映射到该图；多房间背景素材待美术补充（docs/12 表情差分同理，`data-emotion` 先映射高亮/滤镜）。
- mock provider 下 speaker_selector 恒返回 deepseek；对话 Claude 需经前端角色切换器显式选角，Availability 由后端 Presence Gate 把关。真实 DeepSeek 下 Claude 可经 speaker_selector 自行选中。
- 前端角色切换器会列出全部 4 个角色按钮（含未登场角色），但真正可对话性由后端 availability 决定（已存在事件即满足）。若需更严格的门控，可在 UI 层读取 availability 后禁用按钮 —— 属后续 Task 打磨，当前行为不违反 docs/13 §27。
- 03:17 触发依赖「调查纸 EV01」+「提到 03:17」两步；纯计数兜底（不问也触发）由后端 `pre_0317_player_turns >= 2` 条件负责，浏览器脚本未覆盖该分支（后端单测已覆盖）。
- `console.warn` 的未知 Action 拒绝日志无 UI 展示（仅 console），当前无未知 Action 产生。

## 6. 建议提交

可以提交。改动分三类：
- 业务：`frontend-vue/src/api/game.ts`、`frontend-vue/src/adapters/presentation-adapter.ts`、`frontend-vue/src/views/GameView.vue`
- 配置：`frontend-vue/vite.config.ts`、`.claude/launch.json`
- 验证：`validation-results/docs13-task4/*`
