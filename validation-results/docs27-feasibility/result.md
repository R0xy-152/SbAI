# docs/27 可行性探查 — 「她的世界」记忆横版 + Monika 觉醒 + P0-2 真机管线

> **状态：** PASS（核心问题全部获得可复现证据；限制见 §7）
> **日期：** 2026-09-05
> **环境：** macOS / Node v24.18.1 / Vite v6.4.3 / Python 3.12 / Playwright（无头 Chromium，1366×768）/ DeepSeek 真机（`deepseek-v4-flash`，`backend/.env` 已有 key）
> **对象：** docs/27 §8「她的世界」、§7 Monika 觉醒、docs/25 P0-2 评测真机管线（T5 Spike 的退出条件验证）
> **原型性质：** throwaway，全部文案 Fixture，不接任何后端状态；路径 `/prototype/world?variant=A|C|D`（`meta.public`），文件带 `PROTOTYPE` 标注，合并前整目录删除。

## 0. 结论

三块风险的桌面可行性全部成立：**记忆横版 GO**（120fps、约束式文字地形、问答门、三分岔、镜头移交、倒放全通），**Monika 觉醒演出 GO**（纯 DOM/CSS 零风险），**P0-2 评测真机管线 GO**（真实 DeepSeek 全链路跑通，可立即全量 40 条）。未发现需要回退到「记忆问答对决」备选方案的阻塞项。

## 1. 原型交付物

| 文件 | 用途 |
|---|---|
| `frontend-vue/src/views/prototype/WorldPrototype.vue` | 宿主：`?variant=` 切换 + 底部切换条（←/→）+ reduced 档 + 觉醒演出入口 |
| `frontend-vue/src/views/prototype/VariantA.vue` | 变体 A 浮岛横版（主候选）：文字地形/走跳/两门/三分岔/倒放/镜头移交 |
| `frontend-vue/src/views/prototype/VariantC.vue` | 变体 C 记忆长廊（无跳跃备选，结构性对比） |
| `frontend-vue/src/views/prototype/VariantD.vue` | 变体 D 三扇门（最小回退，零物理） |
| `frontend-vue/src/views/prototype/AwakeningSequence.vue` | Monika 觉醒：立绘突破图层 →「我不喜欢这样」→ UI 飞块 → 黑屏虚空 |
| `frontend-vue/src/app/router/index.ts` | 新增 `/prototype/world`（2 行，标注 throwaway） |
| `frontend-vue/scripts/world-prototype-smoke.mjs` | Playwright 全流程冒烟（截图+HUD+错误收集） |
| `frontend-vue/scripts/world-prototype-pixels.mjs` | 像素级渲染验证（不依赖目视） |

运行方式：`npm run dev` → 打开 `http://localhost:5173/prototype/world?variant=A`。

## 2. 逐问题结果

