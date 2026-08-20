# docs16-p5 · 黑幕眼睑式睁眼转场 — 验证结果

> **状态：PASS**
> **日期：2026-08-23** · **环境：** frontend-vue；backend 未改动。
> **依据：** docs/16 P5（docs/16-玩家体验修复与开局选项窗口落地方案.md §2）。

## 1. 目标

开始游戏后增加约 1s 的黑幕眼睑式睁眼效果：全屏黑幕中间一道缝，上下「眼皮」
分开露出画面。每次进入游戏画面都播（新游戏排在猫爪演出之后，读档/会话恢复
直接播）；设置开关可关；reduced-motion 跳过。

## 2. 改动

- 新增 frontend-vue/src/components/effects/EyeOpenTransition.vue：上下两片 50%
  高黑幕 + transform 过渡（1s cubic-bezier）；pointer-events:none；reduced-motion
  立即 emit complete。
- stores/settings.ts：新增 eyeOpenTransitionEnabled（默认 true，向后兼容持久化）。
- views/SettingsView.vue：显示特效区新增「睁眼转场」开关。
- views/GameView.vue：prefersReducedMotion + showEyeOpen/armEyeOpen/onEyeOpenComplete；
  新游戏路径在 onLoadingComplete（猫爪揭幕结束后）播；pendingLoad/会话恢复路径
  挂载即播；无加载演出的新游戏路径 startOpening 后播。
- tests/visual/fixtures.ts：freezeAnimations 注入 eyeOpenTransitionEnabled:false
  （保证视觉/E2E 基线确定性）。
- 新增 EyeOpenTransition.spec（正常 ~1s 完成 / reduced-motion 立即完成）。

## 3. 验证

| 套件 | 结果 |
|---|---|
| npm run typecheck | PASS |
| npm run test:unit | PASS 41/41（新增 2 条 EyeOpenTransition 用例） |
| npm run test:visual | PASS 22/22（睁眼被注入关闭，无基线变化） |
| npm run test:e2e | PASS 6/6（独立 mock 服务） |
| backend pytest | 不适用（零后端改动） |

## 4. 限制

- 睁眼为纯视觉层（pointer-events:none），不阻塞输入/点击，也不影响时序。
- 音频未加入（遵循「不新增素材依赖」边界）；如需可后续叠加 WebAudio 合成。
- in-game Load（系统菜单内读档）不重播睁眼 —— 仅「进入游戏画面」这一边界播
  （用户语义：新游戏 + 标题页读档进入时）。

## 5. 证据

- 单测：Test Files 13 passed，Tests 41 passed。
- 视觉 22 passed + E2E 6 passed（exit 0，独立 mock 服务）。
