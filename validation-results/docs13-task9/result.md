# docs/13 Task 9 — 视觉回归与 Vue Cutover

**状态：PASS**（附已知限制）
**日期：2026-08-19**
**范围：** docs/13 Task 9（§26 测试要求 / §27 UI 达标 / Cutover 8 条件）：AGPL LICENSE 补全 → 旧前端迁移 `frontend-deprecated/` → Docker Compose 生产资源路径修复 → Vitest 组件测试（§26.1）→ backend 补缺测试（§26.3）→ Playwright 视觉回归基线（§26.2）→ 新旧视觉对比证据 → E2E 第一章主线（§26.4）→ result.md + 归档 98/99 + commit。

**术语（用户 D7/D8 裁决，全文遵守）：** 本项目**不存在 React**；新前端是 `frontend-vue/`（Vue 3），旧前端是 vanilla HTML/CSS/JS。docs 中残留的 "React" 属文档漂移。本任务一律称 **Vue Cutover** / 「旧前端 / vanilla 前端」。

## 1. 完成了什么

**Step 1 — AGPL notice 补全（Cutover 条件「AGPL notice完成」）**：新增根目录 `LICENSE`（gnu.org 官方 AGPL-3.0 全文，34,523 字节）；`THIRD_PARTY_LICENSES.md` 第 32 行去掉将来时（「将存放」→「存放」）。`LICENSE` + `NOTICE.md` + `THIRD_PARTY_LICENSES.md` 三件齐全。

**Step 2 — Cutover 机制**：`git mv frontend frontend-deprecated`（保留参考与回退，D1）；Vue 资源路径改指 `/frontend-deprecated/public/characters/`（`asset-resolver.ts`、`api/assets.ts`）；`vite.config.ts` dev proxy 增加 `/frontend-deprecated`；`.dockerignore` 删除失效的 `frontend/` 条目并保留 `frontend-deprecated/` `char/` `backgroud/` 进 build context；`backend/app/main.py` 文档串 URL 同步。旧前端 8 个 `.cjs` 测试在移动后全部可运行（相对路径 `require("../app.js")` 不受影响）。

**Step 3 — Docker Compose 生产资源路径修复（用户 D5：不得放过，必须修复并实测）**：`backend/Dockerfile` 把 `char/` `backgroud/` `frontend-deprecated/` 拷进容器根（容器内 `REPO_ROOT` = 容器根 `/`，与 dev 仓库根挂载语义一致）；`frontend-vue/nginx.conf` 增加三棵资源路径的反代（`proxy_pass $backend` 无尾路径保留完整 URI）。`docker compose up --build` 实测 5 个 URL 全部 200，`docker compose down` 干净退出。

**Step 4 — Vitest 组件测试（§26.1）**：新增 devDeps `vitest` / `@vue/test-utils` / `happy-dom`（§26.1 直接理由）；独立 `vitest.config.ts`（不加载 tailwind 插件与 dev proxy）；6 个 spec 共 16 用例，覆盖 §26.1 全部 12 项（0/1/2/3 角色、show/hide、emotion 动画、thinking 占位+输入/发送禁用、长文本打字机、输入禁用、Save Slot 空/占用、Continue 无存档禁用）。

**Step 5 — Backend 补缺（§26.3）**：`test_json_upsert_is_atomic_on_replace_failure`（monkeypatch `os.replace` 失败 → 旧存档内容不变、无残留可读 .json）；`test_investigation_gates_behave_identically_after_load`（EV01 → 普通回合×2 确定性 Gate → Claude → EV04/EV05 → INF01 → 存档 → Load → 推理重复提交 `ALREADY_ACCEPTED`、`pre_0317_player_turns==2`、hotspot `completed` + `ALREADY_COMPLETED`、deepseek+claude 在场）。

