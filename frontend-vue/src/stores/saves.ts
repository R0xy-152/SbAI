import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { GameSaveInfo } from '../api/saves'

// 存档列表（docs/13 §12.4 / §20.1）。Task 5 使用「是否有任何存档」决定
// Continue / New Game 行为；具体 Save/Load 数据在 Task 6/7 接入后端。
export const useSavesStore = defineStore('saves', () => {
  const auto = ref<GameSaveInfo | null>(null)
  const manual = ref<(GameSaveInfo | null)[]>([null, null, null, null, null, null])

  /** 是否有任何有效存档（Continue 可用的依据，docs/13 §12.3）。 */
  const hasAnySave = computed(
    () => auto.value !== null || manual.value.some((s) => s !== null),
  )

  /** 从后端存档列表刷新（Task 6 接入后端后填充；当前为空列表）。 */
  async function refresh(): Promise<void> {
    // docs/13 §12.3：无存档时 Continue 必须禁用，不得创建空 Session 冒充。
    // Task 6 实现 Save API 后在此 fetch 并填充 auto/manual。
    auto.value = null
    manual.value = [null, null, null, null, null, null]
  }

  return { auto, manual, hasAnySave, refresh }
})
