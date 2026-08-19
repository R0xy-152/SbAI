# docs/14 T3 — 选项功能：出示证据 / 引导推理 / 私审质询

> **状态：PASS**（2026-08-19）

## 范围

docs/14 §3 T3：evidence_present（单个选项 + 小面板，用户确认）、deduction
（D2 引导式提示 + 主输入框一次性推理模式，用户确认）、private_interview
（挑战小面板，参考旧前端形态）三类选项的后端生成 + 前端接入；E2E 推进到
INF01 / Claude 私审完成。

## 环境

- backend：FastAPI + mock provider（GAL_PROVIDER=mock）；Playwright webServer 自起
- frontend-vue：Vue 3 + Vite + TS；Playwright 1.62，两个 viewport 项目
- 视觉阈值：0.0015（T2 已收紧）

## 修改文件

- `backend/app/game/options.py`：新增三种选项生成——
  - evidence_present：FIRST_IMPOSSIBLE_EVENT_RESOLVED 后下发「出示证据」，
    payload 携带已获证据（id/title/summary，兼作 Evidence 查看）+ 在场角色
  - deduction：CT01/CT04（证词齐备/证据齐备且矛盾未解决）与 INF01-04
    （INFERENCE_GATES 满足且未接受；INF04 特殊条件），label + 系统台词式
    hint（例句刻意避开 03:17 token，玩家照抄即命中判定词，D6 兼容）
  - private_interview：claude/chatgpt/doubao 挑战条件与既有
    private_interview_challenges 一致；payload 携带证词/关键证据/观察选项
    文案（豆包证词预选）
- `backend/tests/test_options.py`：+5 用例（出示解锁、CT01 双证词门槛、
  推理门与幂等、CT04 证据门槛、私审选项与完成后消失）
- `frontend-vue/src/components/game/standard/SubActionPanel.vue`（新）：
  D6 小面板——证据×角色单选、证词勾选、观察单选、GPT 单证据自动选中；
  只回传所选 id（D7）
- `frontend-vue/src/components/game/standard/__tests__/SubActionPanel.spec.ts`
  （新）：5 用例
- `frontend-vue/src/views/GameView.vue`：deduction 分支（系统台词播放提示、
  pendingDeduction 一次性推理模式：下一条输入提交 /api/game/deduction，判定
  与演出序列仍全走后端）；evidence_present / private_interview 分支（弹面板，
  submit 回传既有端点）；Load 复位推理/面板本地态
- `frontend-vue/src/api/game.ts`：presentEvidence /
  submitPrivateInterviewChallenge
- `frontend-vue/tests/e2e/ch1-options-t3.spec.ts`（新）：完整 T3 链路
- `docs/11-…` §15：勾销 Evidence 查看/出示、Claim 反馈、Contradiction /
  Inference 提交、Private Interview 入口与三类私审挑战面板；`docs/14` T3 标记完成

## 验证结果

| 套件 | 结果 |
|---|---|
| backend pytest | 382 passed, 12 skipped |
| vitest | 25 passed（含 SubActionPanel 5） |
| vue-tsc + vite build | PASS |
| test:e2e | 4/4（main-line ×2 + T3 ×2） |
| test:visual | 18/18（无基线漂移：T3 未改动基线场景画面） |

T3 E2E 链路（×2 viewport）：03:17 → 调查 3 热点（主终端触发
RESOLVE_IMPOSSIBLE_EVENT）→ 出示解锁（D3 断言未解锁前不可见）→ 面板出示
「压痕纸条」给 Claude（/api/game/evidence 权威断言 presented_to）→ 路由
Claude 取两条证词（确定性 inquiry：谁打开的门 / 亲眼）→ CT01 选项出现 →
系统台词提示 → 一次性推理提交 → 推理成立 → CT01 选项消失、私审选项出现 →
勾选两条证词提交质询 → 私审完成 → INF01 选项出现 → 提示 + 推理 → GPT 立绘
登场 → INF01 选项消失、找 ChatGPT 谈谈出现、CT04 不提前出现（D3）。

## 已知限制 / 后续

- 豆包 / GPT 私审面板已实现并有单测，但挑战触发条件要到 CT04 / 豆包证词
  阶段（T4 E2E 驱动）；「私审小游戏」本体按 docs/14 §5 不实现。
- recovery / narrative 两类 kind 为 T4 预留。
- 推理不成立时（NO_MATCH/BLOCKED）仅反馈文案，无重试引导——与旧前端一致。
