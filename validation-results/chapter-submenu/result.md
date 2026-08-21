# 开始游戏章节下级菜单验证结果

- 状态：PASS
- 日期：2026-08-21
- 环境：Windows 11 / Node.js（项目锁定依赖）/ Chromium Headless
- 范围：标题页一级菜单、`/chapters` 章节选择、序章入口、锁定状态与多比例布局

## 实现结果

1. 标题页只保留「开始游戏 / 继续游戏 / 读取存档 / 设置」四个一级菜单，顺序固定且所有宽高比均为单列。
2. 「开始游戏」进入 `/chapters`，不在打开下级菜单时清除当前会话。
3. 章节页按视觉稿显示「序章 / 第一章 / 第二章 / 第三章 / 第四章 / 终章」，桌面为 2 列 × 3 行，窄屏为单列。
4. 仅「序章」可用；进入时清除旧 `gal_session_id` 与待读档状态并路由到 `/game`。其他五章显示「未开发」、原生 `disabled` 且不可点击。
5. 章节页复用 `backgroud/background_title_21x9.png`：常规比例 `cover`，32:9 使用清晰居中层与模糊延展层。
6. 左下「返回」回到标题页；窄屏为全局账号状态条预留顶部安全区。
7. 主标题、副标题、章节名、状态和返回按钮统一继承标题页现有无衬线中文字体栈。

## 自动验证

| 用例 | 命令 / 范围 | 结果 |
|---|---|---|
| 前端完整回归 | `cd frontend-vue && npm test` | PASS：20 个测试文件、63 条测试；typecheck 与 production build 通过 |
| 标题多比例 | `node scripts/title-responsive-smoke.mjs` | PASS：16:10、16:9、2:1、21:9、32:9；四项菜单均未切双列 |
| 章节多比例 | `node scripts/chapter-menu-smoke.mjs` | PASS：390×844 单列；1920×1080、2520×1080、3840×1080 双列；无水平溢出 |
| 章节状态 | `ChapterSelectView.spec.ts` + smoke | PASS：六章顺序正确，仅序章 enabled，其余五章 disabled |
| 导航与状态清理 | `TitleView.spec.ts` / `ChapterSelectView.spec.ts` | PASS：标题→章节页、序章→`/game`、返回→标题页、旧会话清理 |
| 变更格式 | `git diff --check -- <本任务文件>` | PASS |

## 视觉证据

- `screenshots/16x9.png`：常用 16:9，2 列 × 3 行。
- `screenshots/21x9.png`：目标 21:9 背景与章节面板。
- `screenshots/32x9.png`：极端超宽清晰居中 + 模糊延展。
- `screenshots/narrow.png`：390×844 单列与账号栏安全区。
- `screenshots/16x10.png`、`screenshots/browser-2x1.png`：标题页一级菜单比例回归。

人工复核：16:9、21:9 与窄屏截图中文字完整，锁定状态可辨，返回入口可见，未发现横向滚动或账号状态条遮挡标题。

## 限制与兼容

- 未新增任何章节剧情或章节美术；章节卡片以 CSS 生成，视觉稿仅作为布局和层级参考。
- `/story` 继续为既有故事存档恢复及直接兼容保留，但不再作为新开局入口。
- 本次未执行线上部署或真实 Provider 对话；既有 AI 新开局冒烟脚本已更新为「开始游戏 → 序章 → /game」路径。
