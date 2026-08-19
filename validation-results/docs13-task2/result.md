# docs/13 Task 2 — 迁入 LingChat Standard Game UI

**状态：PASS**
**日期：2026-08-19**
**范围：** docs/13 §25 Task 2（白名单复制 + Mock Presentation State 驱动 + 双视口验收）

---

## 1. 完成了什么

按白名单复制 LingChat（SlimeBoyOwO/LingChat，AGPL-3.0）Standard Game UI 到 `frontend-vue/src/components/game/standard/`，去除 Tauri / LingChat Store 依赖，用本项目 Mock Presentation State 驱动。第一轮达成全部要求：

- 背景显示（`/backgroud/background1.png`，cover 铺满、光照滤镜）
- DeepSeek 立绘（`/char/deepseek/pic/deepseek_main.png`）
- Claude 立绘（`/frontend/public/characters/claude-main.png`）
- 双角色自动站位（`(i+1)/(n+1)` 公式 → 33.3% / 66.7%）
- emotion 切换（img 双叠 cross-fade，不闪白）
- fade（角色进场 Vue Transition + ImageAcrossFade 交叉淡入）
- 基础动画（avatar-animation.css：happy-bounce / angry-jump / serious-think / suprised-jump / embarrassed-emo）
- Dialogue UI（speaker 名 + 情绪标签 + textarea 打字机 + 输入 + 发送 + thinking 占位）

## 2. 修改了哪些文件

**新增（迁入，标注 Adapted from LingChat）：**
- `frontend-vue/src/components/game/standard/GameBackground.vue` — 去粒子/音乐/环境音，保留背景+光照
- `frontend-vue/src/components/game/standard/GameDialog.vue` — 去截图/录音/移动端菜单/Tauri，保留 speaker/textarea/typing/input/send
- `frontend-vue/src/components/game/standard/GameRoleAvatar.vue` — 去 TouchAreas/invoke，立绘改 RoleSprite
- `frontend-vue/src/components/game/standard/GameRolesStage.vue` — 去主语音播放器
- `frontend-vue/src/components/game/standard/RoleSprite.vue` — 新增（img 双叠 cross-fade，撑开容器宽实现自动站位）
- `frontend-vue/src/components/game/standard/ui/ImageAcrossFade.vue` — 背景用（原样）
- `frontend-vue/src/components/game/standard/utils/TypeWriter.ts` — 去音频
- `frontend-vue/src/components/game/standard/useTypeWriter.ts` / `useDialogAppearance.ts` — composable 移植
- `frontend-vue/src/components/game/standard/avatar-animation.css` — 原样
- `frontend-vue/src/components/game/standard/index.ts`

**改写（兼容层 / Mock）：**
- `frontend-vue/src/adapters/lingchat-compat.ts` — useGameStore/useUIStore/useSettingsStore Mock + EMOTION_CONFIG/EMOTION_CONFIG_EMO（英文 emotion 白名单）+ getAvatarFile（asset-resolver）+ escapeHtml/eventQueue
- `frontend-vue/src/adapters/asset-resolver.ts` — characterId+emotion → 真实 URL
- `frontend-vue/src/adapters/presentation-adapter.ts` —（保留骨架）
- `frontend-vue/src/stores/presentation.ts` — Mock Presentation State（docs/13 §9）
- `frontend-vue/src/types/presentation.ts` — SceneLighting 扩展（完整光照契约）
- `frontend-vue/src/views/GameView.vue` — 用 Mock 驱动舞台（背景+双角色+emotion 周期+AI 台词）
- `frontend-vue/vite.config.ts` — 新增 `/char` `/backgroud` `/frontend` 代理（后端托管仓库根静态资源）

**文档：**
- `THIRD_PARTY_LICENSES.md` — 文件来源清单（LingChat 路径 → 本项目路径 → 修改说明，docs/13 §4.3）
- `frontend-vue/src/components/game/standard/README.md`
- `validation-results/docs13-task2/result.md`（本文件）+ verify 脚本 4 个 + 截图

## 3. 如何验证

```bash
cd /d/gal/frontend-vue && npm run typecheck   # PASS（vue-tsc 0 error）
cd /d/gal/frontend-vue && npm run build       # PASS（vite build 成功）
node validation-results/docs13-task2/verify-layout.mjs   # 双视口几何断言
node validation-results/docs13-task2/verify-task2.mjs    # emotion/动画/品牌断言
node validation-results/docs13-task2/verify-imgs.mjs     # 立绘 naturalWidth 断言
```

headless Chrome CDP 实测（1366x768 与 1920x1080）：

| 验收项 | 1366x768 | 1920x1080 |
|---|---|---|
| 背景无白边 | PASS（铺满 1350x621） | PASS（铺满 1904x933） |
| 角色基线合理 | PASS（bottom 贴底） | PASS（bottom 贴底） |
| 双角色自动站位 | PASS（33.3% / 66.7%） | PASS（33.3% / 66.7%） |
| 立绘真实加载 | PASS（naturalWidth=1024） | PASS（naturalWidth=1024） |
| 表情切换不闪白 | PASS（img 双叠 count=2 恒在） | PASS |
| fade 无明显 layout jump | PASS（left 稳定不变） | PASS |
| Dialogue 不遮脸 | PASS（顶部 76.7% vh） | PASS（84.5% vh） |
| 无 LingChat 品牌 | PASS（无 Lovely You/Bilibili/诺一钦灵 等） | PASS |

## 4. 结果

**PASS。** 截图：`validation-results/docs13-task2/TASK2_1366x768.jpg`、`TASK2_1920x1080.jpg`（JPEG 有效 SOI/EOI，80KB/168KB）。

## 5. 已知限制

- **emotion 是单图 + 滤镜**：仓库只有静态立绘，无差分表情素材；当前 emotion 切换是「动画类 + 前景 tint」（Task 2 验收只要求不闪白，已满足）。后续引入差分立绘时在 `asset-resolver` 扩展 spriteKey。
- **GameExtraUI 及其 extra/ 子组件未迁移**：第一轮不需要章节名/选项/剧本显示，Task 4 接 script 时再评估（docs/13 §5.1 允许分批）。
- **GameBackground 粒子/音乐/环境音未迁移**：docs/13 §11.1 第一轮不要求，无相关素材。
- **对话未接真实后端**：GameView 用 Mock 台词演示；Task 4 接 `/api/chat` 后替换。
- **vite 资源代理**：`/char` `/backgroud` `/frontend` 依赖后端 8000 托管仓库根；生产由 nginx 处理。

## 6. 建议提交

可以提交。改动范围：`frontend-vue/src/components/game/standard/*`（迁入）、`adapters/lingchat-compat.ts`、`GameView.vue`、`vite.config.ts`、`THIRD_PARTY_LICENSES.md`、`validation-results/docs13-task2/*`。
