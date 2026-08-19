// LingChat 组件兼容层（docs/13 §8 / §11.2-11.4）。
//
// 目标：让迁入的 LingChat standard 组件（GameDialog / GameRoleAvatar /
// GameBackground / GameRolesStage）无需改动即可运行，方法是用本项目自己的
// store / 资源解析替换 LingChat 的 useGameStore / useUIStore / invoke /
// convertFileSrc / emotion vocab。
//
// 原则（docs/13 §9.2）：这里是「Mock Presentation State」，不是 Game Truth。
// 所有数据只描述「当前应如何展示」，全部由 GameView 注入。

import { usePresentationStore } from '../stores/presentation'
import { useSettingsStore as useRealSettingsStore } from '../stores/settings'
import { resolveCharacterAsset } from '../adapters/asset-resolver'

// ── 角色元数据（角色名等；后端 Game Truth 在 Task 4 接入后优先） ──
export interface MockRoleMeta {
  characterId: string
  roleName: string
  roleSubTitle: string
  character_folder: string
}

// 与后端 ALLOWED_EMOTIONS 对齐（docs/13 §11.2：替换 LingChat emotion vocab）
export const ROLE_META: Record<string, MockRoleMeta> = {
  deepseek: { characterId: 'deepseek', roleName: 'DeepSeek', roleSubTitle: '被困的 AI', character_folder: 'deepseek' },
  claude: { characterId: 'claude', roleName: 'Claude', roleSubTitle: '？？？', character_folder: 'claude' },
  chatgpt: { characterId: 'chatgpt', roleName: 'ChatGPT', roleSubTitle: '？？？', character_folder: 'chatgpt' },
  doubao: { characterId: 'doubao', roleName: '豆包', roleSubTitle: '？？？', character_folder: 'doubao' },
}

// ── emotion → 动画类映射（LingChat 中文词表 → 本项目英文 emotion 白名单） ──
// LingChat 用 bubbleImage/audio，我们当前没有气泡素材与音频，只用 animation
//（docs/13 §11：LingChat 素材不迁移；情绪差分是单图 + 滤镜）。
const ANIMATION_BY_EMOTION: Record<string, string> = {
  happy: 'happy-bounce',
  annoyed: 'angry-jump',
  angry: 'angry-jump',
  embarrassed: 'embarrassed-emo',
  serious: 'serious-think',
  surprised: 'suprised-jump',
  neutral: 'normal',
}

export interface MockEmotionConfig {
  animation: string
  bubbleImage: string
  bubbleClass: string
  audio: string
}

const NONE_CONFIG: MockEmotionConfig = {
  animation: 'none',
  bubbleImage: 'none',
  bubbleClass: 'none',
  audio: 'none',
}

/** emotion → config（气泡/音频当前统一 none，仅动画有效） */
export const EMOTION_CONFIG: Record<string, MockEmotionConfig> = {
  neutral: { ...NONE_CONFIG, animation: 'normal' },
  happy: { ...NONE_CONFIG, animation: 'happy-bounce' },
  annoyed: { ...NONE_CONFIG, animation: 'angry-jump' },
  angry: { ...NONE_CONFIG, animation: 'angry-jump' },
  embarrassed: { ...NONE_CONFIG, animation: 'embarrassed-emo' },
  serious: { ...NONE_CONFIG, animation: 'serious-think' },
  surprised: { ...NONE_CONFIG, animation: 'suprised-jump' },
}

/** LingChat 组件用 EMOTION_CONFIG_EMO[emotion] 把 emotion 归一到词表 */
export const EMOTION_CONFIG_EMO: Record<string, string> = {
  neutral: 'neutral',
  happy: 'happy',
  annoyed: 'annoyed',
  angry: 'angry',
  embarrassed: 'embarrassed',
  serious: 'serious',
  surprised: 'surprised',
}

// ── 兼容 GameDialog / GameRolesStage / GameRoleAvatar 的 Game Store ──
// 读本项目 Presentation Store；status / userName 等由 GameView 注入。
export const useGameStore = () => {
  const presentation = usePresentationStore()

  const toGameRole = (characterId: string) => {
    const c = presentation.state.characters[characterId]
    const meta = ROLE_META[characterId]
    return {
      roleId: characterId,
      roleName: meta?.roleName ?? characterId,
      roleSubTitle: meta?.roleSubTitle ?? '',
      thinkMessage: '思考中…',
      emotion: c?.emotion ?? 'neutral',
      originalEmotion: c?.emotion ?? 'neutral',
      scale: c?.scale ?? 1,
      offsetY: c?.offsetY ?? 0,
      offsetX: c?.offsetX ?? 0,
      slot: c?.slot ?? null,
      animation: c?.animation ?? null,
      show: c?.visible ?? false,
      character_folder: meta?.character_folder ?? characterId,
      clothesName: 'default',
      bubbleTop: 0,
      bubbleLeft: 0,
    }
  }

  return {
    get presentRolesList() {
      return presentation.state.presentCharacterIds
        .filter((id) => presentation.state.characters[id]?.visible)
        .map(toGameRole)
    },
    get presentRoleIds() {
      return presentation.state.presentCharacterIds.filter(
        (id) => presentation.state.characters[id]?.visible,
      )
    },
    get currentStatus(): 'input' | 'thinking' | 'responding' | 'presenting' {
      // docs/13 §26.1：思考中（等待 AI 回复）与逐字播放用权威 status 区分，
      // 使 GameDialog 的 thinking 占位/输入禁用与发送按钮禁用真正生效。
      if (presentation.state.status === 'thinking') return 'thinking'
      if (presentation.state.status === 'streaming') return 'responding'
      return presentation.state.dialogue.mode === 'ai' ? 'responding' : 'input'
    },
    get currentInteractRole() {
      const id = presentation.state.dialogue.speakerId
      return id ? toGameRole(id) : null
    },
    get userName() {
      return '你'
    },
    get userSubtitle() {
      return '侦探'
    },
    get currentScene() {
      return { lighting: presentation.state.scene.lighting ?? {} }
    },
    get command() {
      return null // 无触摸模式
    },
    get gameRoles() {
      return {}
    },
    get runningScript() {
      return null
    },
    get thinkingLength() {
      return 0
    },
  }
}

