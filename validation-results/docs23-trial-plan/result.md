# docs23-trial-plan 验证记录

> **状态：** PASS_WITH_LIMITATION
> **日期：** 2026-09-04
> **环境：** macOS / repository documentation review

## 目标

在不修改既有序章、第一章、终章或运行时代码的前提下，把用户提出的试玩版开局、两段演出、片段 1 与文字天体玩法整理为 ACTIVE 落地方案，并审计当前技术栈是否可承载。

## 验证用例与结果

| 用例 | 结果 |
|---|---|
| 文档状态明确为 ACTIVE | PASS |
| 范围截止片段 1 → 片段 2 双线路提交点 | PASS |
| 未补写具体对白、证据答案、分支剧情 | PASS |
| 明确冻结并隔离既有序章/第一章/终章/旧调查玩法 | PASS |
| 对照最高优先级 Scope 标出开场与主动交互冲突 | PASS |
| 对照当前 Vue/FastAPI/Session/Save/Evidence/Deduction 代码给出复用项和缺口 | PASS |
| 给出玻璃拼图与文字多体运动的可实现方案 | PASS |
| 给出 Backend 权威提交、存档恢复、测试和实施顺序 | PASS |

## 证据

- 方案文档：`docs/23-核心玩法闭环试玩版落地方案.md`
- Scope：`docs/MVP/00 — Project Scope.md`
- 架构与 Narrative：`docs/MVP/02 — System Architecture.md`、`docs/MVP/03 — Narrative Runtime.md`
- 现有模式：`docs/17-快速上线固定剧本落地方案.md`、`docs/19-序章固定剧本与无序探班落地方案.md`
- 当前代码：`frontend-vue/package.json`、`frontend-vue/src/app/router/index.ts`、`frontend-vue/src/views/StoryView.vue`、`frontend-vue/src/views/GameView.vue`、`backend/app/game/orchestrator.py`、`backend/app/game/deduction.py`、`backend/app/save/service.py`

## 限制与阻塞

> 后续更新：用户已确认“试玩版”、原初 AI 命名/遮蔽、Scope 例外和独立分支；实现结果另见 `validation-results/docs23-trial-implementation/result.md`。以下内容保留为方案评审当时的历史结论。

- 本次只完成文档和静态技术审计，没有编写原型或运行产品测试，因此对玻璃拼图视觉质量、低端设备性能和触控手感的判断仍需 Task 3 技术原型验证。
- `docs/MVP/00 — Project Scope.md` 尚未增加试玩模式例外；进入实现前必须由用户确认并先修正文档。
- 原初 AI 命名、开局输入回复策略、第一次失败规则、Evidence/Branch Mapping 和片段 2 内容均待用户确认。
