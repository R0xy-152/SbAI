# merge-main-into-second-tier — 三线合并验证记录

- 状态：PASS
- 日期：2026-09-03
- 环境：macOS / git 2.55 / Python 3.12（SbAI venv）/ GAL_PROVIDER=mock

## 背景

main（生产线，已部署 sbai.xin）与 feat/second-tier（引擎线）自 27fcb19 分叉：main 12 提交（部署/安全/邀请码/人机感评审 #1），引擎线 14 提交（记忆/事实账本/一致性校验/评测/情绪状态机/多角色）。以 feat/second-tier 为基线 merge main，合并提交 a933ebb。

## 冲突解决（23 重叠 / 14 冲突 / 33 冲突块）

- `eval/*` 4 文件：取 main 侧（8d99d81 评审后版本：isfinite 防护、JSON 注入防御、authorized/forbidden 权限上下文、更全测试）。tier 侧无独有功能。
- `characters/*`：3 个角色文件取 main 的 personas 模块结构（内容与 tier 内联人设逐句等价）；`base.py` 保留双方互补功能（main 的 player_notes 去重渲染 + 引擎线 last_reflection 自我反思回灌）。
- frequency_penalty：**移除**（用户确认，跟随 main 09-03 判断——DeepSeek 已弃用该参数、thinking 模式忽略）。
- `memory.py`：删除自动合并产生的重复 `retrieve_player_notes`；`retrieve_context` 扩展 query/now 透传，保住语义召回（docs/05 §40-41）与衰减排序（§66）。
- `character_state.py`：main 的 reasoning 显式清空语义 + 关系阶段校验 + 引擎线的 reflection_for/commit_reflection 接口。
- `orchestrator.py`：retrieve_context(query/now) + 召回强化（reinforce）+ last_reflection 注入，三方功能共存。
- 前端：新增 vitest localStorage polyfill（happy-dom 不提供 localStorage），修复 main 预存在的 20 个失败（对照实验证实 main 副本同样失败，非合并引入）。

## 验证结果

| 项 | 结果 |
|---|---|
| 后端 pytest（mock） | 556 passed, 12 skipped |
| 前端 vitest | 77 passed |
| 前端 vue-tsc typecheck | PASS |
| 前端 vite build | PASS |
| 冲突标记/UU 残留 | 0 |
| feat/first-tier 清理 | 远端+本地已删除（用户确认） |
| origin 分支 | main=a933ebb, feat/second-tier=a933ebb |

## 已知限制

- 未在真实 DeepSeek 与线上环境验证；是否部署合并结果由用户决定。
- gal-first-tier worktree 处于 detached HEAD @ a933ebb（分支已被 second-tier 包含）。
- memory.py 语义重叠区（main fix#3 与引擎线重写）虽文本自动合并成功，已通过全量测试，但未做真实对话回归。
