import { chromium } from '@playwright/test'
const base = 'http://localhost:5173'
const OUT = '/Users/ming/gal/SbAI/validation-results/docs27-feasibility/evidence'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1366, height: 768 } })
const errs = []
p.on('pageerror', e => errs.push(String(e).slice(0,200)))
await p.goto(base + '/trial', { waitUntil: 'load' })
await p.waitForTimeout(2200)
await p.locator('button', { hasText: '开始试玩' }).first().click()
await p.waitForTimeout(2800)
const s1 = await p.evaluate(() => {
  const v = document.querySelector('video'); const a = document.querySelector('audio')
  return { char: document.querySelector('#character')?.textContent,
           line: document.querySelector('#inputMessage')?.value,
           sendBtn: !!document.querySelector('#sendButton'),
           video: v ? !v.paused : false, audio: a ? !a.paused : false }
})
console.log('1 夜色真美:', JSON.stringify(s1))
await p.screenshot({ path: OUT + '/18-trial-序章对话框-夜色真美.png' })
await p.locator('#sendButton').click()
await p.waitForTimeout(1200)
const s2 = await p.evaluate(() => ({ readonly: document.querySelector('#inputMessage')?.readOnly,
  placeholder: document.querySelector('#inputMessage')?.getAttribute('placeholder') }))
console.log('2 输入态:', JSON.stringify(s2))
await p.locator('#inputMessage').fill('是啊')
await p.locator('#inputMessage').press('Enter')
await p.waitForTimeout(1600)
const s3 = await p.evaluate(() => ({ char: document.querySelector('#character')?.textContent,
  line: document.querySelector('#inputMessage')?.value }))
console.log('3 异常拍:', JSON.stringify(s3))
console.log('pageerrors:', errs.length ? errs.join(' | ') : 'none')
await b.close()
