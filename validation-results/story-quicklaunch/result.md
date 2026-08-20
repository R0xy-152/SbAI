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
| 13 | docker-compose 全栈：index.html / nginx 反代 health / 静态资源（deepseek png、doubao 占位） | docker compose up + HTTP | PASS |
| 14 | 经 nginx 完整走查剧本 + postgres 存档读档 | HTTP（8080） | PASS（176 行、3 选项、14 场景边界、AUTO 在 postgres、load 恢复 end） |
| 15 | UI 冒烟（Playwright）：标题 → 开始游戏 → 全程推进 → 3 个选项窗口 → 结局 → 返回标题 | scripts/story-smoke.mjs | PASS（choiceCount=3, ended=true） |
| 16 | 截图视觉核验：选项窗口按钮逐字 = 07 的 A/B/C；结局画面 =「第一章 完 / 《03:17 Incident》 / TO BE CONTINUED / 返回标题」 | vision-router（glm-4v-flash） | PASS |

## 补充（选项窗口借鉴 LingChat）

- StoryChoiceWindow 按 LingChat GameChoices（components/game/standard/extra/GameChoices.vue，AGPL 参考源码）重做：全屏悬浮胶囊按钮组（无面板卡片）、交错入场动画（100ms 逐个上浮 + 回弹缓动）、选择后 300ms 缩放渐隐离场、悬停微光扫射 + 静态/漂浮粒子，配色换用本项目皮肤 token；prefers-reduced-motion 下停用循环动画。
- 验证：StoryChoiceWindow 单测 3 例（渲染/离场后 emit/busy 禁用）+ 冒烟测试重跑通过（3 选项、结局、返回标题）+ 视觉核验（glm-4v-flash）：3 个胶囊按钮纵向排布、半透明玻璃质感、背景场景透出，与 LingChat 一致。前端单测总数 45 → 48。
- 冒烟脚本修复：选项点击后等待窗口真正消失再继续（离场动画期间窗口仍在，避免对同一窗口二次定位超时）。

## 补充2（部署前加固验证，第2轮）

| # | 用例 | 结果 |
|---|---|---|
| 17 | 旧调查玩法回归（入口隐藏但代码完好）：/api/chat/opening + /api/chat + /api/game/state 经 nginx 均正常（mock provider） | PASS |
| 18 | 容器重启恢复：backend 容器 restart 后 health ok，故事会话当前节点恢复（CONNECTION ESTABLISHED） | PASS |
| 19 | postgres 落库实证：game_saves 表存在 AUTO 行（chapter=ch1，psql 直查） | PASS |
| 20 | 选项节点刷新恢复：刷新后同一选项窗口重现（3 个选项逐字一致），可继续选择推进 | PASS（evidence/05-refresh-at-choice.png） |
| 21 | deploy/verify.ps1 验收脚本：本机 5/5 PASS；错误端口 5/5 FAIL + exit 1 | PASS |

## 证据

- evidence/01-title.png、02-story-start.png、03-choice-1..3.png、04-ending.png（docker 栈 8080 实机截图）；
- 后端 pytest 全量输出、API 走查输出见本会话执行记录。

## 失败与修复记录

1. **StoryRuntime 扁平化导致主线环**：初版把三个分支台词排进主线序列，advance 会走进其它分支再绕回选项节点（测试 10000 步守卫触发）。修复：改为链表节点图，分支末句 next 直指合并主线。
2. **Windows 瞬时文件占用**：快速连续原子写会话 JSON 时 os.replace 偶发 PermissionError（杀毒/索引瞬时占用）。修复：JsonSessionRepository.save 增加小退避重试（5 次，保原子写语义）。

## 已知限制（接受项）

见 docs/17 §3（评审稿内容、无音效、立绘占位、叙述行过渡、SC02 自由聊天段未实现、AUTO 粒度）。

## 补充3（差分立绘接线，2026-08-21）

