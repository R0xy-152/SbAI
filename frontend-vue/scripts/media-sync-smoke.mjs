// 【PROTOTYPE throwaway】验证开场「视频+音乐同时起播」（docs/27 §7.1/§7.2）。
// 挂载真实 TrialSceneSnapshot；检查 <video>/<audio> 是否加载并进入播放、素材是否 200。
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const BASE = process.env.GAL_BASE_URL || 'http://localhost:5173'
const OUT = process.env.GAL_OUT_DIR || fileURLToPath(new URL('../../validation-results/docs27-feasibility/evidence', import.meta.url))
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 180)) })
page.on('pageerror', (e) => errors.push(String(e).slice(0, 220)))

await page.goto(BASE + '/prototype/media', { waitUntil: 'load' })
await page.waitForSelector('video.trial-snapshot__video', { timeout: 15000 })
// 等媒体起播（空转期：视频自动播、音频被自动播放策略拦、已注册首次交互兜底）
await page.waitForTimeout(2600)
const before = await page.evaluate(() => {
  const v = document.querySelector('video.trial-snapshot__video')
  const a = document.querySelector('audio[src*="aira_full"]')
  return { audioPausedBefore: a ? a.paused : null, videoPausedBefore: v ? v.paused : null }
})
// 模拟首次交互（用户点击「开始试玩」等同类型手势）
await page.mouse.click(680, 220)
await page.waitForTimeout(1300)

const r = await page.evaluate(() => {
  const v = document.querySelector('video.trial-snapshot__video')
  const a = document.querySelector('audio[src*="aira_full"]')
  const snap = document.querySelector('.trial-snapshot')
  return {
    videoPresent: !!v,
    videoPaused: v ? v.paused : null,
    videoCurrentTime: v ? +v.currentTime.toFixed(2) : null,
    videoReadyState: v ? v.readyState : null,
    videoDurations: v ? +v.duration.toFixed(2) : null,
    videoSrc: v ? v.currentSrc : null,
    audioPresent: !!a,
    audioPaused: a ? a.paused : null,
    audioCurrentTime: a ? +a.currentTime.toFixed(2) : null,
    audioReadyState: a ? a.readyState : null,
    audioDurations: a ? +a.duration.toFixed(2) : null,
    audioSrc: a ? a.currentSrc : null,
    redactedHidden: snap ? !snap.querySelector('.trial-snapshot__stage') : null,
    dialogue: snap ? snap.querySelector('.trial-snapshot__dialogue p')?.textContent : null,
  }
})
console.log('before(首次交互前):', JSON.stringify(before))
console.log(JSON.stringify(r, null, 2))
await page.screenshot({ path: OUT + '/15-媒体同步-开场.png' })
console.log('console 错误数:', errors.length)
if (errors.length) console.log(errors.join('\n'))
await browser.close()
