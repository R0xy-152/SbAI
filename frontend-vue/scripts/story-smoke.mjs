// 快速上线固定剧本 UI 冒烟测试（临时）：docker 栈 http://localhost:8080。
// 走：标题 → 开始游戏 → 逐行推进 → 3 个选项窗口 → 结局画面，全程截图。
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

// 默认本机 docker 栈；公网/服务器复核用 GAL_BASE_URL 环境变量覆盖
const BASE = process.env.GAL_BASE_URL || 'http://localhost:8080'
const OUT = 'D:/gal/validation-results/story-quicklaunch/evidence'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
page.on('console', (msg) => {
  if (msg.type() === 'error') console.log('[console.error]', msg.text().slice(0, 200))
})
page.on('pageerror', (err) => console.log('[pageerror]', String(err).slice(0, 300)))

await page.goto(BASE + '/')
await page.evaluate(() => {
  localStorage.removeItem('gal_session_id')
  localStorage.setItem(
    'gal_settings',
    JSON.stringify({
      textSpeed: 5,
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
await page.screenshot({ path: OUT + '/01-title.png' })

await page.getByRole('button', { name: '开始游戏' }).click()
await page.waitForURL('**/story', { timeout: 15000 })
// 等第一句台词打完（textarea 有内容）
await page.waitForFunction(
  () => (document.querySelector('textarea#inputMessage')?.value ?? '').length > 0,
  { timeout: 30000 },
)
await page.screenshot({ path: OUT + '/02-story-start.png' })

const btn = page.locator('#sendButton')
let choiceCount = 0
let ended = false
for (let i = 0; i < 500; i++) {
  const choice = page.locator('[data-testid="story-choice-window"]')
  if ((await choice.count()) > 0) {
    choiceCount++
    // 等交错入场动画完成（每个按钮延迟 100ms + 500ms 过渡）再截图
    await page.waitForTimeout(1300)
    await page.screenshot({ path: OUT + '/03-choice-' + choiceCount + '.png' })
    await choice.locator('button:not(:disabled)').first().click()
    // 离场动画（300ms）+ 后端提交期间窗口仍在，等它真正消失再继续，
    // 避免对同一窗口二次截图/点击（定位器会一直等待不存在的按钮）。
    await page.waitForFunction(
      () => !document.querySelector('[data-testid="story-choice-window"]'),
      { timeout: 15000 },
    )
    continue
  }
  const ending = page.locator('[data-testid="story-ending"]')
  if ((await ending.count()) > 0) {
    ended = true
    await page.screenshot({ path: OUT + '/04-ending.png' })
    break
  }
  if ((await btn.count()) > 0 && (await btn.isEnabled())) {
    await btn.click()
  }
  await page.waitForTimeout(140)
}

console.log(JSON.stringify({ choiceCount, ended, url: page.url() }))
// 结局后点「返回标题」验证可回标题
if (ended) {
  await page.locator('[data-testid="story-ending-return"]').click()
  await page.waitForURL(BASE + '/', { timeout: 15000 })
  console.log('return to title: OK')
}
await browser.close()
