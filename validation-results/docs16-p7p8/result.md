# docs16-p7/p8 · 选项窗口化 + 线索窗口（气泡条退役） — 验证结果

> **状态：PASS**
> **日期：2026-08-23** · **环境：** frontend-vue；backend 未改动（复用既有 options/evidence/action 端点）。
> **依据：** docs/16 P7/P8（docs/16-玩家体验修复与开局选项窗口落地方案.md §2）；docs/14 D6 修订。

## 1. 目标

问题 6 + 8：去掉「桌上的纸」持久气泡；开局 AI 输出「唔……我这边什么都看不到呢…」
这类话后，点继续弹出 lingchat 式选项窗口；点调查选项后出现对应线索窗口。最终形态：
**所有选项统一走窗口**（docs/14 D6 气泡按钮条退役），自由输入不受限（D4）。

## 2. 改动

- 新增 frontend-vue/src/components/game/standard/OptionWindow.vue：竖排选项窗口（选项 +
  「继续对话」关闭项；chat_routing 粘性高亮；长列表可滚动）。
- 新增 ClueWindow.vue：线索窗口（证据标题 + 描述 + 关闭）。
- api/game.ts：新增 EvidenceView + fetchEvidence（GET /api/game/evidence）。
- views/GameView.vue：
  - 移除 OptionsPanel；新增 showOptionWindow / activeClue / openOptionWindow /
    closeOptionWindow / onOptionWindowSelect / performInvestigate / openClueWindow /
    onClueClose / closePanel；
  - onDialogProceed：台词播完点继续 → 有选项则弹窗口，否则解锁输入；
  - 顶栏新增「行动」按钮（有选项时显示）随时重开窗口；
  - 输入态按 kind 收敛：deduction / narrative(testify) 出提示行自身解锁；
    evidence_present/private_interview 面板关闭时解锁；其余统一解锁；
  - routeLabel / feedback 改为对话框上方状态行（取代气泡条位置）。
- 删除 OptionsPanel.vue + OptionsPanel.spec.ts；新增 OptionWindow.spec / ClueWindow.spec。
- tests/visual/fixtures.ts：waitInputUnlocked 自动关闭窗口；新增 openOptionWindow /
  clickOption / openOptionWindowIfAny；inspectPaper 改经窗口 + 线索窗口。
- E2E ch1-main-line / ch1-options-t3 / t4 改写为窗口交互；effects-showcase 补窗口关闭。
- 重拍游戏内视觉基线 5 张 × 2 viewport（气泡条移除）。

## 3. 验证

| 套件 | 结果 |
|---|---|
| npm run typecheck | PASS |
| npm run test:unit | PASS 45/45（删 OptionsPanel 4 条，新增 OptionWindow/ClueWindow 4 条） |
| npm run test:visual | PASS 22/22（重拍 10 张游戏内基线） |
| npm run test:e2e | PASS 6/6（独立 mock 服务） |
| backend pytest | 不适用（零后端改动） |

## 4. 限制

- 窗口在每次「台词播完 + 继续」时若存在选项即弹出（用户确认「所有选项统一走窗口」）；
  「继续对话」/「行动」均可跳过或重开，自由输入不受限。
- 线索窗口内容为证据 title + summary（docs/10 证据 registry）；不新增图片素材。
- 无后端语义变更；选项仍是 UI 通道（D7）。

## 5. 证据

- 单测：Test Files 15 passed，Tests 45 passed。
- 视觉 22 passed + E2E 6 passed（exit 0，独立 mock 服务）。
- 重拍基线：vue-visual.spec.ts-snapshots 下 5 张 × 2 viewport。
