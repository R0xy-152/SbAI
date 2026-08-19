# docs/13 Task 8 — 接入 Auto Save（checkpoint 自动存档）

**状态：PASS**
**日期：2026-08-19**
**范围：** docs/13 Task 8（§21 Auto Save）：4 个稳定 checkpoint（Opening Complete / Claude Appeared / INF01 Confirmed / INF03 Confirmed + Recovery Entry）在 Narrative commit 后作为 side effect 自动写入单一 AUTO slot，前端只附带匿名 `player_id`，Backend 是触发方与快照权威方（§14.2 / §21.3）。

## 1. 完成了什么

Auto Save 是 Narrative commit 后的 **side effect**（docs/13 §21.3：commit → checkpoint reached → capture，绝不在保存后再更新），由后端触发，绝不每轮自动存（§21.1）：

- **checkpoint 判定机**（新增 `app/save/checkpoint.py`）：纯函数，只读 `NarrativeState`：
  - `AS_CH1_OPENING_COMPLETE`：会话真正说过 opening 台词（`get_history` 非空，opening 是 scripted beat，先于任何 flag/phase 变化，故由 history 派生，而非 state）。
  - `AS_CH1_CLAUDE_APPEARED`：`"claude" in chapter1.available_characters`。
  - `AS_CH1_INF01_CONFIRMED`：`INF01_CURRENT_DEEPSEEK_NOT_0317_ACTOR` 在 `accepted_inferences`。
  - `AS_CH1_INF03_CONFIRMED` + `AS_CH1_RECOVERY_ENTRY`：`chapter1.phase == "recovery_required"`。
  - `pending_checkpoints` = reached − 已捕获（捕获记录为 `narrative_flags` 中的 `AS_CH1_*`，随快照持久化 → 同一会话后续 commit 绝不重复捕获，§21.2 once-per-session）。
- **side effect 接线**：
  - `GameOrchestrator` 新增 `save_service` 注入 + `_player_by_session`（session→player 绑定，`_bind_player` 在 chat / opening / deduction 三个端点 thread `player_id`）；`auto_save_if_reached` 在**每次会话持久化之后**调用（handle_turn / open_turn / submit_deduction 各一处），防御性 try/except（side effect 失败不 crash 游戏回合）。
  - `SaveSnapshotService` 新增 `save_auto` / `auto_save_pending` / `_mark_checkpoints` / `_session_opened`。**§21.3 顺序修正**：`save_auto` 先 `_mark_checkpoints`（把本次捕获的 flag 落进会话快照并 re-persist）再 capture AUTO snapshot——保证 AUTO 存档自身携带刚捕获的 checkpoint flag，恢复后的会话不会重复捕获。
  - `main.py` 绑定 `orchestrator._save_service`（修复了此前 `orchestrator.save_service` 赋值到不存在的公开属性、导致生产路径 `_save_service` 恒 None 的接线 bug）。
  - API 层：`ChatRequest` / `OpeningRequest` / `DeductionRequest` 新增 `player_id` 字段并透传；`frontend-vue/api/game.ts` 的 `createOpening` / `sendChat` / 新增 `submitDeduction` 附带 `getPlayerId()`。
- **Frontend 零改动**：SavePanel / LoadPanel 挂载时 `refresh()` 自动展示最新 AUTO（Task 7 已做）；无 streaming 中间态风险，因为 AUTO 只在 commit 后捕获。

## 2. 修改了哪些文件

- 新增：`backend/app/save/checkpoint.py`、`backend/tests/test_checkpoint.py`
- 修改：`backend/app/save/service.py`、`backend/app/game/orchestrator.py`、`backend/app/main.py`、`backend/app/api/chat.py`、`backend/app/api/game.py`、`backend/tests/test_save_service.py`、`backend/tests/test_save_api.py`、`frontend-vue/src/api/game.ts`
- 验证记录：`validation-results/docs13-task8/result.md`

## 3. 如何验证

```bash
cd /d/gal/backend && .venv/Scripts/python -m pytest -q          # 369 passed, 12 skipped
cd /d/gal/frontend-vue && npm run typecheck                     # PASS
cd /d/gal/frontend-vue && npm run build                         # vue-tsc + vite build PASS
```

新增测试（`test_checkpoint.py` 6 条 + `test_save_service.py` Task 8 区 5 条 + `test_save_api.py` Task 8 区 2 条 = 13 条，含既有共 31 条 save/checkpoint 测试全绿）：