**Step 6 — Playwright 视觉回归（§26.2）**：`@playwright/test` + chromium（直连被墙，经交接文档备用本地代理下载）；`playwright.config.ts`（1366x768 / 1920x1080 双 project、webServer 自动拉起 backend(GAL_PROVIDER=mock)+vite）；6 场景 × 2 viewport = **12 张基线入库** `tests/visual/baselines/`。03:17 一律走确定性 Gate（普通回合×2，测试内断言消息不含 03:17 字样，D6）。

**Step 7 — 新旧视觉对比证据**：旧前端（vanilla）可渲染的 3 场景 × 2 viewport = **6 张证据** 存 `validation-results/docs13-task9/evidence/old-frontend/`。旧前端无 Title Screen / Save-Load 面板——该缺失本身即 Vue 优势证据（不强行补拍）。

**Step 8 — E2E（§26.4）**：`tests/e2e/ch1-main-line.spec.ts` 完整走 §7.2 验收链路（Title → New Game → Opening → 输入 → 回应 → 调查纸 EV01 → 普通回合×2 → 03:17 自动发生 → Claude 出现 → 手动 Slot 1 → 「继续」改变状态 → 返回标题 → Load Slot 1 → 恢复断言：新 session ≠ 旧 session、双立绘在场、恢复台词为存档时 03:17 序列末行而非「继续」回合、`/api/game/state` 权威确认 hotspot 恢复 `completed`）。

**Step 9 — 收尾**：本文件 + `docs/98` `docs/99` 归档至 `docs/abandon/` + 单次 commit（显式路径，不 push；CLAUDE.md 在途修改未纳入）。

**docs 漂移最小修正（用户确认范围）**：docs/13 的 Task 9 章节标题「React Cutover」→「Vue Cutover」、Cutover 条件、§7 标题与正文、§33.6 清单中直接相关的 "React" 表述 → 「旧前端（vanilla）」。

**执行中发现并修复的 3 个真实 bug（测试的额外产出）**：

1. **backend `gameview_state` 的 `history` 是裸数组**，与前端 `LoadResult` 契约（`{session_id, messages}`，docs/13 §20.3）不符 → Load 后最后一句台词无法恢复显示（Task 8 浏览器验收未覆盖到「恢复台词」这一断言）。修复为与 `GET /api/chat/history` 同形，并在 §26.3 测试锁定契约。
2. **frontend `GameView` 三处播放路径（opening / session restore / Load 恢复）的 `setInputMode(false)` 把刚设置的 `status:'streaming'` 覆盖成 `'thinking'`** → 打字机永不启动（此前 opening 只是靠 `reconcileStage` 偶然改写 status 才没暴露）。修复：播放路径只保留 `mode:'ai'` + `status:'streaming'`。
3. **`deduction.py` 缺少幂等闸门**：已接受的推理重复提交会重放副作用。新增 `ALREADY_ACCEPTED` 返回（§26.3「investigation gates after load」所需语义）。

（批 B 另有配套最小修复：`lingchat-compat.ts` 的 `currentStatus` 从不返回 `'thinking'` → GameDialog 思考占位/输入禁用/发送禁用永不生效，按权威 `presentation.state.status` 区分后生效；该修复正是暴露 bug 2 的触发条件。）

## 2. 修改了哪些文件

