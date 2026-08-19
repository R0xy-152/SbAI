import { defineConfig } from '@playwright/test'

// docs/13 §26.2 / §26.4：两个 viewport 的视觉回归 + 第一章主线 E2E。
// webServer：backend（GAL_PROVIDER=mock fixture 契约）+ vite dev（strictPort）。
// 单 worker：mock 后端共享 JSON 数据目录，串行保证确定性。
export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  expect: {
    // 0.5% 容差：吸收字体渲染噪声（通常<0.1%），仍能检测 UI 元素级变化
    //（切换器删除约 1.3%，此前 2% 容差会把它放行）。
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.005,
      animations: 'disabled',
      caret: 'hide',
    },
  },
  snapshotDir: './tests/visual/baselines',
  projects: [
    { name: 'desktop-1366x768', use: { viewport: { width: 1366, height: 768 } } },
    { name: 'desktop-1920x1080', use: { viewport: { width: 1920, height: 1080 } } },
  ],
  webServer: [
    {
      command: '.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000',
      cwd: '../backend',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { ...process.env, GAL_PROVIDER: 'mock' },
    },
    {
      command: 'npm run dev -- --port 5173 --strictPort',
      cwd: '.',
      port: 5173,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
})