| # | 探查问题 | 结果 | 证据 |
|---|---|---|---|
| Q1 | 文字地形可读性 + 约束式自动布局 | **PASS** | 约束生成器（垂直落差≤130px、水平间距 130~280px、mulberry32 seed=20260905）产出可跳布局；像素采样 `litRatio=8.1%`、中带文字区 `textZoneRatio=0.34%`；**图像模型目视确认改版后文字平台清晰、夜空渐变+地平线微光+地表亮线+星点，冷黑记忆虚空身份成立**（evidence/01、05） |
| Q2 | 手写 AABB 走/跳手感与帧率 | **PASS** | 无头 Chromium 桌面：开局 83fps、行进 106fps、门/分岔处 120fps；走/跳/落地/坠落重生按预期（`hud-log.txt`）。参数为初值（g=2300、跳速=-840、上限270px/s），触屏与真机手感待 T5 实机调 |
| Q3 | 问答门（gate_q1 三选项 / gate_q2 三桶+自由输入） | **PASS** | 两门均在正确 x 触发并记录选择：`gate1=①你说过下雨忘带伞`、`gate2=原词：永远`；推进无死路 |
| Q4 | 三分岔：REFUSE 镜头移交 / RESET 倒放 / RELEASE 出口 | **PASS_WITH_LIMITATION** | REFUSE：cam 从 4149 追至 5257 跟随她（her 5080→5825），**镜头移交机械表达成立**；RESET：phase=rewind 逐帧回退正常 + UI 重装闪帧；RELEASE 与 REFUSE 共用 her 出屏路径（未单独截图，代码同路径） |
| Q5 | 减少动态效果档（reduced） | **PASS** | `?reduced=1` 下世界降速可玩（97fps），觉醒演出改静态溶解（CSS `[data-reduced]`） |
| Q6 | Monika 觉醒演出（立绘突破+UI 丢弃+黑屏） | **PASS** | DOM/CSS 全流程：图层突破（z-index 55000+缩放+光晕）→ 台词切换 → UI 逐块飞出 → 黑屏虚空 → 进入世界；0 个前端 console 错误（见 §7-2） |
| Q7 | 备选变体（长廊 / 三扇门） | **PASS** | C 长廊 60fps 可玩（60 为 60Hz 垂直同步上限，非性能问题）；D 三扇门纯 DOM 成立 |
| Q8 | P0-2 评测真机管线 | **PASS** | 见 §3 |

## 3. P0-2 评测真机 smoke

- 聊天面（`--cases ch-ins-01`，真实 DeepSeek）：v1/v2 双版本生成 + 硬规则 1/1 + LLM 评委三维（relevance 0.90 / naturalness 0.80 / persona 0.90，n=1）+ 运行指标：**生成延迟≈4.7s、评审延迟≈3.4s、成本≈¥0.0049/条**；逐行 JSONL 落盘 `eval-smoke-rows.jsonl`。
- 判定面（`--cases ded-eq-01`，真实 TrialRuntime，无需 API）：legacy 1/1、revised 1/1、分歧 0 条（该用例非缺陷样例，符合预期）。
- 全量 40 条预算估算：约 80 次生成 + 40 次评审，串行约 15 分钟、成本约 ¥0.2~0.5；可随时执行。

## 4. 冒烟流程记录（hud-log.txt 摘要）

```
A 起点:  fps=83  x=306  phase=run
A 行进:  fps=106 x=1068 phase=run
A gate1: fps=118 x=1861 phase=gate1
A gate2: fps=120 x=3262 phase=gate2 gate1=①…
A 三分岔: fps=120 x=4540 phase=fork
A REFUSE: fps=120 cam=5257 her=5825   ← 镜头已移交给她
A RESET:  phase=rewind cam=4107        ← 倒放中
C 长廊:   fps=60 d=512
A reduced: fps=97 x=527
```

截图证据 14 张：`validation-results/docs27-feasibility/evidence/01~14-*.png`（起点/行进/gate1/gate2/三分岔/REFUSE/RESET/觉醒×3/长廊/三扇门×2/reduced）。

## 5. 失败记录

- 首轮冒烟在 gate2 处超时：脚本在 gate1 点击后未等面板卸载即检测到残留 `.gate-panel` 而 break。归因：**测试脚本时序**，非原型缺陷。修复：点击后 `waitForTimeout(700)` + `waitForSelector` 检测。复跑全绿。
- 无。

## 6. 已知限制

