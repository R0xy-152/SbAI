import { http } from './http'
import { getPlayerId } from './saves'

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
  const { data } = await http.get<{ status: string }>('/api/health')
  return data.status === 'ok'
}

/** 新开/恢复 Opening（docs/13 Task 5 New Game 会正式接入）。附带匿名
 * player_id（docs/13 §15），供后端 Opening Complete 自动存档（Task 8）。 */
export async function createOpening(sessionId: string | null): Promise<OpeningResponse> {
  const { data } = await http.post<OpeningResponse>('/chat/opening', {
    session_id: sessionId,
    player_id: getPlayerId(),
  })
  return data
}

/** 玩家输入 → 一轮角色回应（docs/13 §27 Task 4：Player Input / Streaming /
 * Response / Presentation Directive）。不传 character_id：玩家发言是公共对
 * 话（后端 heard_by = 全体在场角色），回应者由后端 SpeakerSelector 权威决定。
 * 附带 player_id 供后端 checkpoint 自动存档（Task 8：Claude Appeared）。 */
export async function sendChat(
  sessionId: string,
  message: string,
): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/chat', {
    session_id: sessionId,
    message,
    player_id: getPlayerId(),
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

/** 推理提交（docs/13 Task 8：INF01 / INF03 checkpoint 由后端在 Narrative
 * commit 后自动存档；前端只附带 player_id）。第一章调查主线当前无 UI，先
 * 供后端 / API 测试与后续调查面板使用。 */
export async function submitDeduction(
  sessionId: string,
  message: string,
): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/deduction', {
    session_id: sessionId,
    message,
    player_id: getPlayerId(),
  })
  return data
}
