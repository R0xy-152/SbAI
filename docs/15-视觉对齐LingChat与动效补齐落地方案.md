# 15 — 视觉对齐 LingChat 与动效补齐落地方案

> 状态：Active
> 上游：docs/13（§5.1 白名单、§11 第一轮裁剪、§27 视觉验收、§28 性能边界）
> 背景：docs/13 第一轮以「功能正确」为优先，首页只保留静态背景 + 表单按钮，
> 与 LingChat 参考实现的视觉层（视差、粒子、电影感菜单、加载演出、光标特效、
> 场景粒子）存在系统性差距，且 docs/13 §27.4 明确禁止以「已使用 LingChat 源码」
> 为由跳过视觉验收。本文档定义差距补齐的实现范围、素材边界与验收标准。

## 1. 差距总表（来源：对照 D:\lingchat 源码逐层比对）

| 层 | 差距 | 本文档章节 |
|---|---|---|
| 首页 | 背景压暗（opacity-60 + 55% 遮罩）、无景深层次、无鼠标视差 | §4.1 |
| 首页 | 菜单按钮为表单风，无电影感字号/text-shadow/回弹 hover | §4.2 |
| 首页 | 无流星/星星粒子层 | §4.3 |
| 首页 | 菜单状态无 slide 转场、面板无 backdrop blur | §4.4 |
| 首页 | 无文字 Logo 视觉（图片 Logo 素材不迁移，自制 CSS 文字 Logo） | §4.5 |
| 首页 | 超宽屏（>2:1）菜单不切两列 | §4.6 |
| 全局 | 无光标拖尾/点击涟漪特效 | §5.1 |
| 全局 | 无 Ctrl+滚轮 UI 缩放 | §5.2 |
| 全局 | 设置页无显示特效开关（docs/13 §28 要求粒子低性能开关） | §5.3 |
| 游戏内 | 场景粒子（StarField/Rain/Sakura/Snow/Fireworks）第一轮未迁移 | §6 |
| 游戏内 | 首次进入游戏无加载演出（LoadingTransition） | §7 |
| 全局 | Title/Save/Load/Settings 与游戏内风格不统一（docs/13 §27.3） | §8 |

## 2. 素材边界（不可逾越）

docs/13 §4.4 素材白名单不自动包含字体/Logo/立绘/背景/音效，本任务一律：

- **不复制** LingChat 的字体文件（MaokenAssortedSans）、Logo 图、alona 立绘、
  background2.png 背景与任何音效素材；
- 首页背景用仓库现有 `backgroud/background_title.png`（全亮展示，不做遮罩压暗）；
- ~~首页角色立绘用 `char/deepseek/pic/deepseek_main.png`（本项目自有素材）~~
  **v1.1 修订：首页不放角色立绘层** —— background_title.png 背景图本身已含人物，
  再叠立绘会双人撞车；首页为四层结构（背景/流星/星星/菜单），视差作用于
  背景与星星层（修订前为五层 + 角色视差）。
- 文字 Logo 用 CSS 渐变 + 辉光自制（无新素材依赖）；
- 加载演出音效用 WebAudio 合成（正弦 tick/chime/pop/unveil，无采样文件）；
- 字体栈升级为系统可用中文字体候选列表（PingFang SC / HarmonyOS Sans SC /
  Source Han Sans SC / Noto Sans SC / Microsoft YaHei），不引入字体文件。

## 3. 代码复用与许可证

新增复用（全部登记到 `THIRD_PARTY_LICENSES.md`）：