1. **世界审美为「冷黑记忆虚空」方向（已确认成立）**：文字平台画面对比度在改版后已提升（夜空渐变/地平线光/地表亮线/星点 + 近白文字带描边投影）；若需更暖、更丰富的世界（更密平台、向出口的冷暖色渐变、更多粒子），属风格取舍，可在 T3 迭代。
2. **触屏/真机手感未验**：本探查为桌面 Chromium；移动端触控、低端机帧率按 docs/27 §8.7 需在 T5 实机验证。
3. **地形数据契约未验**：原型用 Fixture 文本数组；真实实现的地形文字来自 Backend 会话数据（`terrain_text[]` 契约），该数据流不在本次探查范围。
4. **RELEASE 未单独截图**：与 REFUSE 共用 her 出屏代码路径。
5. 冒烟中 8 条 `500` 错误已确认来源：后端未启动时 app shell 的 `POST /api/auth/restore`（curl 实测 500），与原型无关；原型自身 0 console 错误。
6. 变体 C 的 60fps 为 60Hz 显示器垂直同步上限。
7. 冒烟脚本 OUT 曾因相对路径两次落到 `frontend-vue/validation-results/`，已修正为基于脚本位置（`fileURLToPath(new URL('../../…', import.meta.url))`），并已把证据归位到 `validation-results/docs27-feasibility/evidence/`。

## 7. Go/No-Go

- **记忆横版（变体 A）：GO**。进入 T5 接线阶段；接线前需定：Backend `terrain_text[]` 契约、触屏控制方案、门/结局 Event 提交协议。
- **Monika 觉醒演出：GO**，实现成本低，可直接进 T3 前端批次。
- **P0-2 评测：GO**，可立即跑全量真实对比（T1）。
- 备选（长廊/三扇门）保留为 Spike 回退资产，暂不删。

## 8. 清理与捕获

- 原型文件均标注 `PROTOTYPE / throwaway`；路由 2 行标注注释。正式并入前整目录 `frontend-vue/src/views/prototype/` 与两个 scripts 从主分支移除，按 prototype 技能约定转存 throwaway 分支（当前工作区有大量未提交改动，未代为提交；指针记录于本文）。

## 9. 开场媒体同步接线验证（2026-09-05，本地）

将「视频特写 + Aira 音乐」接进开场（`TRIAL_OPENING` scene 增加 `video/poster/music`；`TrialSceneSnapshot` 增加同步起播）。验证（本机 vite:5173 + backend:8000）：

- **素材服务**：`/backgroud/kei_opening_720p.mp4`/`aira_full.m4a`/`kei_opening_poster.png` 均 200（后端 StaticFiles）。
- **视频**：`videoPaused=false`、`currentTime≈3.9s`、`readyState=4`、`duration=116.67s`（自动播，muted loop）。
- **音频**：进入时自动播放被策略拦（`audioPaused=true`），**首次交互后起播**：`audioPaused=false`、`currentTime≈1.24s`、`duration=136.14s`——与视频「同时出场」（首交互兜底）。
- **遮蔽**：开场遮蔽块隐藏，露出特写视频中的她；底部对话框显示遮蔽名 + 台词正常。
- `npm run typecheck` 全绿；试玩内容测试 15 passed。
- 1 条 console 401 来自 app-shell 的 `auth.restore()`（public 路径仍调用鉴权，环境性、非媒体问题）。
- 证据：`evidence/15-媒体同步-开场.png`。
- **未上传/未部署**：kei 视频、Aira 音频、poster 均已 `.gitignore`（`backgroud/kei_opening*.mp4`、`backgroud/kei_opening_poster.png`、`backgroud/aira_full.m4a`）；backend 与 vite 仅本机运行，验证后已关闭。
- 待办：异常冻结帧作为四片玻璃裁切源（docs/27 §7.1 的 live2d 冻结帧替代，本批仅完成「视频+音乐同步起播」，冻结帧留到接线 shatter 时）。

## 10. 异常冻结帧喂四片玻璃（2026-09-05，本地 PASS）

