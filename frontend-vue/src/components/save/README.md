# Task 7 Save/Load UI 组件

- `SavePanel.vue` — 游戏内「保存」面板（docs/13 §13.1）：6 个手动 Slot + 即时标题输入；LLM 中间态禁用（§22）。
- `LoadPanel.vue` — 读取面板（§12.4 / §13.2）：Auto + 6 Manual；overlay（游戏内）与 embedded（LoadView 页）两种形态；删除仅手动 slot（§20）。
- `AutoSaveCard.vue` — 唯一 AUTO slot 卡片（Task 8 接 checkpoint 后由后端自动写入）。
- `ManualSaveSlot.vue` — 单个手动存档 slot（save/load/view 三种模式）。

数据走 `stores/saves` → `api/saves`（Save API，docs/13 §20）；snapshot 由 Backend Capture（§14.2），list 只下发 slot 元数据（§29）。展示格式化在 `utils/save-format.ts`。