| LingChat 路径 | 本项目路径 | 修改 |
|---|---|---|
| `src/components/game/standard/animations/MeteorAnimation.vue` | `frontend-vue/src/components/effects/MeteorAnimation.vue` | 去 Tauri 无关依赖；保留模板缓存/贝塞尔尾巴/帧率限制/可见性暂停 |
| `src/components/game/standard/animations/StarAnimation.vue` | `frontend-vue/src/components/effects/StarAnimation.vue` | 同上；保留离屏预渲染光晕缓存 |
| `src/components/game/standard/animations/ParallaxAnimation.ts` | `frontend-vue/src/composables/useParallaxAnimation.ts` | 原样移植（无 Tauri 依赖） |
| `src/components/effects/CursorEffects.vue` | `frontend-vue/src/components/effects/CursorEffects.vue` | 去 settings store 依赖（改读本项目 settings）；去弹窗抑制选择器适配 |
| `src/components/views/menu/base/StartPage|StartLogo|StartItem|StartLine|StartList.vue` | `frontend-vue/src/components/title/` | StartLogo 改为自制 CSS 文字 Logo；StartItem/StartList/StartLine 原样适配（Tailwind 类） |
| `src/components/views/LoadingTransition.vue` | `frontend-vue/src/components/effects/LoadingTransition.vue` | 去 i18n/eventQueue；进度事件改为「opening 数据就绪」信号；最短展示 2.4s（Web 版缩短）/最长 12s；保留猫爪 SVG 遮罩揭幕 + WebAudio 合成音效 |
| `src/components/game/standard/particles/StarField.vue` | `frontend-vue/src/components/game/standard/particles/StarField.vue` | 原样适配（enabled/starCount/scrollSpeed/colors props） |
| `src/components/game/standard/particles/Rain.vue` + `hooks/useRain.ts` + `config/rain.ts` | `frontend-vue/src/components/game/standard/particles/Rain.vue`（内联合并） | 原样适配 |
| `src/components/game/standard/particles/Sakura.vue` / `Snow.vue` + `hooks/useFallingParticle.ts` + `config/sakura.ts` / `config/snow.ts` + `types/falling.ts` | `frontend-vue/src/components/game/standard/particles/`（Sakura.vue / Snow.vue / useFallingParticle.ts） | 原样适配 |
| `src/components/game/standard/particles/Fireworks.vue` | 自研简化实现（仅概念参考，不复制源码） | 火箭升空 + 爆炸粒子 + 拖尾；无音频/无 pointer 交互；性能受 docs/13 §28 约束 |

## 4. 首页 TitleView 重构（docs/13 Task 5 视觉层补齐）

### 4.1 背景与景深

- 背景层：全亮 `background_title.png`，`left:-10%; width:120%` 给视差留余量，
  `background-size:cover`，`will-change:transform`；**删除** opacity-60 与深色遮罩；
- 层级（自底向上）：背景(-2) → 流星层(2) → 星星层(2) → 菜单(5)；
- **v1.1 修订：无角色立绘层**（背景图已含人物，叠立绘会撞车）；
  useParallaxAnimation 的 charRef 因此改为可选参数。

### 4.2 鼠标视差

`useParallaxAnimation`：bg ±6px / stars ±20px（v1.1 起无角色层，char 通道保留为可选参数），rAF 阻尼插值
（DAMPING 0.08）；16ms 节流；收敛自动停；页面隐藏暂停；will-change 优化。
仅当 `prefers-reduced-motion` 未启用时运行（可访问性）。

### 4.3 粒子层

- MeteorAnimation：canvas 流星（贝塞尔曲线 + 渐变尾巴 + 光晕），30fps 上限，
  模板缓存 10 条，同时最多 3 颗，1s 生成间隔；
- StarAnimation：canvas 80 颗星（星形/圆形混用），离屏预渲染发光贴图缓存，
  30fps 上限，闪烁 + 缓慢漂移；
- 两开关来自设置 `mainMenuStarsEnabled` / `mainMenuMeteorsEnabled`（默认开）。

### 4.4 菜单

- StartList/StartLine/StartItem/StartLogo 组件化；
- 按钮：`clamp(28px,3vw,52px)` 大字（非超宽）/ `clamp(40px,4vw,72px)`（超宽），
  text-shadow，hover `-translate-y-2 scale-105` + 白辉光 + `cubic-bezier(0.18,0.89,0.32,1.28)`；
- 保留 `title-btn` class 与四个按钮文案（开始游戏/继续游戏/读取存档/设置），
  E2E/视觉基线选择器与语义不破坏；
