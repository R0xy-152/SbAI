# readme-reposition — README 重定位为 AI 叙事一致性引擎

- 状态：PASS
- 日期：2026-09-03
- 环境：macOS / git / gh CLI（账号 R0xy-152）

## 目的

从面试官视角重定位（P0-3）：把「galgame demo」的门面改为「AI 叙事一致性引擎 + 对话式悬疑解谜 demo」，让差异化系统在 30 秒内可见。

## 变更

- 标题下加一句话定位（「语言自由，事实不自由」）+ 在线体验链接 sbai.xin。
- 新增「技术亮点」节：LLM 三层校验、确定性叙事运行时、角色信息隔离、记忆系统、事实账本 + 一致性校验、反思回灌、LLM-as-judge、工程纪律。
- 架构节嵌入系统架构图（docs/architecture/project-architecture.visual-check.1440x900.dark.png）。
- 新增「评测」节：真机 4 维平均分（详单见 eval-live-deepseek 记录）。
- 数字刷新：后端 456→556 passed；前端 71→77 passed（本机实跑复核）。
- 第一章状态改为「已实现并通过测试，入口待上线（Beta 暂缓）」。

## 验证

| 项 | 结果 |
|---|---|
| 后端 pytest 复核 | 556 passed, 12 skipped（4.12s，GAL_PROVIDER=mock） |
| 前端 vitest 复核 | 77 passed（26 files） |
| 架构图文件存在 | docs/architecture/project-architecture.visual-check.1440x900.dark.png ✓ |
| GitHub 元数据 | description + topics 已设置（gh repo edit） |

## 已知限制

- 评测节 A/B 数字待 eval-ab 真机跑分完成后回填引用。
- 仓库公开（R0xy-152/SbAI），README 是简历主入口，后续数字变更需同步本节。
