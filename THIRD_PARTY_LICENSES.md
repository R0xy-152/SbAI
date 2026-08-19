# THIRD-PARTY LICENSES

本文件记录从 LingChat（SlimeBoyOwO/LingChat）复用的源码清单，以及项目自身的许可证归属。

## 复用来源：LingChat

- **项目：** SlimeBoyOwO/LingChat
- **许可证：** GNU Affero General Public License v3.0（AGPL-3.0）
- **许可证全文：** https://www.gnu.org/licenses/agpl-3.0.html
- **复用政策：** 只复用 docs/13 §5.1 白名单代码；游戏素材（立绘/背景/音乐/字体/Logo/Prompt/剧情文本）一律不复用（docs/13 §4.4）。

### 复用文件清单

> 此表在 Task 2 迁入时逐步填充。格式：LingChat 原路径 → 本项目路径 → 修改说明。

| LingChat 路径 | 本项目路径 | 修改说明 |
|---|---|---|
| `src/components/game/standard/GameBackground.vue` | `frontend-vue/src/components/game/standard/GameBackground.vue` | 去掉 Tauri `convertFileSrc`（改走 HTTP 静态资源）；去掉粒子特效（StarField/Rain/Sakura/Snow/Fireworks）、背景音乐（AudioAcrossFade）、环境音（AmbientLoopPlayer）与短效音效；保留背景图 + 光照滤镜（docs/13 §11.1 第一轮不迁移） |
| `src/components/game/standard/GameDialog.vue` | `frontend-vue/src/components/game/standard/GameDialog.vue` | 删移动端折叠菜单、场景设置/历史/截图/语音/关闭按钮、Tauri `listen`/`invoke`（screenshot）、语音识别；去掉 LingChat stores；保留 auto 布局、typing/streaming、player input、thinking 占位、对话框外观（docs/13 §11.4） |
| `src/components/game/standard/GameRoleAvatar.vue` | `frontend-vue/src/components/game/standard/GameRoleAvatar.vue` | `useGameStore`/`useUIStore` 改为本项目 Mock 兼容层；去掉 `invoke('get_avatar_file')` + `convertFileSrc`（改走 asset-resolver）；去掉 TouchAreas（docs/13 §5.2 不迁移）；气泡/音效保留结构但移除播放逻辑（无素材） |
| `src/components/game/standard/GameRolesStage.vue` | `frontend-vue/src/components/game/standard/GameRolesStage.vue` | 去掉主语音播放器（getVoiceAudio / audio events）；store 换兼容层；保留遍历在场角色、统一舞台、lighting overlay（docs/13 §11.3） |
| `src/components/game/standard/avatar-animation.css` | `frontend-vue/src/components/game/standard/avatar-animation.css` | 原样复制（无外部依赖） |
| `src/components/ui/ImageAcrossFade.vue` | `frontend-vue/src/components/game/standard/ui/ImageAcrossFade.vue` | 原样复制（`ui/` 实际依赖，白名单 §5.1「实际被上述组件依赖的文件」） |
| `src/utils/typewriter/TypeWriter.ts` | `frontend-vue/src/components/game/standard/utils/TypeWriter.ts` | 去掉所有 AudioContext / 音效逻辑（docs/13 §11：无关音频控制删除），保留纯打字引擎 |
| `src/composables/ui/useTypeWriter.ts` | `frontend-vue/src/components/game/standard/useTypeWriter.ts` | 原样移植（依赖 TypeWriter） |
| `src/composables/useDialogAppearance.ts` | `frontend-vue/src/components/game/standard/useDialogAppearance.ts` | 去掉 settings store 依赖（改读本项目 Mock store）；去掉滚轮历史/空格隐藏/思考自动隐藏（docs/13 §11.4 无需） |

> 参考（未复制，仅用于理解行为）：`src/controllers/emotion/config.ts`、`src/stores/modules/ui/ui.ts`、`src/stores/modules/game/state.ts`、`src/components/base/index.ts`。它们定义了「emotion → animation/bubble」「UI Store 视口字段」「角色结构」的契约，本项目在 `frontend-vue/src/adapters/lingchat-compat.ts` 中实现等价的最小 Mock（docs/13 §11.2：替换 LingChat emotion vocab / useGameStore / useUIStore 数据来源）。

## 本项目许可证

本项目代码仓库整体按 **AGPL-3.0** 开源（docs/13 §4.1）。根目录 `LICENSE` 将存放 AGPL-3.0 全文。
