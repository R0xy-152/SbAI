# docs15 — 视觉对齐 LingChat 与动效补齐 验证记录

- **状态：** PASS
- **日期：** 2026-08-20
- **环境：** Windows · Vue 3 + Vite 6 + TailwindCSS v4（frontend-vue）· FastAPI（GAL_PROVIDER=mock）· Playwright 1.62
- **计划文档：** docs/15-视觉对齐LingChat与动效补齐落地方案.md
- **上游校准：** docs/13 §11.1 / §11.5 / §27.4 已标注第二轮落地状态

## 1. 实施摘要（每步一个 commit）

| commit | 内容 |
|---|---|
| `5e024f2` | 设置页显示特效开关（6 项）+ 全站共享皮肤 token（style.css） |
| `9f9de5d` | 全局光标拖尾/点击涟漪（CursorEffects）+ Ctrl+滚轮缩放（useZoom）+ 路由淡入过渡 |
| `262fa17` | 场景粒子组件库（StarField/Rain/Sakura/Snow/Fireworks）+ 首页流星/星星动画 |
| `71ed351` | TitleView 重构（全亮背景/流星星空/立绘视差/电影感菜单/超宽两列/CSS 文字 Logo） |
| `327543b` | 首次加载演出（LoadingTransition，New Game 专用）+ opening 缓冲应用 |
| `925d895` | 游戏内场景粒子：后端权威 background_effect（scene.py/orchestrator）+ GameBackground 粒子层 |
| `274e25b` | Save/Load/历史/系统菜单/顶部条统一皮肤 + 面板背景模糊 |
| `67530f6` | 测试与基线：特效关闭注入、视觉基线重拍 12 张、特效展示截图 8 张 + canvas 像素断言 |

## 2. 验证结果

### 2.1 前端单元测试（vitest）

`npx vitest run` → **39 passed（12 个文件）**。新增：

- settings store：默认值/旧数据兼容/持久化/坏 JSON 回落（4）；
- 粒子组件：enabled=false 不绘制、无 2d context 降级、卸载清理（3）；
- GameBackground：effect 映射与 sceneEffectsEnabled 开关（4）；
- presentation-adapter：background_effect 对账写入/缺省不覆盖/null 清空（3）。

### 2.2 后端测试（pytest）

`pytest -q` → **399 passed, 12 skipped**（较基线 +3：scene background_effect
默认/白名单拒绝/state view 透传）。

### 2.3 类型与构建

- `npm run typecheck` → PASS；
- `npm run build` → PASS（vite 179 modules，272 KB JS / 49.6 KB CSS）。

### 2.4 E2E（docs/13 §26.4 主线 + docs/14 T3/T4）

`npx playwright test tests/e2e` → **6/6 PASS**（两个 viewport × 3 条）。
期间修复两个回归：① 系统菜单换肤误删 `.sys-menu-btn` E2E 定位类 → 恢复
双类名；② 路由淡入过渡（out-in）使 GameView 挂载晚于 URL 变化，Load 后
直接 evaluate `gal_session_id` 存在竞态 → 改为 waitForFunction 等待落盘。

### 2.5 视觉基线（docs/13 §26.2）

`npx playwright test tests/visual --update-snapshots` → **22/22 PASS**，
重拍 12 张 Vue 基线（TITLE_EMPTY_SAVE / OPENING_DEEPSEEK_ONLY /
CLAUDE_APPEARS_TWO_ROLE / LONG_DIALOGUE / SAVE_PANEL / LOAD_PANEL × 2
viewport）+ 6 张旧前端对比证据。确定性保障：freezeAnimations 现同时注入
「特效全关」设置（canvas 粒子不受 CSS 冻结控制，必须经设置关闭）。

### 2.6 特效展示截图（人工/视觉模型复核证据）