- 继续游戏无存档时 disabled + 提示（沿用 docs/13 §12.3）；
- 菜单区 hover/入场用 slide-left 0.4s `cubic-bezier(0.7,0,0.2,1)`；
- 后端连接状态提示条保留，样式改为底部小字 + 呼吸灯点。

### 4.5 文字 Logo

CSS 渐变（#dff7ff → #87d6f4）+ 多层辉光 + 字距拉开 + 缓慢呼吸；
Logo 区 hover 放大（drop-shadow 增强），点击无行为（无 GitHub 链接）。

### 4.6 超宽适配

>2:1 宽高比时主菜单切两列 grid（StartList responsive 逻辑原样适配）。

### 4.7 首页验收

- 背景全亮无遮罩；三色层叠（背景/粒子/立绘）可见；
- 鼠标移动视差生效（背景/立绘/星星相对位移）；
- 四按钮大字 + 回弹 hover；无存档时「继续游戏」禁用；
- resize 不溢出（含超宽两列切换）；
- 粒子开关关闭后首页无 canvas 绘制且无报错。

## 5. 全局动效与设置

### 5.1 CursorEffects

- 全局 60fps 光标拖尾 + 点击涟漪（canvas，双缓冲 + 脏矩形清理）；
- 弹窗/模态（.gal-modal 遮罩）打开时不绘制；
- 设置开关 `globalMouseTrailEnabled` / `clickAnimationEnabled`（默认开）；
- teleport 到 body，避开 #app 缩放坐标问题（与 LingChat 同方案）。

### 5.2 Ctrl+滚轮缩放

- `useZoom`：#app `zoom`，范围 0.8~1.5，步进 0.05，Ctrl+0 复位；
- zoom 持久化到设置（`uiZoom`）。

### 5.3 设置页（SettingsView）重构

新增「显示特效」分组：

| 键 | 默认 | 说明 |
|---|---|---|
| `mainMenuStarsEnabled` | true | 首页星星 |
| `mainMenuMeteorsEnabled` | true | 首页流星 |
| `globalMouseTrailEnabled` | true | 光标拖尾 |
| `clickAnimationEnabled` | true | 点击涟漪 |
| `sceneEffectsEnabled` | true | 游戏内场景粒子总开关 |
| `loadingTransitionEnabled` | true | 首次加载演出 |

沿用 `gal_settings` localStorage（向后兼容：缺省字段取默认值，旧数据不丢）。

## 6. 游戏内场景粒子（Backend 权威）

### 6.1 后端

- `Scene` 增加字段 `background_effect: str | None = None`（纯展示性视觉事实，
  不进角色上下文；DeepSeek 不可见性不受影响）；
- `KNOWN_BACKGROUND_EFFECTS = {"StarField","Rain","Sakura","Snow","Fireworks"}`；
- `binding_room`（默认场景）→ `"StarField"`；其余场景暂不配置（保持 None，
  由后续内容团队按场景配置，防止前台臆造）；
- `presentation_state` 增加 `background_effect`（orchestrator 经 SceneRegistry
  解析 `state.current_scene`），Frontend 不对 effect 做剧情推断。

### 6.2 前端

- `PresentationStateView` / `PresentationState.scene` 增加 `backgroundEffect`；
- adapter 对账写入；`lingchat-compat` 的 `currentBackgroundEffect` 读该字段；
- `GameBackground.vue` 增加粒子层：按 effect 渲染五个粒子组件之一；
  `sceneEffectsEnabled=false` 时整层不渲染；
- 粒子层 `isolation:isolate` 建立独立层叠上下文（防 z-index 逃逸盖 UI）。

### 6.3 粒子组件契约

- 全部 `enabled` prop + resize 重算 + visibilitychange 暂停 + 卸载清理；
- canvas 类限帧（StarField 30fps / Rain 60fps / Fireworks 60fps），
  CSS 类（Sakura/Snow）每粒子一条 keyframes，数量 = baseCount × intensity；
- `document.hidden` 时取消 rAF/interval，恢复后重启。

### 6.4 游戏内验收

