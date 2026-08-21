// docs/19 序章 UI 冒烟：章节入口 → 无序探班 → 3/2/1 剩余选项 → 后日谈。
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE = process.env.GAL_BASE_URL || 'http://localhost:8080'
const API_BASE = process.env.GAL_API_BASE_URL || ''
const OUT =
  process.env.GAL_OUT_DIR || 'D:/gal/validation-results/prologue-implementation/evidence'
const visitOrder = (process.env.GAL_VISIT_ORDER || 'claude,deepseek,chatgpt').split(',')
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
if (API_BASE) {
  const baseUrl = new URL(BASE)
  await page.route(`${baseUrl.origin}/{api,char,backgroud}/**`, async (route) => {
    const source = new URL(route.request().url())
    const response = await route.fetch({ url: API_BASE + source.pathname + source.search })
    await route.fulfill({ response })
  })
}

await page.goto(BASE + '/')
await page.evaluate(() => {
  localStorage.clear()
  localStorage.setItem(
    'gal_settings',
    JSON.stringify({
      textSpeed: 1,
      loadingTransitionEnabled: false,
      eyeOpenTransitionEnabled: false,
      mainMenuStarsEnabled: false,
      mainMenuMeteorsEnabled: false,
      globalMouseTrailEnabled: false,
      clickAnimationEnabled: false,
      sceneEffectsEnabled: false,
    }),
  )
})
await page.reload()
await page.getByRole('button', { name: '开始游戏' }).click()
await page.waitForURL('**/chapters')
await page.getByRole('button', { name: '序章' }).click()
await page.waitForURL('**/story?story_id=prologue')
await page.waitForSelector('#sendButton', { timeout: 15_000 })
await page.screenshot({ path: OUT + '/01-opening.png' })

const observedChoices = []
let visitIndex = 0
let reunionCaptured = false
for (let step = 0; step < 1_000; step++) {
  const titleCards = page.locator('[data-testid="scene-title-card"]')
  const titleTexts = await titleCards.allTextContents()
  if (!reunionCaptured && titleTexts.some((text) => text.includes('三人集合'))) {
    reunionCaptured = true
    await page.waitForTimeout(1_000)
    await page.screenshot({ path: OUT + '/05-reunion.png' })
  }

  const choice = page.locator('[data-testid="story-choice-window"]')
  if ((await choice.count()) > 0) {
    await page.waitForTimeout(750)
    const labels = await choice.locator('button span:last-child').allTextContents()
    observedChoices.push(labels)
    await page.screenshot({ path: OUT + `/choice-${observedChoices.length}.png` })
    const isFinalChoice = labels[0]?.startsWith('与 ')
    const target = isFinalChoice ? 'chatgpt' : visitOrder[visitIndex++]
    const displayName =
      target === 'deepseek' ? 'DeepSeek' : target === 'chatgpt' ? 'ChatGPT' : 'Claude'
    await choice.locator('button').filter({ hasText: displayName }).first().click()
    if (isFinalChoice) break
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="story-choice-window"]'),
      { timeout: 15_000 },
    )
    continue
  }
  const proceed = page.locator('#sendButton')
  if ((await proceed.count()) > 0) await proceed.click()
  await page.waitForTimeout(35)
}

await page.waitForURL('**/game?character=chatgpt', { timeout: 15_000 })
await page.waitForTimeout(800)
await page.screenshot({ path: OUT + '/06-chatgpt-aftertalk.png' })

const expected = [
  ['去找 DeepSeek', '去找 ChatGPT', '去找 Claude'],
  ['去找 DeepSeek', '去找 ChatGPT'],
  ['去找 ChatGPT'],
  ['与 DeepSeek 聊天', '与 ChatGPT 聊天', '与 Claude 聊天'],
]
if (JSON.stringify(observedChoices) !== JSON.stringify(expected)) {
  throw new Error(`unexpected choices: ${JSON.stringify(observedChoices)}`)
}
console.log(
  JSON.stringify({
    status: 'PASS',
    visitOrder,
    observedChoices,
    reunionCaptured,
    url: page.url(),
  }),
)
await browser.close()
