import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

// 设置（docs/13 §12.5）：文字速度 + BGM/音效音量（音频系统接入前仅存值）。
// 仅保存非敏感 UI 设置到 localStorage（docs/13 §14.1）。
// T2review P2-3：设置持久化到 localStorage，并已被 lingchat-compat 的
// typeWriterSpeed 消费（此前硬编码 50 且不持久化）。
const SETTINGS_KEY = 'gal_settings'

interface PersistedSettings {
  textSpeed: number
  bgmVolume: number
  sfxVolume: number
}

function loadPersisted(): PersistedSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (raw) {
      const data = JSON.parse(raw) as Partial<PersistedSettings>
      return {
        textSpeed: typeof data.textSpeed === 'number' ? data.textSpeed : 1,
        bgmVolume: typeof data.bgmVolume === 'number' ? data.bgmVolume : 0.6,
        sfxVolume: typeof data.sfxVolume === 'number' ? data.sfxVolume : 0.8,
      }
    }
  } catch {
    // 解析失败按默认值处理，绝不让设置崩溃页面
  }
  return { textSpeed: 1, bgmVolume: 0.6, sfxVolume: 0.8 }
}

export const useSettingsStore = defineStore('settings', () => {
  const initial = loadPersisted()
  const textSpeed = ref(initial.textSpeed)
  const bgmVolume = ref(initial.bgmVolume)
  const sfxVolume = ref(initial.sfxVolume)

  watch([textSpeed, bgmVolume, sfxVolume], () => {
    try {
      localStorage.setItem(
        SETTINGS_KEY,
        JSON.stringify({
          textSpeed: textSpeed.value,
          bgmVolume: bgmVolume.value,
          sfxVolume: sfxVolume.value,
        }),
      )
    } catch {
      // 存储不可用时静默降级（设置只影响体验，不影响游戏状态）
    }
  })

  return { textSpeed, bgmVolume, sfxVolume }
})