- 机制：`components/trial/mediaFrame.ts`（模块级冻结帧缓存）；`TrialSceneSnapshot` 在直播视频期间约 260ms 捕获当前帧（drawImage→JPEG dataURL，960 宽）并在卸载时捕获末帧；`ShatterPuzzle` 挂载时读取冻结帧，通过 `frozen` prop 让四片（含发光底图）共用**同一张冻结图**。
- 验证（/prototype/shatter，真实组件）：直播视频播放 t=3.2s → 触发碎裂 → **碎裂区 0 个实时视频、4 片、uniqueSrcCount=1（四片同一 data:image/jpeg）**、底图目标也用冻结帧；typecheck 全绿。
- UI 复用：碎片/物理/拼合/提示条全部是现役 ShatterPuzzle 与 TrialSceneSnapshot（含对话框）；仅背景源由「实时视频」替换为「冻结帧」。
- 证据：`evidence/16-冻结帧-碎裂.png`。

## 11. 开场碎片节拍落地（2026-09-05，PASS）

- 用户定稿开场流程：夜色真美 → 回应（是啊）→ 画面碎裂 → 拼好碎片 → 「一定要记得我」→ 获得碎片 → 警告停止服务。
- content.py：`opening_warm_chat`「夜色真美」、`opening_origin_ai_remains`「一定要记得我」（用户提供，非 Fixture）；输入引导改为「【Fixture】回应她。」；异常拍为 Fixture 闪烁描述；`service_stop_modal.message` 改为「警告：AI 停止服务」。
- Token：`RING` → **`FRAGMENT（碎片）`**（`TOKENS=("FRAGMENT",)`、`FRAGMENT_ACQUIRED`、停止服务幂等授予）；前端「已获得：碎片」。
- 运行时驱动全流程逐拍输出与用户流程一致（上面【1】~【6】）；pytest 22 passed（含改名 `test_trial_flow_redacts_origin_ai_and_commits_fragment_once`）；typecheck 全绿。
- 连贯性：拼合后 `opening_origin_ai_remains`/`opening_service_stopped` 用冻结帧（`postBreakFrozen`），避免视频从头循环；碎裂拼图复用现役 ShatterPuzzle。

## 12. 本地免登录测试（2026-09-05，PASS）

- 前端：`router/index.ts` guard 顶部加 `if (import.meta.env.DEV) return true`（**仅 Vite dev**；线上构建 `import.meta.env.DEV=false`，登录逻辑不变）。
- 后端：`GAL_AUTH_REQUIRED=false`（或 0/no）启动即启用既有 `auth_disabled` 机制（固定本地用户 test-user + quota 1M；authz 的 require_owned_session/bind_session/current_user_id 均放行）；线上默认 `true` 不受影响。
- 验证：`http://localhost:5173/trial` 免登录直达 → 点「开始试玩」→ **视频播放、音乐播放、对话「夜色真美」**（video/audio 均 !paused，无 pageerror）。证据：`evidence/17-trial-免登录开场.png`。
- 运行方式已记入 AGENTS.md 常用命令。

## 13. 对话框复用序章 GameDialog（2026-09-05，PASS）

- 移除 `TrialSceneSnapshot` 自造的 `.trial-snapshot__dialogue`（含 node prop 与相关样式）；碎片拼图不再逐片渲染对话框。
- `TrialView` 渲染序章现役 `GameDialog.vue`：节点经 `setDialogueLine(presentation.state, …)` 写入（`speakerName`=遮蔽 label ████、emotion 清空避免「中性」标签、`status='streaming'`）；`text_input` 阶段切 `status='idle'`+`mode='script'` 进入可输入态。
- 事件接线：`@dialog-proceed`→`advance()`（推进）、`@player-continued`→`onPlayerContinued`（输入；空参推进路径已守卫）。
- 移除自造 `.trial-input` 表单与带台词阶段的 `.trial-advance` 按钮（仅 `not_started` 无台词时保留「开始试玩」按钮）。
- 验证：typecheck 全绿；端到端探针——夜色真美（████+台词+▼+视频音频在播）→ 输入态（readonly=false、placeholder「输入你的台词…」）→ 输入「是啊」回车 → 异常拍；**pageerrors: none**。证据 `evidence/18-trial-序章对话框-夜色真美.png`。

## 14. 玻璃拼图必须手动拖动、不得自动拼成（2026-09-05，PASS）

