# 序章固定剧本与无序探班实现验证

- 状态：PASS
- 日期：2026-08-21
- 环境：Windows / Python pytest / Vue 3 + Vitest + vue-tsc + Vite / Playwright Chromium
- Provider：`GAL_PROVIDER=mock`（不需要 API Key）

## 验证范围与结果

1. `docs/story/Prologue.md` 可由后端 fail-closed 内容加载器完整编译；`main` 情绪映射为既有 `neutral`：PASS。
2. DeepSeek、ChatGPT、Claude 的 6 种访问排列全部可完成：PASS。
3. 每次只返回未访问角色；重复访问、未知角色、选项节点直接 advance 均拒绝：PASS。
4. 三篇全部完成后才进入三人集合；后端权威下发三人站位、缩放和垂直补偿，三套不同留白的人物素材头肩等高、膝盖线贴近对话框：PASS。
5. 快照/恢复保留阶段、段内台词、已访问集合、活动分支和最终聊天对象：PASS。
6. 最终 DeepSeek / ChatGPT / Claude 三种选择均可写入后日谈路由；Presence Gate 只允许所选角色：PASS。
7. 旧第一章 `story_cursor={node_index}` 继续由 legacy Runtime 恢复：PASS。
8. 章节选择 → 序章 → Claude → DeepSeek → ChatGPT → 三人集合 → ChatGPT 后日谈浏览器流程：PASS。

## 自动化证据

- 后端全量：`451 passed, 12 skipped`。
- 后端序章定向（最终版）：`13 passed`。
- 前端：`20` 个测试文件、`64 passed`；`vue-tsc` PASS；Vite production build PASS。
- 浏览器：`frontend-vue/scripts/prologue-smoke.mjs` 输出 `status=PASS`，观测选项依次为 3 / 2 / 1 / 最终 3 个聊天对象，并到达 `/game?character=chatgpt`。
- 截图：`evidence/01-opening.png`、`evidence/choice-1.png` 至 `choice-4.png`、`evidence/05-reunion-knee-line.png`、`evidence/06-chatgpt-aftertalk.png`。

## 素材说明

- 序章已接入专用常驻背景 `backgroud/background_prologue.png`（1672×941，16:9）。21:9 下使用居中 `cover` 裁切，主体安全，无需额外生成超宽版本。
- `claude_annoyed.png` 不存在，既有资产解析器会按设计回退 `claude_main.png`；不阻塞流程。
- 浏览器冒烟使用 `GAL_AUTH_REQUIRED=false` 时，现有 Test User 标识不满足存档 API 的 player_id 格式，会在标题页产生一次既有 `/api/saves` 400；序章 Runtime 的仓库/快照/恢复与 SaveSnapshotService 自动化测试均通过。正式账号链路不使用该测试标识。
