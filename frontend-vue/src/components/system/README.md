# Task 7 游戏内系统菜单（docs/13 §13）

- `SystemMenu.vue` — 系统菜单：保存 / 读取 / 历史 / 设置 / 返回标题。
- `HistoryPanel.vue` — 对话历史（§13.3）：当前 Session 已显示 History（docs/01 §18），≠ Character Memory。

菜单只发事件由 GameView 打开对应面板；返回标题不删除 Session、不强制任意中间态 snapshot（§13.4）。
