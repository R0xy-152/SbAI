import { http } from './http'

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
  quota_remaining: number
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
  quota_remaining: number
}

/** 后端权威角色在场/表现状态（docs/12 §39 Task 1，GET /api/game/state 的
 * presentation_state 字段）。前端展示完全对账于此，不从剧情条件推断。 */
export interface PresentationStateView {
  scene: string
  /** 场景粒子氛围层（docs/15 §6.1，Backend 权威下发；null = 不渲染） */
  background_effect?: string | null
  characters: Array<{
    character_id: string
    visible: boolean
    emotion: string
    slot: string | null
  }>
  input_mode: 'locked' | 'investigation'
}

/** docs/14 §2.1：后端权威「可用选项」（D3 未解锁/已完成不下发）。payload
 * 是既有执行端点的参数（如 {steps}、{character_id}），前端不解释、只回传
 *（D7）。kind 全量常量由后端定义；T2 前端只处理 investigate / chat_routing。 */
export interface GameOption {
  id: string
  label: string
  kind:
    | 'chat_routing'
    | 'investigate'
    | 'evidence_present'
    | 'deduction'
    | 'private_interview'
    | 'recovery'
    | 'narrative'
  payload: Record<string, unknown>
  hint?: string | null
}

/** Liveness probe（docs/13 Task 1 验收：Vue 可请求 FastAPI health）。 */
export async function checkBackendHealth(): Promise<boolean> {
  // T2review P2-2：baseURL 已含 /api，此前 /api/health 会请求 /api/api/health。
  const { data } = await http.get<{ status: string }>('/health')
  return data.status === 'ok'
}

/** 新开/恢复 Opening；账号身份由 HttpOnly Cookie 提供。 */
export async function createOpening(sessionId: string | null): Promise<OpeningResponse> {
  const { data } = await http.post<OpeningResponse>('/chat/opening', {
    session_id: sessionId,
  })
  return data
}

/** 玩家输入 → 一轮角色回应（docs/13 §27 Task 4：Player Input / Streaming /
 * Response / Presentation Directive）。默认不传 character_id：玩家发言是公共
 * 对话（后端 heard_by = 全体在场角色），回应者由后端 SpeakerSelector 权威决定。
 * characterId 仅在 chat_routing 选项激活时透传（docs/14 D5：走既有 Presence
 * Gate，替代已删除的切换器）。 */
export async function sendChat(
  sessionId: string | null,
  message: string,
  characterId?: string,
): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/chat', {
    session_id: sessionId ?? null,
    message,
    character_id: characterId ?? null,
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

/** 权威舞台对账（docs/12 §39 Task 1：presentation_state 是后端决定的在场事实；
 * docs/14 T1 起同通道下发当前合法 options，D3 未解锁不下发）。 */
export async function fetchGameState(sessionId: string): Promise<{
  presentation_state: PresentationStateView
  available_hotspots: Array<{
    hotspot_id: string
    title: string
    preview: string
    interaction_type: string
  }>
  hotspots: Record<string, string>
  options: GameOption[]
  /** 序章结尾后锁定的自由聊天对象；其余玩法省略。 */
  chat_character_id?: string | null
}> {
  const { data } = await http.get('/game/state', { params: { session_id: sessionId } })
  return data
}

/** 已获得证据（GET /api/game/evidence，docs/16 P7 线索窗口内容源）。 */
export interface EvidenceView {
  evidence_id: string
  title: string
  summary: string
  facts: string[]
  source_hotspot: string
  acquired: boolean
  presented_to: string[]
}

export async function fetchEvidence(sessionId: string): Promise<EvidenceView[]> {
  const { data } = await http.get<EvidenceView[]>('/game/evidence', {
    params: { session_id: sessionId },
  })
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

/** 出示证据（docs/14 T3：evidence_present 选项走既有权威端点）。 */
export async function presentEvidence(
  sessionId: string,
  characterId: string,
  evidenceId: string,
): Promise<{
  session_id: string
  event: string
  character_id: string
  evidence: Record<string, unknown>
}> {
  const { data } = await http.post('/game/present', {
    session_id: sessionId,
    character_id: characterId,
    evidence_id: evidenceId,
  })
  return data
}

/** 私审质询（docs/14 T3：private_interview 选项走既有挑战端点；
 * claim_ids / evidence_ids 由小面板按后端 payload 组装回传，D7）。 */
export async function submitPrivateInterviewChallenge(
  sessionId: string,
  characterId: string,
  claimIds: string[],
  evidenceIds: string[],
): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/private-interview/challenge', {
    session_id: sessionId,
    character_id: characterId,
    claim_ids: claimIds,
    evidence_ids: evidenceIds,
  })
  return data
}

/** Recovery 开始（docs/14 T4：recovery 选项走既有权威端点，session_id 为
 * 查询参数，与后端路由签名一致）。 */
export async function startRecovery(sessionId: string): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/recovery/start', null, {
    params: { session_id: sessionId },
  })
  return data
}

/** Recovery 单步操作（PREVIEW/VERIFY/PROTECT/REPAIR/OPTIMIZE × 节点）。 */
export async function recoveryAction(
  sessionId: string,
  action: string,
  target: string,
  actor: string,
): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/recovery/action', {
    session_id: sessionId,
    action,
    target,
    actor,
  })
  return data
}

/** 进入 Security Review（docs/14 T4 narrative 选项）。 */
export async function securityReviewStart(sessionId: string): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/security-review/start', null, {
    params: { session_id: sessionId },
  })
  return data
}

/** Security Review 自证（按后端权威顺序逐个听取）。 */
export async function securityReviewTestify(
  sessionId: string,
  characterId: string,
): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/security-review/testify', {
    session_id: sessionId,
    character_id: characterId,
  })
  return data
}

/** Security Review 清理抉择（DELETE_* / DELEGATE / CONFIRM_KEEP_CHATGPT）。 */
export async function securityReviewCleanup(
  sessionId: string,
  action: string,
): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/security-review/cleanup', {
    session_id: sessionId,
    action,
  })
  return data
}

/** 拒绝清理（To Be Continued）。 */
export async function securityReviewRejectCleanup(
  sessionId: string,
): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/security-review/reject-cleanup', null, {
    params: { session_id: sessionId },
  })
  return data
}

/** 推理提交（docs/13 Task 8：INF01 / INF03 checkpoint 由后端在 Narrative
 * commit 后自动存档）。docs/14 T3 起由「质疑…」
 * 提示选项 + 主输入框一次性推理模式调用。 */
export async function submitDeduction(
  sessionId: string,
  message: string,
): Promise<Record<string, unknown>> {
  const { data } = await http.post('/game/deduction', {
    session_id: sessionId,
    message,
  })
  return data
}
