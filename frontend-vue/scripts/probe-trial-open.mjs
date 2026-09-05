import { chromium } from '@playwright/test'
const base = 'http://localhost:5173'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1366, height: 768 } })
const errs = []
p.on('pageerror', e => errs.push(String(e).slice(0,200)))
await p.goto(base + '/trial', { waitUntil: 'load' })
await p.waitForTimeout(2500)
console.log('finalURL:', p.url())
const s1 = await p.evaluate(() => ({
  trialView: !!document.querySelector('.trial-view'),
  buttons: [...document.querySelectorAll('button')].map(x => x.textContent.trim()).slice(0,6),
  body: document.body.innerText.slice(0, 100).replace(/\s+/g,' '),
}))
console.log('第一步:', JSON.stringify(s1))
const start = p.locator('button', { hasText: '开始试玩' })
if (await start.count()) {
  await start.first().click()
  await p.waitForTimeout(2500)
}
const s2 = await p.evaluate(() => {
  const v = document.querySelector('video.trial-snapshot__video')
  const a = document.querySelector('audio[src*="aira_full"]')
  const dia = document.querySelector('.trial-snapshot__dialogue p')?.textContent ?? null
  return {
    video: v ? !v.paused : false,
    audio: a ? !a.paused : false,
    dialogue: dia,
    phase: document.querySelector('.trial-fixture-badge')?.textContent ?? null,
  }
})
console.log('进入后:', JSON.stringify(s2))
await p.screenshot({ path: 'validation-results/docs27-feasibility/evidence/17-trial-免登录开场.png' })
console.log('pageerrors:', errs.length ? errs.join(' | ') : 'none')
await b.close()
