import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createOpening, type OpeningResponse } from '../api/game'

// docs/13 §14.1：localStorage 只允许保存 player_id 与 UI 标记等；
// session_id 作为「恢复当前会话」的非敏感标识暂存（现有旧前端同约定）。
export const useGameStore = defineStore('game', () => {
  const sessionId = ref<string | null>(localStorage.getItem('gal_session_id'))
  const canInput = ref(false)
  const lastResponse = ref<OpeningResponse | null>(null)
  const busy = ref(false)
  const error = ref<string | null>(null)

  async function startNewSession(): Promise<void> {
    busy.value = true
    error.value = null
    try {
      const res = await createOpening(sessionId.value)
      sessionId.value = res.session_id
      localStorage.setItem('gal_session_id', res.session_id)
      lastResponse.value = res
      canInput.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      busy.value = false
    }
  }

  return { sessionId, canInput, lastResponse, busy, error, startNewSession }
})
