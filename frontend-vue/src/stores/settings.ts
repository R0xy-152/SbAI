import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

// 设置（docs/13 §12.5）：文字速度 + BGM/音效音量（音频系统接入前仅存值）。
// 仅保存非敏感 UI 设置到 localStorage（docs/13 §14.1）。
// T2review P2-3：设置持久化到 localStorage，并已被 lingchat-compat 的
// typeWriterSpeed 消费（此前硬编码 50 且不持久化）。
// docs/15 §5.3：新增显示特效开关（首页星星/流星、光标拖尾/点击涟漪、
// 场景粒子、首次加载演出）与 UI 缩放。缺省字段一律取默认值，旧数据不丢。
const SETTINGS_KEY = 'gal_settings'

export const DEFAULT_SETTINGS = {
  textSpeed: 1,
  bgmVolume: 0.6,
  sfxVolume: 0.8,
  // docs/15 §5.3 显示特效（默认全开，与 LingChat 默认一致；视觉基线注入关闭）
  mainMenuStarsEnabled: true,
  mainMenuMeteorsEnabled: true,
  globalMouseTrailEnabled: true,
  clickAnimationEnabled: true,
  sceneEffectsEnabled: true,
  loadingTransitionEnabled: true,
  // docs/16 P5：进入游戏画面时的黑幕睁眼转场
  eyeOpenTransitionEnabled: true,
  // docs/15 §5.2 Ctrl+滚轮 UI 缩放（0.8~1.5）
  uiZoom: 1,
}

export interface PersistedSettings {
  textSpeed: number
  bgmVolume: number
  sfxVolume: number
  mainMenuStarsEnabled: boolean
  mainMenuMeteorsEnabled: boolean
  globalMouseTrailEnabled: boolean
  clickAnimationEnabled: boolean
  sceneEffectsEnabled: boolean
  loadingTransitionEnabled: boolean
  eyeOpenTransitionEnabled: boolean
  uiZoom: number
}

type SettingsKey = keyof PersistedSettings

function loadPersisted(): PersistedSettings {
  const out = { ...DEFAULT_SETTINGS } as PersistedSettings
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (raw) {
      const data = JSON.parse(raw) as Partial<PersistedSettings>
      for (const key of Object.keys(DEFAULT_SETTINGS) as SettingsKey[]) {
        const value = data[key]
        const def = DEFAULT_SETTINGS[key]
        if (typeof value === typeof def) {
          ;(out as unknown as Record<string, unknown>)[key] = value
        }
      }
    }
  } catch {
    // 解析失败按默认值处理，绝不让设置崩溃页面
  }
  return out
}

export const useSettingsStore = defineStore('settings', () => {
  const initial = loadPersisted()
  const textSpeed = ref(initial.textSpeed)
  const bgmVolume = ref(initial.bgmVolume)
  const sfxVolume = ref(initial.sfxVolume)
  const mainMenuStarsEnabled = ref(initial.mainMenuStarsEnabled)
  const mainMenuMeteorsEnabled = ref(initial.mainMenuMeteorsEnabled)
  const globalMouseTrailEnabled = ref(initial.globalMouseTrailEnabled)
  const clickAnimationEnabled = ref(initial.clickAnimationEnabled)
  const sceneEffectsEnabled = ref(initial.sceneEffectsEnabled)
  const loadingTransitionEnabled = ref(initial.loadingTransitionEnabled)
  const eyeOpenTransitionEnabled = ref(initial.eyeOpenTransitionEnabled)
  const uiZoom = ref(initial.uiZoom)

  const state = {
    textSpeed,
    bgmVolume,
    sfxVolume,
    mainMenuStarsEnabled,
    mainMenuMeteorsEnabled,
    globalMouseTrailEnabled,
    clickAnimationEnabled,
    sceneEffectsEnabled,
    loadingTransitionEnabled,
    eyeOpenTransitionEnabled,
    uiZoom,
  }

  watch(
    () => [
      textSpeed.value,
      bgmVolume.value,
      sfxVolume.value,
      mainMenuStarsEnabled.value,
      mainMenuMeteorsEnabled.value,
      globalMouseTrailEnabled.value,
      clickAnimationEnabled.value,
      sceneEffectsEnabled.value,
      loadingTransitionEnabled.value,
      eyeOpenTransitionEnabled.value,
      uiZoom.value,
    ],
    () => {
      try {
        const data: Record<string, unknown> = {}
        for (const [key, refValue] of Object.entries(state)) {
          data[key] = refValue.value
        }
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(data))
      } catch {
        // 存储不可用时静默降级（设置只影响体验，不影响游戏状态）
      }
    },
  )

  return state
})
