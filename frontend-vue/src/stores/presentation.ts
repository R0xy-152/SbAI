import { defineStore } from 'pinia'
import { ref } from 'vue'
import { toPresentationState } from '../adapters/presentation-adapter'
import type { PresentationState } from '../types/presentation'

// Presentation Store（docs/13 §9.2）：禁止在此做剧情判断，
// 所有变化只能来自 Backend 的 presentation directive / presentation_state。
export const usePresentationStore = defineStore('presentation', () => {
  const state = ref<PresentationState>(toPresentationState())

  function reset(): void {
    state.value = toPresentationState()
  }

  return { state, reset }
})
