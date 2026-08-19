import axios from 'axios'

// docs/13 §8.2：UI 组件禁止散落 fetch('/api/...')，统一走本层。
// Dev 期 vite 代理 /api → 本地 FastAPI；生产由 nginx 代理。
const http = axios.create({ baseURL: '/api', timeout: 30_000 })

export interface OpeningResponse {
  session_id: string
  character_id: string
  dialogue: string
  message_count: number
  emotion: string
  animation: string
  presentation: string[]
  presentation_actions: unknown[]
  claim_refs: unknown[]
  script_sequence: unknown[]
}

export interface PresentationAction {
  type: string
  character_id?: string | null
  emotion?: string | null
  animation?: string | null
  slot?: string | null
  scale?: number | null
  offset_x?: number | null
  offset_y?: number | null
  background?: string | null
  transition?: string | null
  intensity?: string | null
}

export interface ChatResponse {
  session_id: string
  character_id: string
  dialogue: string
  message_count: number
  emotion: string
  animation: string
  presentation: string[]
  presentation_actions: PresentationAction[]
  claim_refs: string[]
  script_sequence: Array<{
    speaker: string
    dialogue: string
    emotion?: string | null
    animation?: string | null
  }>
}

/** 后端权威角色在场/表现状态（docs/12 §39 Task 1，GET /api/game/state 的
 * presentation_state 字段）。前端展示完全对账于此，不从剧情条件推断。 */
export interface PresentationStateView {
  scene: string
  characters: Array<{
    character_id: string
    visible: boolean
    emotion: string
    slot: string | null
  }>
  input_mode: 'locked' | 'investigation'
}

/** Liveness probe（docs/13 Task 1 验收：Vue 可请求 FastAPI health）。 */
export async function checkBackendHealth(): Promise<boolean> {
  const { data } = await http.get<{ status: string }>('/health')
  return data.status === 'ok'
}

/** 新开/恢复 Opening（docs/13 Task 5 New Game 会正式接入）。 */
export async function createOpening(sessionId: string | null): Promise<OpeningResponse> {
  const { data } = await http.post<OpeningResponse>('/chat/opening', {
    session_id: sessionId,
  })
  return data
}

/** 玩家输入 → 一轮角色回应（docs/13 §27 Task 4：Player Input / Streaming /
 * Response / Presentation Directive）。 */
export async function sendChat(
  sessionId: string,
  message: string,
  characterId?: string,
): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/chat', {
    session_id: sessionId,
    message,
    ...(characterId ? { character_id: characterId } : {}),
  })
  return data
}

/** 调查热点 action（docs/13 §27：03:17 需要 EV01，经纸面调查获取）。 */
export async function sendInvestigationAction(
  sessionId: string,
  action: 'INSPECT_HOTSPOT' | 'PAPER_RUBBING_COMPLETE',
  hotspotId: string,
): Promise<{
  session_id: string
  outcome: string
  hotspot_id: string
  evidence_id: string | null
  state: {
    presentation_state: PresentationStateView
    available_hotspots: Array<{
      hotspot_id: string
      title: string
      preview: string
      interaction_type: string
    }>
    hotspots: Record<string, string>
  }
  presentation: string[]
  presentation_actions: PresentationAction[]
}> {
  const { data } = await http.post('/game/action', {
    session_id: sessionId,
    action,
    hotspot_id: hotspotId,
  })
  return data
}

/** 权威舞台对账（docs/12 §39 Task 1：presentation_state 是后端决定的在场事实）。 */
export async function fetchGameState(sessionId: string): Promise<{
  presentation_state: PresentationStateView
  available_hotspots: Array<{
    hotspot_id: string
    title: string
    preview: string
    interaction_type: string
  }>
  hotspots: Record<string, string>
}> {
  const { data } = await http.get('/game/state', { params: { session_id: sessionId } })
  return data
}

/** 会话对话历史（docs/01 §18）。 */
export async function fetchHistory(sessionId: string): Promise<{
  session_id: string
  messages: Array<{ role: string; character_id: string | null; content: string }>
}> {
  const { data } = await http.get('/chat/history', { params: { session_id: sessionId } })
  return data
}
