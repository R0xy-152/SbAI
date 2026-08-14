## TV-17

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`) with deterministic Mock provider (script tests are keyless / network-free); static Gal UI (`frontend/`) validated with hand-written DOM-stub tests (no build step). Session persistence via `JsonSessionRepository` (TV-14 fixture).

Goal: 对话输出双模式 (docs/03 §37, docs/01 §4) — 关键剧情节点输出**确定性固定台词**(剧本驱动),其余一律落入 LLM 自由生成(AI 生成)。覆盖两个已确认的场景:(1) 主动开场白(不等玩家输入的第一句);(2) 揭示线索的同一回合念固定承接台词。最小合理改动,不把台词塞进 NarrativeEvent、不让剧本节点改状态。

Design (what was built):

- **独立 Script 层**(`backend/app/script/`, docs/03 §37):
  - `node.py` — `ScriptLine`(dialogue / emotion / animation,与 `CharacterResponse` 对齐)+ `ScriptNode`(node_id / speaker / line / trigger / event_id / repeat_policy)。触发类型 `OPENING`(主动开场,由 `open_turn` 触发)与 `ON_EVENT`(本回合 narrative decision 命中某 `event_id` 时)。
  - `service.py` — `ScriptService`,per-session 已消费集合;`resolve()` 只读匹配不消费、按节点顺序取第一个「未消费 + 条件满足 + speaker==本回合角色」;`consume()` 回合成功后标记;`snapshot()`/`restore()` 供持久化。
  - `fixture.py` — 两句 POC 台词:`SCRIPT_OPENING`(deepseek 主动开场,与 index.html 静态占位一致)、`SCRIPT_ON_CLAUDE_APPEARS`(deepseek,ON_EVENT `EV_POC_CLAUDE_APPEARS`,emotion=annoyed)。**Fixture ≠ Production Content**(docs/06 §10),文案为占位。
- **Orchestrator**(`backend/app/game/orchestrator.py`):构造参数加 `script: ScriptService | None = None`(默认 None,现有直接构造的测试行为不变)。`handle_turn` 在 narrative decision 之后、`runtime.respond` 之前插入分支:命中脚本节点则用固定台词构造 `CharacterResponse`(仍过 Semantic Validation Gate 作 defense-in-depth),否则走原 LLM 路径;`decision.kind=="event"` 时 Event **照常 commit**(剧本只定台词,状态推进仍由 NarrativeEvent 负责);once 节点在回合成功(approved)后 consume,再持久化(validate-before-commit 同样约束剧本表)。新增 `open_turn(session_id)` 主动开场:已消费或 session 已有消息则幂等返回空 dialogue,否则念 `SCRIPT_OPENING`、append 一条 character 消息、consume、持久化,`message_count==0`(开场不算 player turn)。
- **持久化**(`backend/app/persistence/repository.py`):`PersistedSession` 加 `consumed_script_nodes: set[str]`;序列化/反序列化增补该字段,反序列化用 `set(data.get("consumed_script_nodes", []))` 向后兼容旧快照。
- **API**(`backend/app/api/chat.py`):新增 `POST /api/chat/opening`(body `{ session_id: str | None }`),返回现有 `ChatResponse` 结构,dialogue 为空表示「已开场」。
- **装配**(`backend/app/main.py`):`GameOrchestrator(..., script=ScriptService(build_script_nodes()))`。
- **前端**(`frontend/app.js`):新增 `openOpening()`,加载后主动调 opening 端点,非空 dialogue 则 `writeSessionId` / `applyPresentation` / `setSpeaker` / `setCharacter` / `dialogueText`;空则静默保留现状(无后端时 catch 静默,index.html 静态开场白仍在)。

Automated tests:

- 后端 `backend/tests/test_script_runtime.py` — **4 passed**:开场固定台词且只念一次(幂等);ON_EVENT 当回合念固定承接台词且 flag `claude_has_appeared` + `SHOW_CHARACTER claude` 仍提交、节点被消费;普通回合未命中脚本仍走 LLM 且不消费;开场后重建 orchestrator(同 repository)不重复念、`consumed_script_nodes` 从快照恢复。
- 前端 `frontend/tests/tv17-script-opening.test.cjs` — **PASS**:加载即调 `POST /api/chat/opening`、渲染返回的开场白、写 `gal_session_id`。
- `node --check frontend/app.js` — PASS。

Regression note (pre-existing, not introduced by TV-17): 全量后端套件 `pytest -q` 为 **226 passed / 5 failed**;前端套件 tv01/tv02/tv14/tv17 PASS,tv03/tv16 FAIL。经归因,这 7 个失败全部来自本任务之前的**并发 Presence Gate 重构**(`availability` → `enforce_presence` 参数改名、co-presence audibility 默认 `present=["deepseek"]`)与 character 切换按钮移除(不再发送 `character_id`),使既有测试 stale —— 与 TV-17 的 `script` 参数(默认 None)及前端新增的 `openOpening()`(实验中确认其不干扰既有测试的 fetch 捕获)无关。这些失败归属 Presence Gate / 前端角色切换的重构收尾,不在 TV-17 范围。

Failures: None in the TV-17 scope (script runtime + opening frontend tests all PASS).

Known limitations:

- 剧本节点 `speaker` 必须等于本回合解析出的 `character_id` 才命中,不一致则跳过走 LLM(不引入「剧本指定他人发言」,也绝不绕过 Presence Gate)。
- POC 台词为占位 fixture(最终文案由内容方提供);当前只支持 `OPENING` / `ON_EVENT` 两类触发。
- 全量测试套件的 7 个 pre-existing 失败(见上)需由 Presence Gate / 角色切换重构另行收尾。

Evidence: `backend/tests/test_script_runtime.py`, `frontend/tests/tv17-script-opening.test.cjs`, `backend/app/script/`(node.py / service.py / fixture.py)。

Conclusion: PASS — 对话双模式以最小改动落地:关键剧情节点走确定性固定台词(主动开场 + 线索当回合承接),其余走 LLM;剧本节点只定台词、状态仍由 NarrativeEvent 推进;开场幂等且可跨刷新恢复。TV-17 范围内的自动化测试全部通过。
