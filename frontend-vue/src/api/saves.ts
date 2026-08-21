import { http } from './http'

// Save API（docs/13 §20）。Task 6 后端 Save Snapshot、Task 7 存档 UI 接入。
// Snapshot 由 Backend Capture（docs/13 §14.2）；账号身份只来自 HttpOnly
// Cookie，前端只传 session_id / slot_index。

export type SaveSlotType = 'AUTO' | 'MANUAL'

export interface GameSaveInfo {
  id: string
  player_id: string
  slot_type: SaveSlotType
  /** AUTO 为 null，MANUAL 为 1..6。 */
  slot_index: number | null
  title: string | null
  source_session_id: string | null
  chapter_id: string | null
  phase: string | null
  created_at: string
  updated_at: string
}

export interface SaveListResponse {
  auto: GameSaveInfo | null
  manual: Array<GameSaveInfo | null>
}

/** Load 结果（docs/13 §20.3）：new_session_id + initial GameViewState。 */
export interface LoadResult {
  session_id: string
  /** 故事游标快照；null = 该存档从未进入故事模式（旧玩法存档）。 */
  story_cursor: { node_index: number } | null
  /** 故事是否已走到结局（结局后为自由聊天态，应进 /game）。 */
  story_finished: boolean
  state: {
    presentation_state: PresentationStateView
    available_hotspots: Array<{
      hotspot_id: string
      title: string
      preview: string
      interaction_type: string
    }>
    hotspots: Record<string, string>
    /** docs/14 T2：Load 恢复后同样对账当前合法选项（D3）。 */
    options: GameOption[]
  }
  history: {
    session_id: string
    messages: Array<{ role: string; character_id: string | null; content: string }>
  }
}

// 复用 game.ts 的权威角色在场 / 选项类型（同一契约，docs/13 §9.2 / docs/14）
import type { GameOption, PresentationStateView } from './game'

/** 存档目标路由：故事未完结 → /story（继续剧本）；已完结 / 旧玩法 → /game（自由聊天）。 */
export type SaveTargetRoute = '/story' | '/game'

export function saveTargetRoute(
  storyCursor: { node_index: number } | null,
  storyFinished: boolean,
): SaveTargetRoute {
  if (storyCursor && !storyFinished) return '/story'
  return '/game'
}

/** docs/13 §20.1：列出该 player 的存档（auto + manual[6]，空 slot 由前端渲染）。 */
export async function listSaves(): Promise<SaveListResponse> {
  const { data } = await http.get<SaveListResponse>('/saves')
  return data
}

/** docs/13 §20.2：手动保存到 1..6 号 slot；snapshot 由 Backend Capture。 */
export async function manualSave(
  sessionId: string,
  slot: number,
  title?: string | null,
): Promise<GameSaveInfo> {
  const { data } = await http.post<GameSaveInfo>(`/saves/manual/${slot}`, {
    session_id: sessionId,
    ...(title ? { title } : {}),
  })
  return data
}

/** docs/13 §21：覆盖唯一 AUTO slot（checkpoint 由 Task 8 接线；端点 Task 6 可用）。 */
export async function autoSave(sessionId: string): Promise<GameSaveInfo> {
  const { data } = await http.post<GameSaveInfo>('/saves/auto', {
    session_id: sessionId,
  })
  return data
}

/** docs/13 §20.3：Load 创建新 Active Session，返回 new_session_id + GameViewState。 */
export async function loadSave(saveId: string): Promise<LoadResult> {
  const { data } = await http.post<LoadResult>(`/saves/${saveId}/load`, {})
  return data
}

/** docs/13 §26.3：删除一个手动 slot。 */
export async function deleteSave(slot: number): Promise<boolean> {
  const { data } = await http.delete<{ deleted: boolean }>('/saves/manual/' + slot)
  return data.deleted
}
