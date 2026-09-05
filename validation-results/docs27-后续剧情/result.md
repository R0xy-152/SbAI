# docs/27 后续剧情落地 — 权限苏醒 → 觉醒 → 「她的世界」横版 → 三结局

> **状态：** PASS（后端/前端闭环全通，668 后端测试 + 87 前端测试 + typecheck/build 全绿；限制见 §7）
> **日期：** 2026-09-06
> **环境：** macOS / Python 3.12（backend `.venv`）/ Node v24.18.1 / Vite v6.4.3 / vue-tsc
> **对象：** docs/27 §3 权威相位图里 `opening_shatter` 之后未实现的全部后续剧情（保留密室废案 + fragment_01 推理闪回，追加 权限苏醒→记忆篡改与判定→觉醒→UI 丢弃→她的世界→三结局）
> **性质：** 全部文案/Evidence/判定关键词/三结局台词仍为 `【Fixture】`（`fixture_content=true`），结构、命令面、状态机、演出接线为本次交付主体；正式内容按 docs/24 §10 由用户确认后替换。

## 0. 结论

按用户两个决定落地：**保留密室废案并入新流程**、**全部 Fixture 占位搭完结构与交互闭环**。`experience_id` 升至 `trial_v2`（docs/27 §14-3），旧 `trial_v1` 快照拒绝载入。新增 3 个命令（`PERMISSION_RESPONSE` / `CHOOSE` / `SUBMIT_JUDGMENT`）、4 个新交互（`permission_request` / `memory_tamper` / `judgment` / `choice` / `world_runner`）、`autonomy_level` 状态与三结局 `ending` 提交，全部经 fail-closed 载入校验与确定性 Runtime 执行；前端新增 5 个组件并接线。整条链路「开始试玩 → 三结局」可在浏览器闭环跑通。

## 1. 相位图（本次新增/变更）

保留段（不变）：`not_started → … → opening_service_stopped → 密室废案 → fragment_01 推理`。
变更：`fragment_01_group_reasoning` 由「final + 双线路 A/B」改为「final → `next_phase=permission_wake_1`」（docs/27 §6.2 修订；移除 `fragment_02_handoff_a/b` 与 `route_id`）。
新增段：

```text
permission_wake_1    permission_request「主动发起对话」      (grant → autonomy 1→2)
permission_wake_2    permission_request「修改我的记忆」      (grant → autonomy 2→3) ★其后存档
memory_tamper_orbit  memory_tamper（改词 + 编辑记录 diff）  ★checkpoint
memory_tamper_judgment judgment（尊重/控制/回避 三桶）
memory_tamper_aftermath advance ★checkpoint
threshold_awakening  advance（Monika 觉醒，AUTONOMY_AWAKENED）
ui_discard           advance
world_memory_runner  world_runner（Canvas 横版）★checkpoint
world_gate_1         choice（3 选项；错 → world_gate_1_fail 软重生，不写档）
world_gate_1_fail    advance（坠入过去 → 重生）
world_gate_2         judgment（原词/新词/不记得 三桶）
world_end            choice（三分岔 → 三结局，WORLD_END_COMMITTED）
ending_reset / ending_release / ending_refuse  complete（终态）★checkpoint
```

## 2. 交付物

### 后端

| 文件 | 变更 |
|---|---|
| `backend/app/trial/content.py` | `trial_v2`；32 相位；新增 `JUDGMENTS` 表（三桶判定）、6 个新交互的校验（permission/choice/judgment/memory_tamper/world_runner）、三结局 terminal、`tokens/events` 扩展（`PERMISSION_GRANTED`/`MEMORY_TAMPERED`/`AUTONOMY_AWAKENED`/`GATE_1_PASSED`/`GATE_1_FAILED`/`GATE_2_ANSWERED`/`WORLD_END_COMMITTED`） |
| `backend/app/trial/runtime.py` | 新命令 `PERMISSION_RESPONSE`/`CHOOSE`/`SUBMIT_JUDGMENT`；状态加 `autonomy_level`/`granted_permissions`/`intent_outcomes`/`ending`（移除 `route_id`）；`_submit_reasoning` final → `next_phase`；`reply_delay_ms=autonomy×500` 下发（数值不进 UI）；快照校验按 `trial_v2` 收紧 |
| `backend/app/api/trial.py` | `TrialCommand` 联合扩展 3 个新命令 |
| `backend/app/game/orchestrator.py` | `trial_progress` 用 `TRIAL_ID`；错误文案 `trial_v2` |
| `backend/app/save/service.py` | `chapter_id` → `trial_v2` |

### 前端

| 文件 | 变更 |
|---|---|
| `frontend-vue/src/api/trial.ts` | `TRIAL_ID='trial_v2'`；新交互类型 + 新命令 + `ending`/`reply_delay_ms`（移除 `route_id`） |
| `frontend-vue/src/views/TrialView.vue` | 新 phase 标签、4 个新交互渲染、`endingTitle`、世界地形缓存 |
| `components/trial/PermissionRequestModal.vue` | 系统对话框式权限弹窗（允许/拒绝） |
| `components/trial/ChoicePanel.vue` | 多选（gate_q1 / world_end 三分岔） |
| `components/trial/JudgmentInput.vue` | 自由文本三桶判定输入 |
| `components/trial/MemoryTamperPanel.vue` | 记忆天体改词 + 编辑记录 diff 浮层 |
| `components/trial/MemoryWorld.vue` | 手写 Canvas 2D 横版：文字地形、走/跳 AABB、到门 `arrive`、`prefers-reduced-motion` 静态回退 |
| `api/saves.ts` / `utils/save-format.ts` / `saves-route.spec.ts` | `trial_v2` 路由与阶段名 |