| # | 用例 | 结果 |
|---|---|---|
| 22 | 素材入库盘点：DeepSeek main+8 差分、Claude main+7（含 serious）、ChatGPT main+8；旧中文名 deepseek_开心 / claude_shengqi 统一为 happy / angry 并删除 | PASS |
| 23 | asset-resolver 差分映射单测 6 例（差分命中 / 404 回落 main / neutral 不探测 / 在途去重 / 结果缓存 / 未知角色 legacy 回退） | PASS |
| 24 | 前端全量回归：typecheck + test:unit（54 单测全绿，GameRoleAvatar 既有用例补 resolver mock）+ 生产构建 | PASS |
| 25 | 本机 docker 栈（重建镜像）完整冒烟：首个登台立绘 URL = /char/deepseek/pic/deepseek_surprised.png；3 选项 + 结局 + 返回标题全通 | PASS |
| 26 | 4xx 全量诊断（完整剧本走查）：仅 doubao_embarrassed.png 404（预期——豆包无立绘，回落占位图）；deepseek / claude 全部差分命中 | PASS |
| 27 | 视觉核验（glm-4v-flash）：05-portrait.png 显示 DeepSeek「惊讶」差分立绘（眼睛睁大），完整无裁切、无破图黑屏 | PASS |
| 28 | 服务器部署（bundle d2b27c8）：重建 backend / frontend 镜像并重启，deepseek_embarrassed / claude_serious 经 nginx 均 200，health 200 | PASS |
| 29 | 公网完整冒烟（http://114.55.133.96）：首个登台立绘 = deepseek_surprised.png，3 选项 + 结局 + 返回标题全通 | PASS（evidence-public/） |
| 30 | 公网截图视觉核验（glm-4v-flash）：立绘完整、惊讶表情差分正确，无异常 | PASS |

实现：asset-resolver.ts 接入 emotion → {角色}_{emotion英文id}.png 差分映射（编程式 Image 探测 + 模块级缓存与在途去重，404/加载失败回落 main 单图，组件不感知资源细节）；豆包补图后无需改代码自动生效。docs/17 §3.2 / §6.2 / §6.3 同步更新。

## 补充4（结局后自由聊天 + 场景演出接线 + 旧玩法入口，2026-08-21）

| # | 用例 | 结果 |
|---|---|---|
| 31 | 故事会话直接进 /api/chat：全流程走完（176 advance / 3 choose / 14 场景边界）后 POST /api/chat 连续两轮均 200、character=deepseek、历史上下文延续 | PASS |
| 32 | 演出配置 fail closed：SCENE_PRESENTATION 未知场景 / 未知效果 / 非法光照均拒绝启动（pytest 3 例）；scene_info 已知/未知场景行为（2 例） | PASS |
| 33 | 故事视图携带 scene（标题 + presentation）+ story_progress（游标/finished）（pytest 2 例）；后端全量回归 434 passed | PASS |
| 34 | 前端全量：typecheck + 57 单测（含 saveTargetRoute 3 例）+ 生产构建 | PASS |
| 35 | 本机 docker 冒烟：场景标题卡「Awakening」出现、SC05/SC14 glitch 脉冲捕获（glitchSeen=true）、3 选项 + 结局、结局→「继续聊天」→ /game 成功、返回标题 | PASS |
| 36 | 视觉核验（glm-4v-flash）：06 标题卡（半透明、居中「Awakening」）/ 07 glitch 扫描线与故障纹 / 08 自由聊天界面（输入框 + 立绘 + 行动/系统菜单/返回标题） | PASS |
| 37 | 存档路由：故事存档 → /story、结局后/旧玩法存档 → /game（单测 + load 响应新增 story_cursor/story_finished） | PASS |

实现：结局后自由聊天复用旧 /game 全链路（零剧情新增）；SCENE_PRESENTATION 与台词分离；ScreenEffects / SceneTitleCard 新组件；标题画面「AI 对话玩法」正式入口。AI 仅 DeepSeek（用户决策）；服务器未配 DEEPSEEK_API_KEY 时为 mock 回复。

## 下一步

1. 部署到服务器（重建镜像 + 公网复核）；
2. 等用户提供 DEEPSEEK_API_KEY 后写入服务器环境变量，真实 AI 回复联调；
3. 豆包立绘（至少主立绘 + embarrassed）到位后替换占位图；
4. 场景背景图（SC03 亮/暗版等，docs/17 §6.1）待用户补充。
