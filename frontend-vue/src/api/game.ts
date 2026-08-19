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
