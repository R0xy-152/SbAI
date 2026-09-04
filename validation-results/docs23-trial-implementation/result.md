# docs23-trial-implementation 验证记录

> **状态：** PASS_WITH_LIMITATION
> **日期：** 2026-09-04
> **分支：** `codex/trial-demo`
> **环境：** macOS / Python 3.12 / Chromium / 1200×680 桌面视口

## 目标

在独立试玩版中实现“固定开局与输入 → 四片玻璃拼合 → 戒指 → AI 停止服务 → DeepSeek 失忆推理 → 全员最终推理 → A/B 线路交接”的首个可玩闭环，同时冻结既有序章、第一章和旧调查玩法。

## 自动化验证

| 命令 / 用例 | 结果 |
|---|---|
| `backend/.venv/bin/python -m pytest -q` | PASS：595 passed，12 skipped |
| `npm run test` | PASS：87 tests；typecheck 与 production build 通过 |
| TrialRuntime 定向测试 | PASS：命名遮蔽、四片容差、戒指幂等、首次 Gate、最终无死路、双线路、Snapshot Restore |
| Trial HTTP / Save 集成测试 | PASS：认证关闭兼容、检查点 AUTO、`chapter_id=trial_v1`、Load 返回 `/trial` 所需标识 |
| 文字物理测试 | PASS：seed 确定性、等质量两体动量对称、成对切向互绕、高速预测避让、10 组 seed × 60 秒五体真实包围体无穿透、自适应降档/恢复 |
| 碎片物理测试 | PASS：四片在高精度子步下由弹簧/阻尼收敛并锁定 |

## 真实浏览器全流程

| 场景 | 结果 |
|---|---|
| 标题 → 章节选择 → 独立试玩版 | PASS |
| 原初 AI 玩家可见名 | PASS：DOM/无障碍快照均为 `████`，无正式称呼泄露 |
| 玩家自然语言输入 | PASS |
| 四块玻璃逐块 Pointer 拖动归位 | PASS：四片均经惯性/扭矩吸附，全部完成后才提交 |
| 戒指与红色“AI 停止服务”弹窗 | PASS |
| Evidence 关键词持续运动且保持水平 | PASS |
| 拖动“记忆断层”进入推理槽 | PASS |
| 第一次错误推理 | PASS：停留原节点、Evidence 不消耗、可再次提交 |
| 第一次正确推理 | PASS：进入全员集合 |
| 最终错误推理 + 身份噪点 | PASS：不形成死路，权威提交到线路 B |
| 自动存档 → 标题“继续游戏” | PASS：恢复到 `/trial` 的同一异常检查点 |
| 最终浏览器 Console | PASS：0 errors / 0 warnings（favicon 噪声与旧本地存档 400 在重启验证后消失） |

截图证据（本地、不纳入剧情真相源）：

- `validation-results/docs23-trial-implementation/evidence/01-chapter-select.png`
- `validation-results/docs23-trial-implementation/evidence/03-shatter.png`
- `validation-results/docs23-trial-implementation/evidence/04-service-stopped.png`
- `validation-results/docs23-trial-implementation/evidence/05-evidence-orbit.png`
- `validation-results/docs23-trial-implementation/evidence/06-fragment-handoff.png`
- `validation-results/docs23-trial-implementation/evidence/07-orbit-braiding.png`
- `validation-results/docs23-trial-implementation/evidence/08-drag-layer.png`

## 2026-09-04 文字天体优化复验

- 碰撞代理半径由 54px 修正为 64px，覆盖 7.2rem × 3rem 胶囊按钮的真实外接范围；
- 加入接触前最近接距离预测、对称侧向避让和中距离成对切向轨道力，所有成对力保持等大反向；
- 页面加入低开销短轨迹，真实浏览器可见连续弧线、绕行与多体交织；减少动态效果模式隐藏轨迹；
- Microsoft Edge（Chromium）1192×681 真实 DOM 连续采样 10 秒、200 个时点、每时点 10 对天体：矩形重叠 0 次，最近中心距 167.36px；
- 本次直接 Vite 验证仅有既存 `favicon.ico` 404，不影响玩法；此前完整试玩流程重启验证为 0 errors / 0 warnings。

Live2D Scope Change 同日获批并写入 `AGENTS.md`、最高优先级 Scope 与 docs/23 §18。当前只完成素材/工程准入定义，未下载 SDK、未加入依赖，也未声称完成 Live2D 验证。

## 2026-09-04 证据跨 UI 拖拽修复

- 原因：拖动坐标被夹在物理场 `width - 30px`，同时物理场 `overflow: hidden`，且拖动物没有高于推理槽的独立层级；
- 修复：Pointer Capture 期间允许证据跟随指针越过物理场，拖动态临时放开裁切并提升层级，释放后恢复场内约束；
- 同步清空/暂停该证据的轨迹采样，避免跨 UI 时产生一条贯穿页面的长轨迹；
- 新增组件回归测试，验证拖动中可越界、存在顶层拖动态、释放后清理状态并发出准确落点；
- Microsoft Edge（Chromium）真实浏览器断言：修复前 `enteredTray=false / topIsEvidence=false`，修复后均为 `true`；拖动过程中证据视觉本体位于推理槽上方，Console 0 errors / 0 warnings。

## 限制

- 剧情对白、Evidence 详情、正确组合与 A/B 映射仍是显式 Fixture，尚未获得正式内容确认。
- 原初 AI 立绘、深夜背景与部分全员素材复用现有占位资源；未制作正式美术。
- 本轮真实交互仅在桌面 Chromium 验收；触屏实机、最低配置硬件和长时间热性能仍未验证。
- 片段 2 不在本轮范围，当前只持久化到 A/B 权威交接点。
- 尚未部署线上。
