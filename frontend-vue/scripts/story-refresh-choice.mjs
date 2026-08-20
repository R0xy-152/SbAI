import { chromium } from '@playwright/test'

const BASE = 'http://localhost:8080'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
page.on('pageerror', (e) => console.log('[pageerror]', String(e).slice(0, 300)))

await page.goto(BASE + '/')
await page.evaluate(() => {
  localStorage.removeItem('gal_session_id')
  localStorage.setItem('gal_settings', JSON.stringify({ textSpeed: 5, loadingTransitionEnabled: false, eyeOpenTransitionEnabled: false, mainMenuStarsEnabled: false, mainMenuMeteorsEnabled: false, globalMouseTrailEnabled: false, clickAnimationEnabled: false, sceneEffectsEnabled: false }))
})
await page.reload()
await page.getByRole('button', { name: '开始游戏' }).click()
await page.waitForURL('**/story')

const btn = page.locator('#sendButton')
for (let i = 0; i < 80; i++) {
  const choice = page.locator('[data-testid="story-choice-window"]')
  if ((await choice.count()) > 0) {
    console.log('choice reached at iter', i)
    await page.waitForTimeout(1300)
    const labels = await choice.locator('button').allTextContents()
    console.log('labels before reload:', JSON.stringify(labels.map((s) => s.trim())))
    // 刷新页面 → 应恢复同一选项节点
    await page.reload()
    await page.waitForURL('**/story')
    const choice2 = page.locator('[data-testid="story-choice-window"]')
    await choice2.waitFor({ state: 'visible', timeout: 20000 })
    await page.waitForTimeout(1300)
    const labels2 = await choice2.locator('button').allTextContents()
    console.log('labels after reload:', JSON.stringify(labels2.map((s) => s.trim())))
    console.log('restore-match:', JSON.stringify(labels.map((s) => s.trim())) === JSON.stringify(labels2.map((s) => s.trim())))
    await page.screenshot({ path: 'D:/gal/validation-results/story-quicklaunch/evidence/05-refresh-at-choice.png' })
    // 继续选第一个选项，确认刷新后仍可继续推进
    await choice2.locator('button').first().click()
    await page.waitForFunction(() => !document.querySelector('[data-testid="story-choice-window"]'), { timeout: 15000 })
    console.log('continue after reload: OK')
    break
  }
  if ((await btn.count()) > 0 && (await btn.isEnabled())) await btn.click()
  await page.waitForTimeout(140)
}
await browser.close()
