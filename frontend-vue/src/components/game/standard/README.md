# Task 2 迁入 LingChat Standard Game UI

白名单迁移（docs/13 §5.1）：GameBackground / GameDialog / GameRoleAvatar /
GameRolesStage / ImageAcrossFade（ui 依赖）/ avatar-animation.css / TypeWriter
（utils 依赖）。GameExtraUI 及其 extra/* 子组件本轮不迁移（docs/13 Task 2 第一轮
不需要章节名/选项/剧本显示，后续 Task 接入 script 时再评估）。

来源与修改说明见仓库根 `THIRD_PARTY_LICENSES.md`。
驱动数据来自 Mock Presentation State（`src/adapters/lingchat-compat.ts` +
`src/stores/presentation.ts`），不引入 LingChat Store / Tauri。
