import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// docs/13 §8：无 Tauri 依赖。Dev 期把 /api 代理到本地 FastAPI，
// 与后端同源请求；生产由 nginx 统一代理（见 Dockerfile / nginx.conf）。
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