| 测试 | 断言 |
|---|---|
| `test_fresh_state_reaches_no_checkpoints` | 空状态 0 checkpoint |
| `test_opening_complete_reached_after_first_interaction` | opening 完成派生自 history 而非 state |
| `test_claude_appeared_reached_from_availability` | claude 可交互 → CLAUDE_APPEARED |
| `test_inf01_and_inf03_reached_from_deduction` | INF01（EV04+EV05）→ INF01_CONFIRMED；INF03（EV01+EV06+EV09）→ INF03_CONFIRMED + RECOVERY_ENTRY + phase=recovery_required |
| `test_duplicate_checkpoint_never_returns_pending` | 已捕获不再 pending（§21.2） |
| `test_pending_only_contains_newly_reached` | 只含新增 |
| `test_opening_complete_auto_saves_once` / `test_plain_turn_does_not_auto_save` / `test_claude_appeared_auto_saves_after_0317_turn` / `test_no_player_id_means_no_auto_save` / `test_inf01_and_inf03_auto_save_after_deduction` | service 层：opening 存一次、普通回合不触发、0317 后 AUTO updated_at 移动、无 player_id 不触发、INF01/INF03 在 deduction 后触发且跨角色 Memory 不泄漏（memories keys ≤ {deepseek}） |
| `test_opening_complete_auto_saves_on_opening` / `test_claude_appeared_auto_saves_after_0317` | API 层验收 #1 / #2 |

浏览器端到端（preview_start gal-backend:8000 + gal-vue-vite:5173，GAL_PROVIDER=mock，JSON save 后端），覆盖 docs/13 Task 8 验收流：

| 验收项 | 结果 |
|---|---|
| New Game → opening | AUTO slot 出现（phase=opening），player 命名空间隔离（另一 player 看不到） |
| AUTO snapshot 携带 `AS_CH1_OPENING_COMPLETE` | PASS（`narrative_flags: ['AS_CH1_OPENING_COMPLETE']`） |
| 调查纸条 → 03:17 → Claude 出现 | AUTO updated_at 移动（08:13:35→08:14:27），phase opening→investigation |
| AUTO snapshot 携带 `AS_CH1_CLAUDE_APPEARED` | PASS（`narrative_flags: ['AS_CH1_CLAUDE_APPEARED', 'AS_CH1_OPENING_COMPLETE', 'PRE_0317_WINDOW', 'claude_has_appeared']`） |
| 重启前端 → 继续游戏（Continue） | PASS（恢复为**新** Active Session `a62ac80f` ≠ 原 `3f69fa32`，§19.1） |
| 恢复点为合法 checkpoint | PASS：`available_characters:[claude,deepseek]`、`acquired_evidence:[EV01_NOTE_V03]`、hotspot completed、private_interview_rights:[deepseek]、input_mode=investigation —— 无 streaming 中间态、无半完成 Evidence、无跨角色 Memory 泄漏 |
| 普通回合不触发新 AUTO | PASS（opening 捕获后多次普通对话 updated_at 不动，§21.1） |

## 4. 结果

**PASS。** docs/13 Task 8 验收流完整跑通：Opening Complete / Claude Appeared 两个可达 checkpoint 均在 Narrative commit 后自动写入单一 AUTO slot（updated_at 移动、快照携带捕获 flag、player 命名空间隔离），Continue 恢复到合法 checkpoint（新 Active Session，剧情/证据/角色正确，无 streaming 中间态）。INF01 / INF03 经 service 层测试覆盖（full-HTTP 路径在 mock provider 下无法注入 LLM claim，属既有限制）。后端 369 passed / 12 skipped，前端 typecheck + build 全绿。

## 5. 已知限制

- **调试日志未落 uvicorn 输出**：`logger.info("auto save captured checkpoints …")` 因 uvicorn 默认日志 handler 未 attach 而不可见（功能正常，日志为辅助诊断；不影响验收证据——以落盘 snapshot 为准）。
- **INF01 / INF03 未经浏览器全链路**：第一章调查主线当前无 UI，且 CT01/CT04 claim 只能经 LLM `claim_refs` 落入（mock 产生不了），故 INF 相关 AUTO 以 service 层测试覆盖（真实 `orchestrator.submit_deduction` side-effect 接线）。
- **`test_save_api.py` 的 `GAL_PROVIDER=mock` 依赖 shell 环境干净**：本文件原无 `GAL_PROVIDER` fixture，一旦 shell 带 `DEEPSEEK_API_KEY`（本机确实有），`create_app()` 会走真实 DeepSeek → 网络抖动 → narrative interpreter 降级 noop → 03:17 回合不触发 checkpoint → 测试**偶发失败**（本次修复为 `_app` 内 `monkeypatch.setenv("GAL_PROVIDER","mock")`，遵循 CLAUDE.md fixture 契约）。测试时间也由此从 ~40s 降到 ~5s。
- **`pre_0317_player_turns` 计数语义**：03:17 触发走 A/B（显式提问或计数≥2），"你好"回合计数=1 属预期，下一回合 03:17 触发——验收以「03:17 回合后 AUTO 移动」为准。

## 6. 建议提交

可以提交。后端 + 前端 API 接线 + 测试 + 验证记录，改动自洽：
- 新增：`backend/app/save/checkpoint.py`、`backend/tests/test_checkpoint.py`、`validation-results/docs13-task8/result.md`
- 修改：`backend/app/save/service.py`、`backend/app/game/orchestrator.py`、`backend/app/main.py`、`backend/app/api/{chat,game}.py`、`backend/tests/test_save_{service,api}.py`、`frontend-vue/src/api/game.ts`
- Commit 建议：`feat(docs13-task8): 接入 Auto Save checkpoint 自动存档`

（注：`CLAUDE.md` 有用户/编辑器侧在途修改，与 Task 8 无关，不纳入本提交。）