- 新增：`LICENSE`；`frontend-vue/vitest.config.ts`、`frontend-vue/playwright.config.ts`；`frontend-vue/tests/visual/`（fixtures.ts、vue-visual.spec.ts、old-frontend.spec.ts、baselines/ 12 张 PNG）；`frontend-vue/tests/e2e/ch1-main-line.spec.ts`；`frontend-vue/src/components/game/standard/__tests__/`（fake-image.ts + 3 spec）、`frontend-vue/src/components/save/__tests__/`（2 spec）、`frontend-vue/src/views/__tests__/TitleView.spec.ts`；`validation-results/docs13-task9/evidence/old-frontend/` 6 张 PNG；`docs/abandon/98-…`、`docs/abandon/99-…`（git mv）
- 修改：`THIRD_PARTY_LICENSES.md`、`.dockerignore`、`backend/Dockerfile`、`backend/app/main.py`（注释）、`backend/app/game/deduction.py`、`backend/app/game/orchestrator.py`、`backend/tests/test_save_repository.py`、`backend/tests/test_save_service.py`、`frontend-vue/nginx.conf`、`frontend-vue/package.json`、`frontend-vue/package-lock.json`、`frontend-vue/tsconfig.json`、`frontend-vue/.gitignore`、`frontend-vue/vite.config.ts`、`frontend-vue/src/adapters/asset-resolver.ts`、`frontend-vue/src/adapters/lingchat-compat.ts`、`frontend-vue/src/api/assets.ts`、`frontend-vue/src/views/GameView.vue`、`docs/13-LingChat前端源码迁移、开始界面与存档系统落地方案.md`
- 重命名：`frontend/` → `frontend-deprecated/`（git mv，含 8 个 `.cjs` 测试）；`docs/98-…`、`docs/99-…` → `docs/abandon/`

## 3. 如何验证

```bash
cd /d/gal/backend && GAL_PROVIDER=mock .venv/Scripts/python -m pytest -q      # 371 passed, 12 skipped
cd /d/gal && for f in frontend-deprecated/tests/*.cjs; do node "$f"; done   # 8/8 exit 0
cd /d/gal/frontend-vue && npm run test:unit                                # 6 files / 16 tests PASS
cd /d/gal/frontend-vue && npm run typecheck && npm run build                # PASS / PASS（134 modules）
cd /d/gal/frontend-vue && npx playwright test tests/visual --update-snapshots  # 首次建基线 18/18
cd /d/gal/frontend-vue && npm run test:visual                               # 对比模式 18/18 PASS
cd /d/gal/frontend-vue && npm run test:e2e                                  # 2/2 PASS（1366x768 / 1920x1080）
cd /d/gal && docker compose up --build -d                                   # 三服务 healthy
  curl :8080/char/... :8080/backgroud/... :8080/frontend-deprecated/... :8080/api/chat/opening→history  # 全部 200
cd /d/gal && docker compose down
```

### §26.1 Frontend Unit / Component（16 用例）

| 用例 | 覆盖项 |
|---|---|
| `GameRolesStage.spec.ts`（5） | 0/1/2/3 角色渲染数量与顺序、visible=false 移除（show/hide） |
| `GameRoleAvatar.spec.ts`（2） | emotion 变化应用动画类（happy-bounce）、show=false → opacity 0 |
| `GameDialog.spec.ts`（3） | thinking 占位「思考中…」+ textarea 只读 + 发送禁用；responding 只读→input 可输入；长文本 fake timers 完整显示 |
| `SavePanel.spec.ts`（2） | 全空槽 6×「空存档位」+「暂无自动存档」；占用槽标题 + 「第一章 · 调查」 |
| `LoadPanel.spec.ts`（2） | 全空槽 6×「暂无存档」；占用槽点击 emit load(存档 id) |
| `TitleView.spec.ts`（2） | 无存档 Continue 禁用 / 有存档启用 |

### §26.2 Visual Regression（18 = 12 基线对比 + 6 旧前端证据，双 viewport）

场景：TITLE_EMPTY_SAVE / OPENING_DEEPSEEK_ONLY / CLAUDE_APPEARS_TWO_ROLE / LONG_DIALOGUE / SAVE_PANEL / LOAD_PANEL。旧前端：OPENING_DEEPSEEK_ONLY / CLAUDE_APPEARS_TWO_ROLE / LONG_DIALOGUE。全部 PASS，基线可复现（对比模式 2.8m 内 18/18）。

### §26.3 Backend Save Tests（2 新增）