`tests/visual/effects-showcase.spec.ts` 生成 8 张（2 viewport × 4 场景）：
TITLE_EFFECTS_ON / TITLE_HOVER / GAME_LOADING_TRANSITION / GAME_STARFIELD，
存于 `validation-results/docs15/showcase/`。GLM 视觉模型复核结论：

- 首页：背景明亮无遮罩、有星星/流星粒子、立绘居中、菜单居左四项齐备、
  文字 Logo 醒目，无重叠/穿帮；
- 加载演出：进度条 + 圆形进度圈 + 猫爪遮罩 + 粒子 + 中文状态文案齐备，
  观感精致无缺陷；
- 游戏内：背景/立绘/对话框（角色名/情绪标签/渐变）正常，无遮挡；
  （星空粒子尺寸小，VLM 降采样不可辨 —— 以 canvas 像素断言为机器证据，
  见 2.7。）

### 2.7 canvas 像素断言（粒子确在绘制的机器证据）

showcase 用例内新增断言：标题页 `#stars-canvas` 与游戏内
`canvas.starfield-canvas` 非透明像素数 **> 0**（实测 PASS），证明
StarAnimation / StarField 在特效开启时确实绘制，不依赖肉眼判断。

> 附：VLM 对 GAME_STARFIELD 截图报告「不可辨星空粒子」——原因是粒子为 2px
> 级发光点，模型降采样后消失；canvas 像素断言（同用例内、机器可复现）是
> 更可靠的证据来源，两种证据互补记录于此。

## 3. 差距表逐项闭合

| docs/15 §1 差距 | 状态 |
|---|---|
| 首页背景压暗/无景深/无视差 | ✅ 全亮 120% 宽 + 五层景深 + 阻尼视差（prefers-reduced-motion 禁用） |
| 菜单表单风 | ✅ clamp 大字 + text-shadow + 回弹 hover（cubic-bezier 0.18/0.89/0.32/1.28） |
| 无流星/星星 | ✅ MeteorAnimation + StarAnimation（离屏预渲染缓存、30fps、隐藏暂停） |
| 无转场/无面板模糊 | ✅ 菜单 slide 入场 + 路由淡入 + .gal-modal-mask 背景 blur |
| 无 Logo | ✅ 自制 CSS 渐变+辉光文字 Logo（素材边界：不迁移 LingChat 图片） |
| 超宽屏 | ✅ >2:1 主菜单两列 grid |
| 无光标特效 | ✅ CursorEffects（双缓冲 + 脏矩形 + 点击涟漪，弹窗内抑制） |
| 无缩放 | ✅ Ctrl+滚轮 0.8~1.5，Ctrl+0 复位，持久化 |
| 无特效开关 | ✅ 设置页 6 项开关，localStorage 持久化，旧数据兼容 |
| 游戏内无场景粒子 | ✅ 五种粒子，后端权威 background_effect（binding_room→StarField） |
| 无首次加载演出 | ✅ LoadingTransition（New Game 专用，2.4s~12s，opening 缓冲应用） |
| 五页风格不统一 | ✅ 共享 token + .gal-panel/.gal-btn + 统一页壳（Load/Settings） |

## 4. 已知限制（如实记录）

- **粒子不进视觉基线**：canvas 动画不可确定性冻结；基线在特效关闭状态拍摄
  （结构布局），粒子正确性由展示截图 + canvas 像素断言 + VLM 复核承担；
- **场景粒子与场景的映射只有 binding_room→StarField**：其余四种粒子已实现
  并进白名单，待内容团队按场景配置（docs/15 §6.1 明示不臆造映射）；
- **情绪气泡/情绪差分立绘/音效**（原差距 #13）：素材级差距，需要美术资源，
  代码通道（bubble 结构/滤镜）已就位（docs/13 §11 原约束）；
- 首页使用现有 `background_title.png`（1536×1024）与 deepseek 立绘；
  视差余量用 120% 宽度实现，最终 KV 上线后可直接替换 URL；
- 旧前端（frontend-deprecated）保持冻结未动。
