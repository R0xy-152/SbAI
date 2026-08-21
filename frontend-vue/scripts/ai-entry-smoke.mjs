// AI 对话玩法新开局冒烟测试（2026-08-21 用户需求验证）：
// 标题 → 「AI 对话玩法」→ /game：
//   1) 不调用 /api/chat/opening、不出现「你醒了」开场白；
//   2) 不自动弹出「选择行动」选项窗口（首个回合结束点继续也不弹）；
//   3) 常驻背景图为 /backgroud/background_ai.png；
//   4) 输入立即可用；首个玩家消息经 /api/chat 创建会话（session_id 写回）。
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE = process.env.GAL_BASE_URL || 'http://localhost:5173'
const OUT = process.env.GAL_OUT_DIR || 'D:/gal/validation-results/ai-entry-and-bg/evidence'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
page.on('pageerror', (err) => console.log('[pageerror]', String(err).slice(0, 300)))

const apiCalls = []
const bgRequests = []
page.on('request', (req) => {
  if (req.url().includes('/api/')) apiCalls.push(req.method() + ' ' + req.url().split('?')[0])
  if (req.url().includes('/backgroud/')) bgRequests.push(req.url())
})

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

await page.getByRole('button', { name: 'AI 对话玩法' }).click()
await page.waitForURL('**/game', { timeout: 15000 })
// 等背景图加载（ImageAcrossFade new Image 加载 + cross-fade）
await page.waitForTimeout(2500)

const result = {}

// 1. 未调用 opening 端点
result.openingCalls = apiCalls.filter((u) => u.includes('/chat/opening'))
result.apiCallsSoFar = apiCalls.slice()

// 2. 无开场白 / 无选项窗口
result.bodyHasOpeningLine = await page.evaluate(() => document.body.innerText.includes('你醒了'))
result.optionWindowCount = await page.locator('[data-testid="option-window"]').count()
result.textareaValue = await page.locator('textarea#inputMessage').inputValue()
result.textareaReadonly = await page.locator('textarea#inputMessage').getAttribute('readonly')

// 3. 背景图 = background_ai.png
result.bgStyle = await page.evaluate(() => {
  const el = document.querySelector('.game-background')
  return el ? getComputedStyle(el).backgroundImage : null
})
result.bgRequests = bgRequests.slice()

await page.screenshot({ path: OUT + '/02-game-entry.png' })

// 4. 首个玩家消息创建会话
await page.locator('textarea#inputMessage').fill('你好呀')
await page.locator('#sendButton').click()
// 等 mock 回复打完（textarea 有内容且回到 input 态）
await page.waitForFunction(
  () => {
    const v = document.querySelector('textarea#inputMessage')?.value ?? ''
    return v.length > 0
  },
  { timeout: 30000 },
)
await page.waitForTimeout(1200)
result.sessionIdInStorage = await page.evaluate(() => localStorage.getItem('gal_session_id'))
result.headerText = await page.evaluate(() =>
  document.querySelector('header')?.innerText.slice(0, 60),
)
result.chatCalls = apiCalls.filter((u) => u.includes('/chat'))
result.replyText = (await page.locator('textarea#inputMessage').inputValue()).slice(0, 80)

// 5. 点 ▼ 推进打字后：选项窗口仍不自动弹出，输入解锁（前置剧情删除的关键验收）
const btn = page.locator('#sendButton')
for (let i = 0; i < 6; i++) {
  const opts = await page.locator('[data-testid="option-window"]').count()
  if (opts > 0) break
  if ((await btn.count()) > 0 && (await btn.isEnabled())) {
    await btn.click()
    await page.waitForTimeout(600)
  } else {
    break
  }
}
result.optionWindowAfterContinue = await page.locator('[data-testid="option-window"]').count()
result.inputEnabledAfterContinue = await page.evaluate(() => {
  const t = document.querySelector('textarea#inputMessage')
  return t ? !t.hasAttribute('readonly') : null
})
await page.screenshot({ path: OUT + '/03-after-first-reply.png' })

// 6. 「行动」按钮仍存在（旧调查玩法可见入口，既有决策）
const actionBtn = page.locator('header button', { hasText: '行动' })
result.actionButtonCount = await actionBtn.count()
if (result.actionButtonCount > 0) {
  await actionBtn.click()
  await page.waitForTimeout(600)
  result.optionWindowManualOpen = await page.locator('[data-testid="option-window"]').count()
  await page.screenshot({ path: OUT + '/04-option-window-manual.png' })
  await page.locator('[data-testid="option-window-dismiss"]').click().catch(() => {})
}

console.log(JSON.stringify(result, null, 2))
await browser.close()
