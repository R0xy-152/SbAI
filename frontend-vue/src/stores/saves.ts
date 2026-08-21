import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { GameSaveInfo, LoadResult, SaveListResponse } from '../api/saves'
import {
  autoSave as apiAutoSave,
  deleteSave as apiDeleteSave,
  listSaves,
  loadSave as apiLoadSave,
  manualSave as apiManualSave,
} from '../api/saves'

// 存档列表（docs/13 §12.4 / §20.1）。Task 7 接入后端 Save API：refresh 拉取
// {auto, manual:[6]}（空 slot 前端明确渲染），saveManual/deleteManual 操作后
// 本地重映射，避免每次全量 fetch；账号归属由后端登录 Cookie 决定。
//（docs/13 §15：匿名浏览器命名空间）。
export const useSavesStore = defineStore('saves', () => {
  const auto = ref<GameSaveInfo | null>(null)
  const manual = ref<(GameSaveInfo | null)[]>([null, null, null, null, null, null])
  const loading = ref(false)
  const error = ref<string | null>(null)

  /** 是否有任何有效存档（Continue 可用的依据，docs/13 §12.3）。 */
  const hasAnySave = computed(
    () => auto.value !== null || manual.value.some((s) => s !== null),
  )

  /** 最近更新的有效存档（docs/13 §12.3 Continue 的目标：优先级 = 更新时间）。 */
  const mostRecent = computed<GameSaveInfo | null>(() => {
    const all = [
      ...(auto.value ? [auto.value] : []),
      ...manual.value.filter((s): s is GameSaveInfo => s !== null),
    ]
    if (all.length === 0) return null
    return all.reduce((a, b) => (a.updated_at >= b.updated_at ? a : b))
  })

  function applyList(list: SaveListResponse): void {
    auto.value = list.auto
    manual.value = list.manual.length === 6 ? list.manual : Array.from({ length: 6 }, (_, i) => list.manual[i] ?? null)
  }

  /** 从后端刷新存档列表（docs/13 §20.1）。 */
  async function refresh(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      applyList(await listSaves())
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 手动保存到 1..6 号 slot（docs/13 §20.2；snapshot 由 Backend Capture）。 */
  async function saveManual(
    sessionId: string,
    slot: number,
    title?: string | null,
  ): Promise<GameSaveInfo> {
    const save = await apiManualSave(sessionId, slot, title)
    manual.value[slot - 1] = save
    return save
  }

  /** 覆盖唯一 AUTO slot（docs/13 §21；Task 8 接 checkpoint）。 */
  async function saveAuto(sessionId: string): Promise<GameSaveInfo> {
    const save = await apiAutoSave(sessionId)
    auto.value = save
    return save
  }

  /** 删除一个手动 slot（docs/13 §26.3）。 */
  async function deleteManual(slot: number): Promise<void> {
    await apiDeleteSave(slot)
    manual.value[slot - 1] = null
  }

  /** Load：Backend 创建新 Active Session，返回 new_session_id + GameViewState
   *（docs/13 §20.3；本 store 不自行改写 Game Truth）。 */
  async function load(saveId: string): Promise<LoadResult> {
    return apiLoadSave(saveId)
  }

  return {
    auto,
    manual,
    loading,
    error,
    hasAnySave,
    mostRecent,
    refresh,
    saveManual,
    saveAuto,
    deleteManual,
    load,
  }
})
