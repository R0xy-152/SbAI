import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// docs/13 §8：无 Tauri 依赖。Dev 期把 /api 代理到本地 FastAPI，
// 与后端同源请求；生产由 nginx 统一代理（见 Dockerfile / nginx.conf）。
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    // 不硬编码 port：由 launch.json autoPort 分配，避免与本机其他会话冲突。
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // 仓库根静态资源（docs/13 §8.3）：背景/角色立绘由后端 FastAPI 托管在
      // 仓库根（backend/main.py `app.mount("/", StaticFiles(REPO_ROOT))`）。
      '/char': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/backgroud': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/frontend': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
