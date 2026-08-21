import { chromium } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

const baseURL = process.env.GAL_BASE_URL ?? 'http://127.0.0.1:5173'
const outDir = process.env.GAL_OUT_DIR
const cases = [
  { name: 'narrow', width: 390, height: 844, columns: 1 },
  { name: '16x9', width: 1920, height: 1080, columns: 2 },
  { name: '21x9', width: 2520, height: 1080, columns: 2 },
  { name: '32x9', width: 3840, height: 1080, columns: 2, containHeight: true },
]

const browser = await chromium.launch({ headless: true })
try {
  if (outDir) await fs.mkdir(outDir, { recursive: true })
  for (const item of cases) {
    const context = await browser.newContext({ viewport: { width: item.width, height: item.height } })
    const page = await context.newPage()
    const browserErrors = []
    page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`))
    page.on('console', (message) => {
      if (message.type() === 'error') browserErrors.push(`console: ${message.text()}`)
    })
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.addInitScript(() => {
      localStorage.setItem('gal_settings', JSON.stringify({
        mainMenuStarsEnabled: false,
        mainMenuMeteorsEnabled: false,
        globalMouseTrailEnabled: false,
        clickAnimationEnabled: false,
      }))
    })
    await page.route('**/backgroud/background_title_21x9.png', (route) => route.fulfill({
      path: path.resolve(process.cwd(), '..', 'backgroud', 'background_title_21x9.png'),
      contentType: 'image/png',
    }))
    await page.route('**/api/auth/me', (route) => route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'chapter-smoke', display_name: 'Chapter Smoke',
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

    await page.goto(`${baseURL}/chapters`, { waitUntil: 'networkidle' })
    await page.locator('.chapter-grid').waitFor({ timeout: 10_000 })

    const actual = await page.evaluate(() => {
      const cards = [...document.querySelectorAll('button.chapter-card')]
      const gridStyle = getComputedStyle(document.querySelector('.chapter-grid'))
      const sharpStyle = getComputedStyle(document.querySelector('.chapter-bg-sharp'))
      return {
        headings: [document.querySelector('h1')?.textContent?.trim(), document.querySelector('.chapter-heading p')?.textContent?.trim()],
        chapters: cards.map((card) => card.querySelector('.chapter-name')?.textContent?.trim()),
        disabled: cards.map((card) => card.disabled),
        columns: gridStyle.gridTemplateColumns.split(' ').length,
        background: sharpStyle.backgroundImage,
        backgroundSize: sharpStyle.backgroundSize,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }
    })

    if (actual.headings.join('/') !== '开始游戏/章节选择') throw new Error(`${item.name}: heading mismatch`)
    if (actual.chapters.join('/') !== '序章/第一章/第二章/第三章/第四章/终章') throw new Error(`${item.name}: chapter order mismatch`)
    if (actual.disabled.join(',') !== 'false,true,true,true,true,true') throw new Error(`${item.name}: unlock state mismatch`)
    if (actual.columns !== item.columns) throw new Error(`${item.name}: expected ${item.columns} columns, got ${actual.columns}`)
    if (!actual.background.includes('background_title_21x9.png')) throw new Error(`${item.name}: wrong background ${actual.background}`)
    if (item.containHeight && actual.backgroundSize !== 'auto 100%') throw new Error(`${item.name}: expected auto 100%, got ${actual.backgroundSize}`)
    if (actual.scrollWidth > actual.clientWidth) throw new Error(`${item.name}: horizontal overflow ${actual.scrollWidth}/${actual.clientWidth}`)
    if (browserErrors.length) throw new Error(`${item.name}: ${browserErrors.join('; ')}`)

    if (outDir) await page.screenshot({ path: path.join(outDir, `${item.name}.png`), fullPage: item.columns === 1 })
    console.log(`${item.name}: PASS columns=${actual.columns} backgroundSize=${actual.backgroundSize}`)
    await context.close()
  }
} finally {
  await browser.close()
}
