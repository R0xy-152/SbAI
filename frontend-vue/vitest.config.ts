import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// 独立于 vite.config.ts（docs/13 §26.1）：测试环境不加载 tailwind 插件与
// dev proxy。spec 全部显式 import（不用 globals），保持 vue-tsc 干净。
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.spec.ts'],
    globals: false,
  },
})
