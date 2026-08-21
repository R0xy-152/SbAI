import { chromium } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

const baseURL = process.env.GAL_BASE_URL ?? 'http://127.0.0.1:5173'
const outDir = process.env.GAL_OUT_DIR
const cases = [
  { name: '16x10', width: 1280, height: 800, asset: 'background_title.png', columns: false },
  { name: '16x9', width: 1920, height: 1080, asset: 'background_title.png', columns: false },
  { name: 'browser-2x1', width: 1920, height: 950, asset: 'background_title_21x9.png', columns: false },
  { name: '21x9', width: 2520, height: 1080, asset: 'background_title_21x9.png', columns: false },
  { name: '32x9', width: 3840, height: 1080, asset: 'background_title_21x9.png', columns: false, containHeight: true },
]

const browser = await chromium.launch({ headless: true })
try {
  if (outDir) await fs.mkdir(outDir, { recursive: true })
  for (const item of cases) {
    const context = await browser.newContext({ viewport: { width: item.width, height: item.height } })
    const page = await context.newPage()
    page.on('pageerror', (error) => console.error(`${item.name}: pageerror: ${error.message}`))
    page.on('console', (message) => {
      if (message.type() === 'error') console.error(`${item.name}: console: ${message.text()}`)
    })
    page.on('requestfailed', (request) => console.error(`${item.name}: request failed: ${request.url()} ${request.failure()?.errorText}`))
    for (const asset of ['background_title.png', 'background_title_21x9.png']) {
      await page.route(`**/backgroud/${asset}`, (route) => route.fulfill({
        path: path.resolve(process.cwd(), '..', 'backgroud', asset),
        contentType: 'image/png',
      }))
    }
    await page.route('**/api/auth/me', (route) => route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'responsive-smoke', display_name: 'Responsive Smoke',
        quota_total: 100, quota_used: 0, quota_remaining: 100,
      }),
    }))
    await page.route('**/api/saves', (route) => route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ auto: null, manual: [null, null, null, null, null, null] }),
    }))
    await page.route('**/api/health', (route) => route.fulfill({
      contentType: 'application/json', body: JSON.stringify({ status: 'ok' }),
    }))
    await page.goto(baseURL, { waitUntil: 'networkidle' })
    await page.locator('.title-bg-sharp').waitFor({ timeout: 10_000 }).catch(async () => {
      throw new Error(`${item.name}: title view missing at ${page.url()} (${await page.locator('body').innerText()})`)
    })
    const actual = await page.evaluate(() => {
      const sharp = document.querySelector('.title-bg-sharp')
      const nav = document.querySelector('nav')
      const style = getComputedStyle(sharp)
      return {
        image: style.backgroundImage,
        size: style.backgroundSize,
        columns: nav?.classList.contains('grid') ?? false,
      }
    })
    if (!actual.image.includes(item.asset)) {
      throw new Error(`${item.name}: expected ${item.asset}, got ${actual.image}`)
    }
    if (actual.columns !== item.columns) {
      throw new Error(`${item.name}: columns expected ${item.columns}, got ${actual.columns}`)
    }
    if (item.containHeight && actual.size !== 'auto 100%') {
      throw new Error(`${item.name}: expected auto 100%, got ${actual.size}`)
    }
    if (outDir) {
      await page.screenshot({ path: path.join(outDir, `${item.name}.png`) })
    }
    console.log(`${item.name}: PASS asset=${item.asset} columns=${actual.columns} size=${actual.size}`)
    await context.close()
  }
} finally {
  await browser.close()
}
