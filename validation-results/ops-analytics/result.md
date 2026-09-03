# ops-analytics — 玩家反馈分析与运营监控闭环（P1 主线，docs/21）

- 状态：PASS
- 日期：2026-09-04
- 环境：本地（pytest 全量；GAL_PROVIDER=mock、内存 recorder/store）
- 方案：`docs/21-运营监控与反馈分析落地方案.md`

## 范围

在不动剧情、不加玩家可见功能的前提下，落地「埋点 → 看板 → 反馈分类 → 人工抽检」闭环：

1. **事件埋点（7 个点位）**：序章开始 / 探班选择 / 角色篇完成 / 序章选项 / 序章完成 / 进入 AI 对话 / AI 请求失败，外加校验拦截与 Presence Gate 拦截。
2. **指标采集**：每次 AI 回合的延迟与 token 用量经 `LLMProvider.complete(metrics=...)` 出参累加（含修复重试与 thinking 降级重试），落 `chat_metrics` 表并计算成本（占位价格可经环境变量覆盖）。
3. **看板**：`GET /ops` 单文件页面 + `/api/ops/funnel|preferences|ai|events` 四端点（GAL_OPS_TOKEN 门禁），漏斗/角色偏好/成功率/P50/P95/成本/拦截分布。
4. **反馈分类**：DeepSeek 结构化输出分类（去重/主题/严重度/场景），原始留言与模型原始输出全部保留；失败行 status=failed 不重试。
5. **人工抽检**：`/api/ops/feedback/annotate` + Precision（topic/severity 分字段）。

## 变更文件

- 新增：`backend/app/ops/`（events / aggregate / feedback / dashboard / page / cli）、`docs/21`、4 个测试文件。
- 修改：`providers/{base,deepseek,mock,anthropic}.py`（metrics 出参 + supports_metrics 能力）、`characters/base.py`（CharacterRequest.metrics 透传）、`game/orchestrator.py`（ops 可选参数 + 埋点）、`api/chat.py`（失败事件）、`main.py`（装配）。
- 兼容性设计：metrics 只在 Provider 声明 `supports_metrics` 时透传；`respond` 签名不变；`ops` 为可选构造参数——既有测试零改动通过。

## 验证

- 后端全量：**581 passed, 12 skipped**（新增 23 项 ops 测试：事件序列、指标落库、漏斗/偏好/AI 聚合口径、门禁 401/503、分类去重/失败隔离、Precision）。
- 事件序列（test_ops_instrumentation）：序章走完全程产生 prologue_start×1、choice×4、visit_chosen×3（order 1..3）、visit_completed×3、completed×1；首轮 AI 对话产生 ai_chat_enter（每会话一次）+ ai_chat_turn + chat_metrics 行（provider/latency/token/cost 正确）；错角色回复触发 validation_reject（gate=deterministic）并回落安全台词。
- 看板聚合（test_ops_dashboard）：3 会话种子数据 → 漏斗 3/3/2/1/1/1，最远阶段分布 {ai_chat_entered:1, visit_chosen:1, visit_completed:1}，角色完成率 deepseek 2/3、chatgpt 1.0、claude 0.5；P50=100ms、P95=300ms。
- 修复过程中发现并修正的缺陷：漏斗「阶段到达数」初始实现累加方向反了（在最远阶段之后累加而非之前），已在聚合单测覆盖下修正。

## 已知限制

- 事件/指标为事后记录副作用，写失败只记日志（与 Auto Save 同约定）。
- 尚未部署：线上仍是 4e85c86，本方案随 P1 部署才生效（见 deploy 计划）。
- 分类器与生成同模型（DeepSeek），人工抽检是当前唯一独立评判；抽检集以实际留言量为准（目标 ≤50 全量）。
- 成本价格为占位口径（token 原始数已落库可重算）；P50/P95 样本小时仅为管线演示。
