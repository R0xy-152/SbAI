import axios from 'axios'

// docs/13 §8.2：UI 组件禁止散落 fetch('/api/...')，统一走本层。
// Dev 期 vite 代理 /api → 本地 FastAPI；生产由 nginx 代理。
// 130s：覆盖后端 DeepSeek 60s 超时 + 一次瞬时故障重试的最坏情形
//（thinking 模式 + 长上下文回合实测可超过 30s，原 30s 会让长回合被前端先掐断）。
export const http = axios.create({ baseURL: '/api', timeout: 130_000, withCredentials: true })

let unauthorizedHandler: (() => void) | null = null

export function setUnauthorizedHandler(handler: () => void) {
  unauthorizedHandler = handler
}

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error?.response?.status === 401 &&
      !['/auth/login', '/auth/me'].includes(error?.config?.url)
    ) {
      unauthorizedHandler?.()
    }
    return Promise.reject(error)
  },
)
