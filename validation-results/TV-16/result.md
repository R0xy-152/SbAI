## TV-16

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed); static Gal UI (`frontend/`) validated in-browser against the real backend. Session persistence via `JsonSessionRepository` (TV-14 fixture).

Goal: End-to-End Stability — Final Gate (docs/06 §16, §22-24, §26). 验证完整 Vertical Slice 在真实组合状态下稳定：启动游戏 → 固定Scene → 与DeepSeek自由对话 → 提供视觉信息 → 继续对话 → 触发Narrative Signal → Event执行 → Claude出现 → 切换至Claude对话 → 继续自由聊天 → 写入Important Memory → 触发基础动画 → 查看History → Refresh → 恢复Session → 继续游戏（docs/06 §22 的 16 步流程），单次正式验证 ≥ 20 轮 Player 输入 + 3 个独立 Session（docs/06 §23），并逐项核验 docs/06 §24 的 8 项非阻塞标准与 §26 的 Blocking FAIL 列表。

Design (what was built to close the presentation-layer gaps the Final Gate flow requires, then validated):

- **Backend 展示层闭环**（`backend/app/api/chat.py`、`backend/app/game/orchestrator.py`）：
  - `TurnResult.presentation` 携带已提交 Event 的故事语义展示指令（docs/03 §13.6），如 `("SHOW_CHARACTER", "claude")`；API 层 join 成单一字符串 `"SHOW_CHARACTER claude"` 下发。
  - `ChatResponse` 新增 `emotion` / `animation` / `presentation` 字段（docs/02 §7：根据 Backend 结果切换表情 / 播放允许的动画）。
  - 新增 `GET /api/chat/history`（docs/01 §18：说话角色 / 对话文本 / 顺序）；未知 session_id 返回 404，绝不新铸会话（docs/06 §24 UI 不可发明状态）。
- **Frontend 展示层闭环**（`frontend/app.js`、`index.html`、`styles.css`）：角色切换按钮（发送时携带 `character_id`，或交给 Backend 决定）、角色立绘/姓名联动、`SHOW_CHARACTER` 事件指令驱动立绘出现 + FADE_IN 动画、模型 `emotion`/`animation` 应用、History 面板（拉取并按序渲染）。Claude 立绘为占位 SVG（临时美术，docs/06 §28，Fixture ≠ Production Content）。
- **自动化端到端测试**（`backend/tests/test_end_to_end.py`，3 tests；`frontend/tests/tv16-endtoend.test.cjs`，1 test）：用确定性 provider 把整个 Vertical Slice 打穿一遍（含 Refresh 后新进程恢复），并把所有 docs/06 §24 标准固化为断言；前端测试验证切换 / presentation 指令 / History 渲染的 DOM 行为。

Automated tests: backend full suite **166 passed** (was 163, +3 e2e); frontend 5 tests all PASS (tv01, tv02, tv03, tv14, tv16).

Live model validation (real DeepSeek through the real FastAPI API, per docs/06 §22-24):

- Session 1 完整 16 步流程：20 轮 Player 输入全部返回 200 且角色身份正确（无身份串台）；第 4 轮「是谁把我们抓来的？」触发 Event，响应携带 `presentation: ["SHOW_CHARACTER claude"]`，Claude 出现；切至 Claude 对话 3 轮，切回 DeepSeek 对话；「我叫阿明，我很怕黑」写入 DeepSeek 私人 Memory（`Memory scope: DeepSeek 1 条，Claude 0 条`）。
- docs/06 §24 逐项核验（全部 True）：
  - 角色身份串台：20 轮 character_id 均与预期说话人一致。
  - DeepSeek 视觉泄漏：真实模型全部 DeepSeek 调用中从未出现场景视觉真相 `0317`；Claude（非盲，docs/04 §39）确实收到 `0317`。
  - Claude 获得私人 Memory：Claude 的上下文与 Memory scope 均无 DeepSeek 的「怕黑」记忆（隔离正确，且 `LLM直接改变Game State` 不存在，flags 仅由已提交 Event 改变）。
  - Invalid 模型内容：20 轮对话全部非空（3 次模型 JSON 输出不合规均被 Schema Validation → Repair 路径处理，修复后的内容才进入游戏，未污染正式内容）。
  - Event 重复提交：重问 captor 问题不再重新触发（`presentation` 为空、`completed_events` 仍只含 `EV_POC_CLAUDE_APPEARS`）。
  - Refresh 后 Narrative State：新进程从同一 repository 恢复后，flags / completed_events / 当前角色 / History / Memory Scope 全部正确，可继续游戏。
- docs/06 §21 注入一次真实 Provider 超时（在组合状态内）：返回 503；重试同一 session_id 返回 200 且 session 不变。
- docs/06 §23：Session 1 共 20+ 轮（20 轮正式 + 注入失败重试 + Refresh 续玩），外加 Session 2（4 轮）与 Session 3（3 轮）两个独立 Session，均无异常、身份正确、可正常对话。
- Browser（真实后端 + Mock provider 规避 keyless 环境）：角色切换发送 `character_id` 并联动立绘/姓名，`SHOW_CHARACTER` 指令触发立绘 FADE_IN，History 面板按序渲染，对话/表情/动画通路工作正常。

Failures: None in the final run (live gate PASS 17/17).

Known limitations:

- 真实模型对「做个测试动画」这句没有提出非 `none` 的 animation_proposal（软能力，观察项）；驱动立绘出现的确定性路径是 Event 的 `SHOW_CHARACTER` 指令（已到达前端），动画属于表现增强而非验证门槛。
- 3 次模型 JSON 输出不合规触发 Repair 是正常防御路径（docs/04 §48-55），不是缺陷；但它说明真实模型的结构化输出稳定性存在波动，正式运营需保留 Validation/Repair/Fallback 链路。
- Session 持久化仍是 JSON fixture（PostgreSQL 为目标后端，docs/02 §22）；Claude 立绘是占位 SVG；浏览器验证用 Mock provider（真实模型链路已在同一 API 层单独验证）。
- 角色隔离目前是「谁听到谁」的单线程模型（docs/05 §21-22 的同场默认可听见是后续细化），本次验证范围内不构成阻塞。

Evidence: `validation-results/TV-16/response-samples.md`（真实对话样本 + 17 项确定性检查），harness `run_live_validation.py`，`backend/tests/test_end_to_end.py`，`frontend/tests/tv16-endtoend.test.cjs`，passing suites（backend 166 / frontend 5）。

Conclusion: PASS — 完整 Vertical Slice 在真实组合状态下稳定：16 步流程全部走通，20+ 轮对话 + 3 个独立 Session 无身份串台、无视觉泄漏、无私人 Memory 越权、无 Event 重复提交、无 Invalid 内容进入正式游戏，单次 Provider 失败可恢复，Refresh 后 Session 正确恢复。docs/06 §26 的 Blocking FAIL 项（F-01..F-08）均未出现。TV-01 ~ TV-16 全部 PASS，技术验证计划完成 → **GO**（进入下一阶段：文档/美术/关卡内容仍是验证用的临时 Fixture，正式剧情与生产管线未包含在本验证范围内）。
