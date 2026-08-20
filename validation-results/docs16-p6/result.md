# docs16-p6 · 台词按换行分段逐段播放 — 验证结果

> **状态：PASS**
> **日期：2026-08-23** · **环境：** frontend-vue；backend 未改动。
> **依据：** docs/16 P6（docs/16-玩家体验修复与开局选项窗口落地方案.md §2）。

## 1. 目标

台词支持分段输出：按换行切成多段，点继续逐段替换式播放，最后一段播完后解锁
输入（为 P7/P8「点继续→弹选项窗口」打底）。

## 2. 改动

- views/GameView.vue：把原「主台词 + scriptQueue」两套队列统一为 lineQueue
  （QueuedLine{speaker,text,emotion}）：主台词 splitTextSegments 切段在前，
  script_sequence 行在后；playNextLine 逐行推进；onDialogProceed 依序推进、
  播完解锁输入；opening / 玩家回合 / 推理(script_sequence) 三处统一走该队列。
- utils/text-segments.ts（新增）：splitTextSegments = 按换行 trim + 过滤空行。
- utils/__tests__/text-segments.spec.ts（新增）：切段 / 过滤空行 / 单段 / 空串。
- tests/visual/fixtures.ts：waitTyped / waitInputUnlocked 改为「逐段推进」：
  - waitInputUnlocked：锁定期间按钮可用即连续点继续快速跳过多段 AI 回声；
  - waitTyped：仅在「非空且非目标前缀」时点继续跳过回声段，目标前缀/空值等待，
    不打断目标 script 行。
  （mock 回声内嵌多行上下文，分段后旧「点一次即解锁」假设不再成立。）

## 3. 验证

| 套件 | 结果 |
|---|---|
| npm run typecheck | PASS |
| npm run test:unit | PASS 45/45（新增 4 条 splitTextSegments） |
| npm run test:visual | PASS 22/22（独立 mock 服务；基线不变） |
| npm run test:e2e | PASS 6/6（独立 mock 服务） |
| backend pytest | 不适用（零后端改动） |

## 4. 限制

- 恢复历史/读档路径保持现状：最后一句即时整段显示，不重播、不分段。
- 分段规则仅按换行（用户确认）；句号级分句不在本步。
- 测试助手改为逐段推进后，ch1-main-line 时长由 ~20s 增至 ~40-50s（因等待回声
  段推进），仍在 120s 超时内。

## 5. 证据

- 单测：Test Files 14 passed，Tests 45 passed。
- 视觉 22 passed + E2E 6 passed（exit 0，独立 mock 服务）。
