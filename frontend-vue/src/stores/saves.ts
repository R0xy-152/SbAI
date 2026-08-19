import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GameSaveInfo } from '../api/saves'

// 存档列表（docs/13 §12.4 / §20.1）。Task 7 Save/Load UI 接入后端列表；
// 骨架期占位：1 个 Auto + 6 个 Manual，全部空。
export const useSavesStore = defineStore('saves', () => {
  const auto = ref<GameSaveInfo | null>(null)
  const manual = ref<(GameSaveInfo | null)[]>([null, null, null, null, null, null])
  return { auto, manual }
})