// ── 兼容 GameDialog 的 UI Store ──
// showCharacter* 由 GameView 写入 presentation store 的 dialogue 字段后映射。
export const useUIStore = () => {
  const presentation = usePresentationStore()
  return {
    get aspectRatio() {
      return window.innerWidth / window.innerHeight
    },
    get isNarrowScreen() {
      return window.innerWidth / window.innerHeight < 1.0
    },
    get isMobile() {
      return this.aspectRatio <= 1
    },
    get viewportHeight() {
      return window.innerHeight
    },
    get viewportWidth() {
      return window.innerWidth
    },
    get typeWriterSpeed() {
      // T2review P2-3：文字速度来自设置 store（默认 1x），不再硬编码 50。
      const settings = useRealSettingsStore()
      const speed = settings.textSpeed && settings.textSpeed > 0 ? settings.textSpeed : 1
      return Math.max(10, Math.round(50 / speed))
    },
    get currentBackgroundTransition() {
      return 300
    },
    get currentBackground() {
      return presentation.state.scene.backgroundId
    },
    get currentBackgroundEffect() {
      return ''
    },
    get currentBackgroundMusic() {
      return 'None'
    },
    get bgMusicPaused() {
      return false
    },
    get bgMusicStoped() {
      return false
    },
    get bgMusicPlaybackRate() {
      return 1
    },
    get bgMusicMode() {
      return 'loop-single'
    },
    get currentSoundEffect() {
      return 'None'
    },
    get currentAvatarAudio() {
      return 'None'
    },
    get ambientTracks() {
      return []
    },
    get characterVolume() {
      return 100
    },
    get backgroundVolume() {
      return 100
    },
    get bubbleVolume() {
      return 100
    },
    get ambientVolume() {
      return 100
    },
    get enableChatEffectSound() {
      return false
    },
    get showCharacterTitle() {
      return presentation.state.dialogue.speakerName ?? ''
    },
    get showCharacterSubtitle() {
      return ''
    },
    get showCharacterEmotion() {
      return presentation.state.dialogue.speakerId
        ? (presentation.state.characters[presentation.state.dialogue.speakerId]?.emotion ?? '')
        : ''
    },
    get showCharacterLine() {
      return presentation.state.dialogue.text
    },
    get showCharacterMotionText() {
      return ''
    },
    get showPlayerHintLine() {
      return ''
    },
    get showCharacterThinkLine() {
      return '思考中…'
    },
    get showSettings() {
      return false
    },
    get currentSettingsTab() {
      return 'text'
    },
    toggleSettings(_show: boolean) {},
    setSettingsTab(_tab: string) {},
    showNotification(_options: Record<string, unknown>) {},
    setEnableChatEffectSound(_enabled: boolean) {},
    handleBackgroundMusicEnd() {},
  }
}

// ── 兼容 useDialogAppearance 的 Settings Store（固定外观） ──
export const useSettingsStore = () => {
  return {
    get dialogBackgroundImage() {
      return ''
    },
    get dialogOpacity() {
      return 0.85
    },
    get dialogBlur() {
      return 0
    },
    get dialogBorderRadius() {
      return 12
    },
    get dialogGradientColor() {
      return '#0a1626'
    },
    get dialogTextColor() {
      return '#f4f8ff'
    },
    get dialogScrollHistoryEnabled() {
      return false
    },
    get dialogSpacebarHideEnabled() {
      return false
    },
    get dialogAutoHideOnThinkEnabled() {
      return false
    },
    get text() {
      return { inlineMotionText: false }
    },
    get textSpeed() {
      return 50
    },
  }
}

// ── 兼容 GameRoleAvatar 的资源解析（替换 invoke('get_avatar_file') + convertFileSrc） ──
// docs/13 §8.3 / §11.2：本项目必须建立自己的 characterId + emotion → asset URL。
export async function getAvatarFile(characterId: string, emotion: string, _clothesName: string): Promise<string> {
  return resolveCharacterAsset({ characterId, emotion })
}

export const getVoiceAudio = async (_file: string) => {
  console.warn('[lingchat-compat] getVoiceAudio: 当前项目无语音系统，忽略')
  return ''
}

// 兼容 GameDialog 的 escapeHtml
export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export const setInputHasText = (_v: boolean) => {}

// 空事件队列（GameDialog continueDialog 使用）
export const eventQueue = {
  continue() {
    return false
  },
}
