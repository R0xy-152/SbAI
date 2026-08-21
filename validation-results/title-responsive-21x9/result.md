# 标题背景 21:9 响应式适配

- 状态：PASS
- 日期：2026-08-21
- 环境：Windows 11 / Chromium Playwright / Vue 3 + Vite

## 变更

- 新增 `backgroud/background_title_21x9.png`（1915×821，2.3325:1）。
- 16:10、16:9 默认使用原 3:2 近景图 cover。
- 视口比例达到 1.9:1 后切换 21:9 扩展图。
- 2.45:1 以上极端超宽屏保持清晰图完整高度，模糊层横向兜底。
- 背景视差超扫由 120% 收敛为左右各 12px。
- 菜单双列阈值由 2:1 提高到 2.2:1。

## 验证

- `npm run typecheck`：PASS。
- `npm run test:unit`：59 passed。
- `npm run build`：PASS。
- `scripts/title-responsive-smoke.mjs`：
  - 1280×800（16:10）：原图、单列、cover，PASS；
  - 1920×1080（16:9）：原图、单列、cover，PASS；
  - 1920×950（约 2:1 浏览器内容区）：21:9 图、单列、cover，PASS；
  - 2520×1080（21:9）：21:9 图、双列、cover，PASS；
  - 3840×1080（32:9）：21:9 图、双列、完整高度，PASS。
- 对 16:9、约 2:1 和 21:9 截图进行人工检查：无硬接缝，三名角色面部与主要身体区域可见，菜单与标题未越界。