| 测试 | 断言 |
|---|---|
| `test_json_upsert_is_atomic_on_replace_failure` | `os.replace`（唯一提交点）失败 → 抛错、旧存档内容不变、`list_by_player` 不受影响、无残留可读 `.json`（all-or-nothing，docs/13 §18） |
| `test_investigation_gates_behave_identically_after_load` | 推进态存档 → Load 新会话：INF01 重复提交 `ALREADY_ACCEPTED`（不重放副作用）、`pre_0317_player_turns==2`、CH1_NOTE_01 仍 `completed` 且重复检查 `ALREADY_COMPLETED`、`available_characters ⊇ {deepseek, claude}`；并锁定 Load 返回的 history 契约（最后一条角色台词 = 03:17 序列 DS 行） |

### §26.4 E2E（2/2，双 viewport）

全部玩家消息断言不含 03:17 token（确定性轮数兜底 Gate，D6）；恢复断言：新 Active Session（§19.1）、双立绘在场、恢复台词 = 存档时的 `……你、你怎么会在这里？！`（非「继续」回合回应）、权威 `hotspots.CH1_NOTE_01 == 'completed'`。

## 4. Cutover 8 条件核对

| 条件 | 结果 | 证据 |
|---|---|---|
| Vue 视觉显著优于旧前端 | ✅ | §5 对比表 + GLM 目检：旧前端背景明显白边、立绘过大未居中；旧前端无 Title/Save/Load 面板 |
| 第一章主线可运行 | ✅ | E2E 2/2（§7.2 验收链路，确定性 Gate 触发 03:17） |
| Save/Load 可运行 | ✅ | Task 7/8 已 PASS + §26.3 补缺测试 + E2E Save/Load 断言 |
| backend tests 通过 | ✅ | 371 passed / 12 skipped（GAL_PROVIDER=mock） |
| Vue build 通过 | ✅ | `npm run typecheck` + `npm run build`（134 modules） |
| 无 Tauri 依赖 | ✅ | `frontend-vue/src` 中 `@tauri-apps/convertFileSrc/invoke(` 0 实际调用（仅 5 处「已移除」说明注释）；package.json 无 tauri 依赖 |
| AGPL notice 完成 | ✅ | `LICENSE`（AGPL-3.0 全文）+ `NOTICE.md` + `THIRD_PARTY_LICENSES.md` |
| Docker Compose 指向 Vue | ✅ | compose 三服务已指向 Vue；生产资源路径本任务修复并 `docker compose up --build` 实测 5 URL 全 200 |

## 5. 新旧视觉对比（Task 2 验收标准）

目检辅助：ds-vision-skill（glm-4v-flash）；截图路径见 §9。

| Task 2 验收项 | 旧前端（vanilla） | Vue |
|---|---|---|
| 背景无白边 | ❌ 明显白边/空白区域 | ✅ 铺满无白边 |
| 立绘大小/脚底基线合理 | ⚠️ 立绘过大、未完全居中，观感接近占位图 | ✅ 单角色居中、基线合理 |
| 单角色居中 | ⚠️ 未完全居中 | ✅ 居中 |
| 双角色稳定左右布局 | ✅ 左右分列不重叠 | ✅ 左右分列、间距合理不重叠 |
| 表情切换不闪白 | ⚠️ 单图直接替换（无交叉淡入） | ✅ RoleSprite 双叠 cross-fade（Task 2 验证） |
| fade 无 layout jump | — | ✅ 冻结动画下截图稳定复现（基线对比 18/18） |
| Dialogue 不遮脸 | ✅ | ✅（GLM 逐张确认） |
| 无 LingChat 文案 | ✅ | ✅（GLM 逐张确认） |
| Title Screen / Save / Load | ❌ 无此界面 | ✅ Title + 系统菜单 + Save/Load 面板 |

## 6. 结果

