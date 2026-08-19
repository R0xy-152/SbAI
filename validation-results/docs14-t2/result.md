# docs/14 T2 — 选项功能前端接入（OptionsPanel + investigate + chat_routing）

> **状态：PASS**（2026-08-19）

## 范围

docs/14 §3 T2：前端 OptionsPanel 气泡按钮条；接入 investigate（纸 + 其余 3 个
hotspot，走 payload.steps）与 chat_routing（粘性路由，用户确认方案 A）；E2E 覆盖
选项路径与 D3/D5 断言。同批顺带：Claude 立绘迁入 char/ 约定。

## 环境

- backend：FastAPI + mock provider（GAL_PROVIDER=mock）；Playwright webServer 自起
- frontend-vue：Vue 3 + Vite + TS；Playwright 1.62，两个 viewport 项目
- 视觉阈值：maxDiffPixelRatio 0.005 → **0.0015**（见「排障记录」）

## 修改文件

- 新增 `frontend-vue/src/components/game/standard/OptionsPanel.vue`：气泡按钮条
  （D6），只渲染后端下发的 options、原样回传（D7）；routeLabel / activeRouteId /
  feedback / busy 由 GameView 驱动
- 新增 `frontend-vue/src/components/game/standard/__tests__/OptionsPanel.spec.ts`
  （4 用例）
- `frontend-vue/src/views/GameView.vue`：删除旧「调查桌上的纸」按钮与
  available_hotspots 推断；options 由 reconcileStage / applyLoadedSession 对账；
  executeOption：investigate 逐步骤执行 payload.steps → 先对账后反馈；
  chat_routing 粘性路由（再点同一气泡取消；路由对象离场自动复位）；
  sendChat 透传 character_id（仅路由激活时）
- `frontend-vue/src/api/game.ts`：GameOption 类型、fetchGameState options 字段、
  sendChat 可选 characterId
- `frontend-vue/src/api/saves.ts`：LoadResult.state.options
- `frontend-vue/src/adapters/asset-resolver.ts`：claude →
  /char/claude/pic/claude_main.png；新增 `char/claude/pic/claude_main.png`
  （源文件哈希一致，旧图保留供冻结旧前端）
- `frontend-vue/tests/visual/fixtures.ts`：inspectPaper 走选项气泡；
  claude_main.png 断言
- `frontend-vue/tests/e2e/ch1-main-line.spec.ts`：D3 断言（开场仅纸上选项；
  完成后消失；Claude 登场后 4 个新选项出现、DeepSeek 无路由选项）、D5 粘性路由
  双向断言（后端历史 character_id=claude → 取消后 deepseek）、Load 恢复后选项
  对账断言
- `frontend-vue/playwright.config.ts`：阈值 0.0015 + 注释记录两次教训
- `docs/14-…`：T2 标记完成；`docs/11-…` §15：勾销两项（Hotspot 调查 / 对话路由）
- 视觉基线：10 张 vue-visual 基线重拍（TITLE 2 张逐字节不变，佐证确定性）

## 验证结果

| 套件 | 结果 |
|---|---|
| backend pytest | 377 passed, 12 skipped |
| vitest | 20 passed（含 OptionsPanel 4） |
| vue-tsc + vite build | PASS |
| test:visual | 18/18 ×2（0.0015 阈值连续两轮无抖动） |
| test:e2e | 2/2（含新选项断言） |

E2E 新增覆盖：开场仅「桌上的纸」；拓印后选项消失；Claude 登场后
「找 Claude 谈谈」可见且「找 DeepSeek 谈谈」不可见；主终端 / C-02 隔离门 /
角色注册表选项可见；路由后历史末条 character_id=claude、取消后=deepseek；
Load 后「桌上的纸」选项不可见（hotspot=completed，权威 /api/game/state 佐证）。

## 排障记录（关键）

1. **EBUSY**：vite 运行期间编辑前端文件会崩（chokidar），编辑前先停 vite。
2. **Playwright 阈值陷阱（本次最重要的教训）**：T2 选项气泡条约占画面 0.16%，
   低于旧阈值 0.5% —— 对比「通过」且 `--update-snapshots` 对未超阈值文件
   **跳过重写**（基线 mtime 不变，git 干净），形成「旧基线静默有效」假象。
   排查手段：全像素 diff（1.64% vs 旧基线为探针时机差；测试捕获图实际 0.16%）。
   处置：先移走旧基线强制重拍 + 阈值收紧至 0.0015（噪声实测 <0.1%）。规则：
   **基线重拍前先删除旧图；新增小元素后复查阈值**。
3. GLM 视觉复核：新 OPENING 基线含胶囊「桌上的纸」、无旧「调查桌上的纸」按钮。

## 已知限制 / 后续

- evidence_present / deduction / private_interview / recovery / narrative 五类
  kind 前端暂不处理（后端届时才下发），属 T3/T4。
- 行为差异（按 docs/14 §2.3 决策）：已完成热点在 Vue 不再提供复查选项
  （旧前端冻结版仍保留复查按钮；docs/12 §41 的复查语义仅适用于旧前端参考实现）。
- 豆包仍为占位 SVG；Claude 立绘已迁 char/ 约定。
