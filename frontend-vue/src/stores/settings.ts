import { defineStore } from 'pinia'
import { ref } from 'vue'

// 设置（docs/13 §12.5）：首版文字速度 + BGM/音效音量（音频系统接入前仅存值）。
// 仅保存非敏感 UI 设置到 localStorage（docs/13 §14.1）。
export const useSettingsStore = defineStore('settings', () => {
  const textSpeed = ref(1)
  const bgmVolume = ref(0.6)
  const sfxVolume = ref(0.8)
  return { textSpeed, bgmVolume, sfxVolume }
})
