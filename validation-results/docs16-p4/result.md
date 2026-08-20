# docs16-p4 · 继续/发送按钮命中区扩大 — 验证结果

> **状态：PASS**
> **日期：2026-08-23** · **环境：** frontend-vue；backend 未改动。
> **依据：** docs/16 P4（docs/16-玩家体验修复与开局选项窗口落地方案.md §2）。

## 1. 目标

对话框右下角 ▼（#sendButton）按钮**位置与外观不动**，只扩大命中区域，且不与
其它功能按键（选项气泡条 / 系统菜单等）重合。

## 2. 改动

- frontend-vue/src/components/game/standard/GameDialog.vue：
  - #sendButton 增类 send-hit-area；
  - 新增 .send-hit-area::after（content:''；绝对定位）透明扩展命中区：
    top:-40px / bottom:-24px / right:-24px / left:0 —— 向右/下/上方扩展（这些
    方向是对话框右侧与屏幕底边的空区，不会压到 textarea 右侧输入区），
    **不向左扩展**，避免与输入区及上方气泡条冲突。
  - 视觉按钮位置/样式/disabled 行为完全不变；E2E locator #sendButton 不变。

## 3. 验证

| 套件 | 结果 |
|---|---|
| npm run typecheck | PASS |
| npm run test:unit | PASS 39/39 |
| npm run test:visual | PASS 22/22（::after 透明，无可见像素变化，无需重拍基线） |
| npm run test:e2e | PASS 6/6（独立 mock 服务；#sendButton 点击更易命中） |
| backend pytest | 不适用（零后端改动） |

## 4. 限制

- ::after 命中区在 disabled（thinking）时随按钮一并禁用，不改变语义。
- 上方 -40px 扩展经布局核对在选项气泡条下方，未与其重合；P8 选项改窗口化后
  该空间更无冲突。

## 5. 证据

- 单测：Test Files 12 passed，Tests 39 passed。
- 视觉 22 passed + E2E 6 passed（exit 0，独立 mock 服务）。
