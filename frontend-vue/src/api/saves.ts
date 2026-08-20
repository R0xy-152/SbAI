import { http } from './http'

// Save API（docs/13 §20）。Task 6 后端 Save Snapshot、Task 7 存档 UI 接入。
// Snapshot 由 Backend Capture（docs/13 §14.2），前端只传 player_id /
// session_id / slot_index；List 只返回 slot 元数据，不含 snapshot（§29）。

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

const PLAYER_KEY = 'gal_player_id'

/** 匿名 Player 身份（docs/13 §15）：首次打开生成 UUID 存 localStorage，
 * 之后所有 Save API 带上该 player_id。不是登录凭据/安全边界。
 *
 * 注意：crypto.randomUUID 只在安全上下文（HTTPS / localhost）可用；
 * 公网 IP:80 直连（HTTP 非安全上下文）下会抛
 * "crypto.randomUUID is not a function"（上线实测踩坑），因此保留手工
 * 生成回退——player_id 本就只是匿名命名空间，不承担安全职责。 */
export function getPlayerId(): string {
  let id = localStorage.getItem(PLAYER_KEY)
  if (!id) {
    id = generateUuid()
    localStorage.setItem(PLAYER_KEY, id)
  }
  return id
}

function generateUuid(): string {
  const c = globalThis.crypto
  if (typeof c !== 'undefined' && typeof c.randomUUID === 'function') {
    return c.randomUUID()
  }
  // 非安全上下文回退（RFC4122 v4 形状，够用即可）
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (ch) => {
    const r = (Math.random() * 16) | 0
    const v = ch === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/** docs/13 §20.1：列出该 player 的存档（auto + manual[6]，空 slot 由前端渲染）。 */
export async function listSaves(): Promise<SaveListResponse> {
  const { data } = await http.get<SaveListResponse>('/saves', {
    params: { player_id: getPlayerId() },
  })
  return data
}

/** docs/13 §20.2：手动保存到 1..6 号 slot；snapshot 由 Backend Capture。 */
export async function manualSave(
  sessionId: string,
  slot: number,
  title?: string | null,
): Promise<GameSaveInfo> {
  const { data } = await http.post<GameSaveInfo>(`/saves/manual/${slot}`, {
    player_id: getPlayerId(),
    session_id: sessionId,
    ...(title ? { title } : {}),
  })
  return data
}

/** docs/13 §21：覆盖唯一 AUTO slot（checkpoint 由 Task 8 接线；端点 Task 6 可用）。 */
export async function autoSave(sessionId: string): Promise<GameSaveInfo> {
  const { data } = await http.post<GameSaveInfo>('/saves/auto', {
    player_id: getPlayerId(),
    session_id: sessionId,
  })
  return data
}

/** docs/13 §20.3：Load 创建新 Active Session，返回 new_session_id + GameViewState。 */
export async function loadSave(saveId: string): Promise<LoadResult> {
  const { data } = await http.post<LoadResult>(`/saves/${saveId}/load`, {
    player_id: getPlayerId(),
  })
  return data
}

/** docs/13 §26.3：删除一个手动 slot。 */
export async function deleteSave(slot: number): Promise<boolean> {
  const { data } = await http.delete<{ deleted: boolean }>('/saves/manual/' + slot, {
    params: { player_id: getPlayerId() },
  })
  return data.deleted
}