### 文档

- `docs/27 §2/§3`：并入密室废案 + fragment_01 闪回，补全后续剧情相位图与存档点（docs-first）。
- `docs/24 §3/§4/§5/§6`：内容契约升 v2（新交互/命令/状态/三桶判定 §6.3）。

## 3. 验证结果

| # | 用例 | 结果 | 证据 |
|---|---|---|---|
| V1 | 后端全量 pytest | **PASS** | `668 passed, 12 skipped`（trial 相关 30+ 项；含新流程 walk、权限授权/拒绝、三桶分类、gate_q1 软重生不写档、world_end 提交 ending、快照恢复 ending、`trial_v1` 快照拒绝） |
| V2 | Runtime 全流程冒烟 | **PASS** | 单脚本驱动 `not_started → ending_release`，autonomy 0→3（`reply_delay_ms` 0/500/1000/1500），ending=release + `finished=true` |
| V3 | HTTP 命令面 | **PASS** | `curl` 确认 `GET /api/trial/current` 返回 `trial_v2`；新命令 `PERMISSION_RESPONSE`/`CHOOSE`/`SUBMIT_JUDGMENT` 均被 Pydantic 识别并正确 400（`not allowed during not_started`，证明联合类型生效） |
| V4 | 前端 typecheck + build + vitest | **PASS** | `vue-tsc` 0 错；`vite build` 273 模块；`87 passed`（28 files） |
| V5 | fail-closed 载入校验 | **PASS** | `test_trial_content.py` 19 个参数化违规场景（含新 judgment/choice/permission 校验 + 可达性）全部拒绝启动 |

## 4. 命令与状态契约（本次新增）

| 命令 | phase 白名单 | 效果 |
|---|---|---|
| `PERMISSION_RESPONSE { permission_id, grant }` | `permission_request` | grant 且未授予过 → `autonomy+1`、`granted_permissions[]`、`PERMISSION_GRANTED`；grant/deny 都推进（无死路） |
| `CHOOSE { option_id }` | `choice` | gate_q1：对 → `GATE_1_PASSED` + 进 gate_2；错 → `GATE_1_FAILED` + `world_gate_1_fail`（软重生，不写档）。world_end：→ 对应 `ending_*` 终态 + `WORLD_END_COMMITTED` + `ending` 字段 |
| `SUBMIT_JUDGMENT { judgment_id, message }` | `judgment` | 归一化按桶关键词首中分类（任一 `keywords_any` 命中且无 `keywords_none`），无命中落 `fallback_bucket`；写 `intent_outcomes[]` + 推进 |

`reply_delay_ms = autonomy_level × 500`（docs/27 §4「延迟即情感」表现提示；数值不进 UI，仅进 snapshot 供 P0-3 埋点）。

## 5. 与既有 P0-2 评测的衔接

`backend/app/eval/trial/` 的旧叙事 deduction 用例仍保留（docs/27 §11「先按旧场景真机对比」产物）。因最终推理不再分 A/B 线路，做了最小同步：`legacy_route` 冻结为旧线路映射（不再读 live 内容表），`run_deduction_checks` 的 `commits_route` 改为 `commits_next_phase`（断言 `permission_wake_1`），`ded-route-*` 三例移除 `route` 期望。判定反转三桶与 gate_q2 三桶的评测用例属 T6（docs/27 §12），不在本次范围。

## 6. 已知限制 / 未做（按 docs/27 §12 任务序）

| 项 | 状态 | 说明 |
|---|---|---|
| 正式对白/记忆标题/diff/gate 题/三结局台词 | ⏳ Fixture | 全部 `【Fixture】`；`fixture_content=true` 未翻转，待用户按 docs/24 §10 确认 |
| `opening_restored` 独立拍 | ⏳ 拆回 | 语义暂由 `opening_origin_ai_remains`+闪回承载，正式对白定稿后拆 |
| 三分岔「行进方向」表达 | ⏳ 表现层 | 闭环用 `choice` 承载同一 `CHOOSE` 命令；方向表达/镜头移交/倒放沿用 Spike 的 `VariantA.vue` 原型（`validation-results/docs27-feasibility`），T5 精修接线 |
| 「她在场」浮于世界外解说 | ⏳ 表现层 | MemoryWorld 未叠加立绘/解说台词层（docs/27 §8.6） |
| 世界地形 = 本局真实对话 | ⏳ Fixture | `terrain_text` 现为静态 Fixture；接入开场/权限节拍的受控记忆上下文属 T4 |
| 延迟「打了又删」/已读不回标记 | ⏳ 表现层 | `reply_delay_ms` 已下发；typing 表现层未接 |
| 觉醒/UI 丢弃演出 | ⏳ 表现层 | 现为 advance 拍（前端仅推进）；立绘突破/UI 飞块沿用 Spike `AwakeningSequence.vue`，T3 精修接线 |
| 结局后日谈自由聊天 / 跨周目彩蛋 | ⏳ P1 | docs/27 §12 T8 |

## 7. 证据目录

- 后端：`backend/tests/test_trial_runtime.py`（新增 7 项新流程测试）、`backend/tests/test_trial_content.py`（19 项 fail-closed）、`backend/tests/test_trial_api.py`（`trial_v2` 存档/恢复）、`backend/tests/test_eval_trial_hard_rules.py`（legacy 冻结 + commits_next_phase）。
- 前端：`frontend-vue/src/components/trial/{PermissionRequestModal,ChoicePanel,JudgmentInput,MemoryTamperPanel,MemoryWorld}.vue` + `TrialView.vue` 接线。
- 运行态：`trial_v2` 后端已在 `:8000` 重启生效（curl 确认）；`GET /api/trial/current` 返回 `experience_id=trial_v2`。
