# AI 对话玩法：删除前置剧情 + 常驻背景图替换

- **状态**：PASS（本机验证 + 公网复核）
- **部署**：服务器 git 同步 65a8380 → docker compose build backend frontend-vue → up -d；容器健康（backend/frontend-vue Up，postgres healthy）
- **日期**：2026-08-21
- **环境**：Windows 本机；backend 运行于 venv uvicorn :8000（GAL_PROVIDER=mock、GAL_SAVE_BACKEND=json）；前端 vite dev :5173；Playwright chromium 1366×768
- **任务来源**：用户直接需求（不在 docs/13 / docs/17 原计划内）：1) 删除 AI 对话玩法的前置剧情（「你醒了，别怕」开场白 + 「选择行动」选项步骤）；2) 用户提供新背景图，重命名放入项目并替换 AI 玩法常驻背景。

## 修改内容

| 文件 | 修改 |
| --- | --- |
| frontend-vue/src/views/GameView.vue | 新开局不再调用 /api/chat/opening：不播开场白、不自动弹选项窗口，直接进入自由对话；会话由首个玩家消息经 /api/chat 创建（响应带回 session_id 写回 localStorage）；新增 suppressFirstOptionPop —— 首个回合结束点「▼」也不自动弹「选择行动」；背景常量 BG 改为 /backgroud/background_ai.png |
| frontend-vue/src/api/game.ts | sendChat 允许 session_id = null（后端 mint 新会话） |
| frontend-vue/src/adapters/presentation-adapter.ts | applyPresentationStateView 背景参数化（默认仍为背景1，故事模式不变；GameView 传入 AI 常驻背景） |
| backgroud/background_ai.png | 新图（用户提供，重命名自 ChatGPT 生成图；1672×941 教室场景），后端 /backgroud 静态挂载直接可见 |
| docs/17 §2.5.2、docs/12 §10、AGENTS.md、CLAUDE.md | 行为变更说明 |

**未改**：后端 SCRIPT_OPENING 节点与 /api/chat/opening 端点原样保留（旧前端与既有测试依赖）；StoryView 故事模式背景不变；旧调查玩法仍经左上角「行动」按钮正式可见（既有决策）。

## 测试用例

| # | 用例 | 结果 |
| --- | --- | --- |
| 1 | 新开局不发 POST /api/chat/opening | PASS（请求日志 openingCalls=[]） |
| 2 | 页面无「你醒了」开场白文本 | PASS |
| 3 | 进入 /game 即输入可用（textarea 无 readonly） | PASS |
| 4 | 不自动弹「选择行动」窗口（entry + 首个回合点▼后） | PASS（optionWindowCount=0 / optionWindowAfterContinue=0） |
| 5 | 常驻背景为 /backgroud/background_ai.png（教室场景） | PASS（请求日志 + 截图确认） |
| 6 | 首个玩家消息经 POST /api/chat 创建会话，session_id 写回 localStorage、顶部显示会话 pill | PASS（c138ac5e…） |
| 7 | mock DeepSeek 正常回复（打字机） | PASS（「这是 DeepS…」） |
| 8 | 左上角「行动」按钮仍可打开选项窗口（旧调查玩法可见入口） | PASS（手动打开成功，窗口标题「选择行动」，选项「桌上的纸/继续对话」） |
| 9 | backend pytest | PASS（434 passed, 12 skipped，无回归） |
| 10 | 前端 vue-tsc typecheck / vitest / vite build | PASS（57 tests，build 成功） |
| 11 | story-smoke 回归（故事模式 → 结局 → /game 继续聊天） | 见 evidence/story-regression 与 smoke 输出 |

## 证据

- evidence/01-title.png 标题画面
- evidence/02-game-entry.png 进入 AI 玩法：教室背景、无立绘、输入框可用、无选项窗口
- evidence/03-after-first-reply.png 首个回合结束：无自动弹窗、背景不变、「行动」按钮可见
- evidence/04-option-window-manual.png 手动打开「选择行动」（旧玩法入口完好）
- evidence/story-regression/ 故事模式回归截图
- evidence-public3/ 公网复核（http://114.55.133.96/）：与上述断言一致（openingCalls=[]、optionWindow=0、背景 background_ai.png 200、首条消息建会话、mock 回复、行动按钮可用）

## 公网复核结果

与用例 1-8 断言逐项一致（GAL_BASE_URL=http://114.55.133.96/）：POST /api/chat/opening 未发出；无「你醒了」文本；进入即输入可用；全程无自动弹「选择行动」；/backgroud/background_ai.png 200（2103237 bytes）；首个玩家消息创建会话（30b7b578…）；「行动」按钮手动打开选项窗口正常。注：nip.io HTTPS 从本地网络握手被重置（GFW SNI 干扰，服务器自测 200 正常），公网冒烟改用 HTTP 执行。

## 已知限制

- 新开局在首个玩家消息发出前，顶部显示「未连接」（会话在首条消息时创建）；属预期行为。
- 背景图为 AI 生成 Fixture（用户提供），2.1MB PNG 未压缩；后续如需可转 WebP 压缩。
- 后端 /api/chat/opening 仍可用（旧前端路径），现役前端不再消费。
