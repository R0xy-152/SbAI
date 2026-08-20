# docs16-p3 · 标题背景完整显示 + 模糊填充 — 验证结果

> **状态：PASS**
> **日期：2026-08-23** · **环境：** frontend-vue；backend 未改动。
> **依据：** docs/16 P3（docs/16-玩家体验修复与开局选项窗口落地方案.md §2）。

## 1. 目标

标题界面背景 background_title.png（1536×1024，3:2）在 16:9 窗口下原 cover +
120% 宽导致上下各裁约 21%。改为：整图完整显示不裁切，左右两侧用同一张图
模糊放大填充（无黑边、无人物裁切）。

## 2. 改动

- frontend-vue/src/views/TitleView.vue：
  - .title-bg-layer 由「单层 cover」改为「容器 + 两子层」：
    - .title-bg-fill：同图 cover + blur(24px) + brightness(0.72) + saturate(1.05)
      + scale(1.08)（scale 防止模糊边缘露白）；
    - .title-bg-sharp：同图 background-size: auto 100% 居中（高度铺满、宽度
      按 3:2 比例，整图完整显示）。
  - 视差仍作用于整层容器（bgRef），位移时两侧永远露出的是模糊填充层，不露底。

## 3. 验证

| 套件 | 结果 |
|---|---|
| npm run typecheck | PASS |
| npm run test:unit | PASS 39/39（TitleView 无背景断言） |
| npm run test:visual | PASS 22/22（重拍 TITLE-EMPTY-SAVE ×2 viewport 基线后） |
| npm run test:e2e | PASS 6/6（独立 mock 服务） |
| backend pytest | 不适用（零后端改动） |

## 4. 证据

- 重拍基线：tests/visual/baselines/visual/vue-visual.spec.ts-snapshots/
  TITLE-EMPTY-SAVE-desktop-{1366x768,1920x1080}-win32.png（本步提交）。
- 游戏内 OPENING-DEEPSEEK-ONLY 等其余基线未变（P3 仅动标题屏）。

## 5. 限制

- 模糊填充层 + 清晰层同源同图，视差位移时清晰图边缘与模糊底过渡自然；
  若未来替换背景图需同步更新两层 url（同 CSS 变量化不在本步范围）。