**PASS。** Task 9 全部 9 个 Step 完成：AGPL 补齐、旧前端迁移 `frontend-deprecated/`、Docker 生产资源路径修复并实测、§26.1/§26.2/§26.3/§26.4 四类测试全部通过且可复现（backend 371/12、Vitest 16/16、Playwright 视觉 18/18、E2E 2/2、build PASS），Cutover 8 条件全部满足；额外修复 3 个真实 bug（Load 台词恢复契约、GameView 播放态 status 覆盖、推理幂等闸门）。Vue 成为默认前端，旧前端移入 deprecated archive，双前端维护结束。

## 7. 失败与修复记录（调试过程，非产品缺陷）

1. Playwright webServer backend 命令 `.venv/Scripts/python` 在 cmd 下不识别 → 改 `.venv\\Scripts\\python.exe`。
2. 「调查纸按钮在拓印后消失」假设错误：后端 `available_hotspots` 保留已完成热点供复查（docs/12 §41）→ 断言改为拓印消息 + 权威 API 状态。
3. 旧前端拓印覆盖率：初始扫动只覆盖右列（阈值 28×15×0.38≈160 格）→ 蛇形扫动 + 达标早退。
4. `freezeClock` 冻结 `Date.now()` 导致所有超时判断死循环 → 移除（存档面板时间戳差异远小于 2% 像素容差）。
5. mock AI 回声逐字回显上下文（极长）→ AI 回合只等「开始打字」即推进；确定性 script 行用 `waitTyped` 精确比对。
6. 系统菜单打开后存在两个「返回标题」按钮（顶栏 + 菜单）→ 用 `.sys-menu-btn` 精确定位。

## 8. 已知限制

- **调查主线 UI 未建（D4，明确搁置）**：证据面板 / 推理 / 私审 / 收尾 / 其余 3 个 hotspot 在 frontend-vue 无实现；后端已充分测试；旧前端保留在 `frontend-deprecated/` 作参考；后续用 LingChat 选项功能实现。
- **docs 其余 "React" 漂移未修**（用户限定最小范围）：docs/13 的 §0/§1/§2/Task 0/§32/§34/§35 等处仍称旧前端为 React；CLAUDE.md / AGENTS.md 未动（CLAUDE.md 有用户/编辑器在途修改）。
- **Postgres 存档接线未成为已验证运行路径**：compose 实测按用户确认的最小范围（资源路径 4 URL + opening/history），`GAL_SAVE_BACKEND=postgres` 的读写留待后续任务。
- **SAVE_PANEL 在 768 高度下 5/6 号位需滚动**（面板 85vh 设计内，非缺陷）。
- **Title「继续游戏」禁用为 opacity 0.45**，视觉差异细微（DOM 级 `toBeDisabled` 已断言）。
- **视觉目检为 GLM 视觉模型代理**：本会话主模型无图像输入，逐张检查由 ds-vision-skill（glm-4v-flash）完成；截图路径见 §9，建议人工抽看双角色与旧前端对比图。
- **Playwright chromium 经本地代理下载**（直连 googleapis 被墙）；CI 环境需自行配置浏览器下载渠道。
- **旧前端 URL 变更**：`/frontend/` → `/frontend-deprecated/`（dev 后端仓库根静态挂载直接可服务；compose 经 nginx 反代）。

## 9. 证据

Vue 基线（入库）：`frontend-vue/tests/visual/baselines/visual/vue-visual.spec.ts-snapshots/` 下 12 张 PNG（TITLE-EMPTY-SAVE / OPENING-DEEPSEEK-ONLY / CLAUDE-APPEARS-TWO-ROLE / LONG-DIALOGUE / SAVE-PANEL / LOAD-PANEL × desktop-1366x768 / desktop-1920x1080）。

旧前端证据：`validation-results/docs13-task9/evidence/old-frontend/` 下 6 张 PNG（OPENING_DEEPSEEK_ONLY / CLAUDE_APPEARS_TWO_ROLE / LONG_DIALOGUE × 双 viewport）。

交接文档归档：`docs/abandon/98-最新决策与信息-2026-08-19.md`、`docs/abandon/99-临时交接文档-2026-08-19.md`。
