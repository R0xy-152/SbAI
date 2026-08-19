import axios from 'axios'

// docs/13 §8.2：UI 组件禁止散落 fetch('/api/...')，统一走本层。
// Dev 期 vite 代理 /api → 本地 FastAPI；生产由 nginx 代理。
export const http = axios.create({ baseURL: '/api', timeout: 30_000 })
