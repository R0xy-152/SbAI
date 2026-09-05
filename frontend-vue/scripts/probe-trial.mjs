import { chromium } from '@playwright/test'
const base = 'http://localhost:5173'
const b = await chromium.launch()
const p = await b.newPage()
const errs = []
p.on('pageerror', e => errs.push(String(e).slice(0,150)))
await p.goto(base + '/trial', { waitUntil: 'load' })
await p.waitForTimeout(2000)
console.log('finalURL:', p.url())
console.log('hasOpeningVideo:', await p.evaluate(() => !!document.querySelector('video.trial-snapshot__video')))
console.log('pageerrors:', errs.length ? errs.join(' | ') : 'none')
await b.close()
