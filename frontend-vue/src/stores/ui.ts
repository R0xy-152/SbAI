import { defineStore } from 'pinia'
import { ref } from 'vue'

// UI 瞬态（docs/13 §9/§31：前端 Presentation State）。
export const useUiStore = defineStore('ui', () => {
  const backendOk = ref<boolean | null>(null)
  const historyOpen = ref(false)
  const systemMenuOpen = ref(false)
  return { backendOk, historyOpen, systemMenuOpen }
})
