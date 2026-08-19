import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LoadResult } from '../api/saves'

// 会话状态（docs/13 §14.1 / §12.2）。session_id 作为「恢复当前会话」的
// 非敏感标识暂存 localStorage（现有旧前端同约定）。Opening 的创建与台词
// 渲染由 GameView 负责（docs/13 Task 4 接入 FastAPI 后 GameView 自持生命周期）。
//
// pendingLoad（docs/13 §20.3）：Load 结果（new_session_id + GameViewState）
// 由 LoadView/TitleView 暂存，GameView 挂载时消费并渲染。中间态放在 store
// 里而不是 URL query，避免刷新后残留过期 Load 状态。
export const useGameStore = defineStore('game', () => {
  const sessionId = ref<string | null>(localStorage.getItem('gal_session_id'))
  const busy = ref(false)
  const error = ref<string | null>(null)
  /** 待消费的 Load 结果；GameView 消费后清空。 */
  const pendingLoad = ref<LoadResult | null>(null)

  return { sessionId, busy, error, pendingLoad }
})