- **问题**：四片玻璃在碎裂后直接自动归位，玩家来不及拖动。根因：`createShardBodies` 的散落偏移用 `nx*width / ny*height`（≈16% 视口），而 `stepShardBodies` 的吸附半径是**固定 150px**——两者单位不一致；视口宽 <≈850px 时散落距离 < 150px，四片一出生就落在弹簧吸附域内被吸回中心。
- **修复**（`shard-physics.ts`）：散落与吸附半径同源缩放（均取拼图短边 `scale = min(w,h)`）。新增 `ShardBody.snapRadius = scale * 0.18`；散落偏移改为 `nx*scale / ny*scale`（≈0.34×scale），保证任何视口下初始都落在吸附域外。`stepShardBodies` 弹簧阈值与最终锁定阈值改用 `body.snapRadius`。
- **接线同步**（`ShatterPuzzle.vue`）：`nearby` 高亮、`onPointerUp` 阻尼、键盘 Enter 归位三处阈值均改 `body.snapRadius`，与物理一致。
- **测试更新**（`__tests__/physics.spec.ts`）：`ShardBody` 字面量补 `snapRadius: 150`。
- 验证：typecheck 全绿；vitest 7/7 通过；多视口探针（1440/1280/1000/800/700）3 秒后四片均 `snapped=false`（不再自动拼成）；端到端手动逐片拖到中心 → 弹簧收敛全部锁定 → `COMPLETE_SHATTER` 被后端接受 → 阶段推进到「残存意识」，**pageerrors: none**。证据 `evidence/19-拼图-手动拖拽归位.png`。

## 15. 密室废案接入 + 拓印小游戏 + 全屏继续热区（2026-09-05，PASS）

- **范围**（用户确认）：`opening_service_stopped`（AI 停止服务警告）之后**插入**密室废案段落，再回到原有 `fragment_01_*` 推理流程（推理保留）；见三人后不结束。
- **后端**（`content.py` / `runtime.py`）：新增 2 场景（`TRIAL_LOCKED_ROOM` 复用 `background1.png` + DeepSeek；`TRIAL_LOCKED_ROOM_EXIT` + Claude/ChatGPT，复用 `char/` 现成立绘）、6 句 Fixture 台词、6 阶段（`locked_room_wake → deepseek → paper(拓印) → password(输密码) → door_open → meet → fragment_01_deepseek_intro`）。新增交互 `paper_rubbing`（`answer`=拓印密码）、`text_input` 可选 `player_input_answer` 密码校验、事件 `LOCKED_ROOM_UNLOCKED`；`_player_input` 密码不匹配抛「密码不正确…」。密码沿用废案 `03:17`（`PAPER_PASSWORD`，Fixture）。
- **前端**：`PaperRubbing.vue` 移植 `frontend-deprecated/app.js` 的石墨拓印小游戏（刮够 38% 覆盖显影密码）；`TrialView` 渲染拓印、新增阶段标签、错误详情透传（取 axios `response.data.detail`）。
- **全屏继续热区**：`TrialView` 根 `@click` 事件委托——`advance` 且有台词时点击画面任意处调 `GameDialog.triggerAdvance()`（等效 ▼）；`closest('button,a,input,select,[role=button],[role=dialog],[role=alertdialog]')` 命中则放行，不吞其它按钮/输入框/弹窗。
- 验证：后端 pytest 614 passed / 12 skipped（含新增密码门禁与拓印阶段用例 9/9）；前端 typecheck 全绿；端到端探针全流程——密室醒来→遇 DeepSeek→拓印刮出 `03:17`→错误密码报「密码不正确，再看看纸上的字。」→正确密码开门→见 DeepSeek+Claude+ChatGPT 三人立绘→回到「单人审问」推理，**pageerrors: none**。证据 `evidence/21-密室拓印-揭晓密码.png`、`evidence/22-密室开门-见三人.png`。