- opening 阶段绑定房间可见星空粒子；保存/读取对账后 effect 与 scene 一致；
- 设置关闭 `sceneEffectsEnabled` 后立即卸载粒子层；
- 视觉基线在粒子关闭状态下拍摄（确定性），另存 effects-on 展示截图进
  validation-results 作为人工复核证据（canvas 动画不进基线）。

## 7. 首次加载演出（LoadingTransition）

- 仅「开始游戏（New Game）」路径显示；Continue / Load 恢复路径不显示；
- 进度条：事件（opening 数据就绪）到达后 1s 内冲满；最短展示 2.4s，最长 12s
  强制完成；完成后猫爪 SVG 遮罩揭幕（peek → anticipation → unveil 三阶段）；
- WebAudio 合成音效（tick/chime/pop/unveil），音量 0.05 级，autoplay 失败静默；
- 设置 `loadingTransitionEnabled=false` 或 E2E 注入时完全不挂载；
- 演出结束后才恢复打字机/事件队列（避免在遮罩后提前播放）。

## 8. 全站视觉统一（docs/13 §27.3）

- `style.css` 定义共享 token（背景/面板/主色/次色/辉光）与 `.gal-panel`、
  `.gal-btn`、`.gal-btn-primary`、`.gal-modal-mask` 基础类；
- 套用对象：SystemMenu / SavePanel / LoadPanel / AutoSaveCard / ManualSaveSlot /
  HistoryPanel / SettingsView / LoadView / GameView 顶栏与面板遮罩；
- 面板打开时游戏场景加 backdrop blur（`backdrop-filter: blur(12px) brightness(0.9)`）；
- GameView 顶栏改 pill 按钮组（右上角），保留「系统菜单」「返回标题」语义；
- 标题页与 Load/Settings 页共享同一背景皮肤（全亮背景 + 左上标题 + 右下版本号）。

## 9. 验证计划

### 9.1 单元/组件测试（vitest）

- settings store：新字段默认值/持久化/旧数据兼容；
- TitleView：沿用 Continue 禁用/启用语义（`.title-btn` 选择器不变）；
- 粒子组件：enabled=false 不建 canvas；无 2d context 时静默降级；卸载清理；
- GameBackground：effect 映射与设置开关的渲染分支；
- presentation-adapter：backgroundEffect 对账写入。

### 9.2 后端测试（pytest）

- `Scene.background_effect` 默认 None；binding_room 注册 StarField；
- `presentation_state.background_effect` 随 scene 解析；未知场景 → None；
- 未知 effect 值拒绝（配置期校验）。

### 9.3 E2E / 视觉基线

- E2E：`page.addInitScript` 注入 `gal_settings`（全部特效关 +
  loadingTransitionEnabled=false），保证时序确定性；全部选择器不变 → 6 条
  主线用例应原样通过；
- 视觉基线：重拍（旧基线删除后 `--update-snapshots`，禁止复用服务器）；
  新增 `EFFECTS_OFF` 系列维持确定性；
- 展示证据：新增 `tests/visual/effects-showcase.spec.ts`（特效全开、无断言）
  把首页/游戏内效果截图存入 `validation-results/docs15/showcase/`，人工 + 视觉
  模型复核后随结果文档归档。

### 9.4 结果

- `validation-results/docs15/result.md` 记录每步验证与 PASS 结论；
- docs/13 §11.1 第一轮裁剪表标注「第二轮已补齐」并指向 docs/15；
- docs/13 §27.4 逐条对照验收记录。

## 10. 风险与边界

- 粒子动画为展示层，不进视觉回归基线（canvas 不可确定性冻结）；基线只覆盖
  结构布局，粒子正确性由展示截图 + 人工复核承担；
- `prefers-reduced-motion` 用户：视差/光标特效自动禁用，粒子保留静态降级
  （星/雨/樱/雪/烟花不受影响，符合 LingChat 行为）；
- 性能边界遵守 docs/13 §28：帧率限制、离屏缓存、隐藏暂停、卸载清理；
- 不在本任务引入任何新运行时依赖（不装第三方动画库）。
