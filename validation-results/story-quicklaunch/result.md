# 快速上线固定剧本 — 验证结果

- **状态：PASS_WITH_LIMITATION**（限制即 docs/17 §3 列出的快速上线接受项）
- **日期：** 本次会话
- **范围：** 后端故事模式（story_content / story_runtime / API / 持久化 / 自动存档）+ 前端 StoryView；旧调查玩法回归。

## 测试用例与结果

| # | 用例 | 方法 | 结果 |
|---|---|---|---|
| 1 | 07 内容载入（14 场景 / 198 节点 / 3 选项 id 集合正确） | backend pytest test_story_content_loads / scene_ids | PASS |
| 2 | 坏内容 fail closed（未知 speaker / emotion / 空步骤 / 嵌套选项） | pytest 4 例 | PASS |
| 3 | 游标语义：advance 起步、选项跳转、分支合并回主线、choose 错误分支 | pytest test_choice_jump_and_merge / choose_requires_started | PASS |
| 4 | 全流程走查（3 选项全选 A，14 个场景边界 + end，结尾 kind=end） | pytest test_full_walkthrough_all_choices_a | PASS |
| 5 | 三分支各自走到结尾（不卡死） | pytest test_three_branches_reach_same_merge | PASS |
| 6 | 快照恢复（runtime 内存 + PersistedSession JSON 往返，旧快照兼容） | pytest 2 例 | PASS |
| 7 | Orchestrator 集成：台词进历史、仓库持久化恢复、AUTO 自动存档、未接线 fail closed | pytest 3 例 | PASS |
| 8 | 后端全量回归 | pytest -q | PASS（426 passed, 12 skipped） |
| 9 | 真实 HTTP 走查：完整剧本 178 行、3 选项、14 场景边界、结局、history 178 条、AUTO 存档存在 | uvicorn + Invoke-RestMethod | PASS |
| 10 | 存档载入：结局 AUTO 载入 → 新会话当前节点 = end | HTTP API | PASS |
| 11 | 中段手动存档 → 读档 → 恢复同一节点（SC01「好吧，有一点。」） | HTTP API | PASS |
| 12 | 前端 typecheck / 单测 / 生产构建 | npm typecheck / test:unit / build | PASS（45 单测全绿） |

## 失败与修复记录

1. **StoryRuntime 扁平化导致主线环**：初版把三个分支台词排进主线序列，advance 会走进其它分支再绕回选项节点（测试 10000 步守卫触发）。修复：改为链表节点图，分支末句 next 直指合并主线。
2. **Windows 瞬时文件占用**：快速连续原子写会话 JSON 时 os.replace 偶发 PermissionError（杀毒/索引瞬时占用）。修复：JsonSessionRepository.save 增加小退避重试（5 次，保原子写语义）。

## 已知限制（接受项）

见 docs/17 §3（评审稿内容、无音效、立绘占位、叙述行过渡、SC02 自由聊天段未实现、AUTO 粒度）。

## 下一步

1. 本机 docker-compose 全量验证（frontend 8080 经 nginx 反代走通）；
2. 等用户提供服务器信息后远程部署；
3. 用户补充缺失立绘后替换占位。
