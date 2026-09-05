// 【PROTOTYPE throwaway】验证「异常冻结帧喂四片玻璃」：直播视频 → 触发碎裂 → 四片同为一张冻结帧。
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

await page.goto(BASE + '/prototype/shatter', { waitUntil: 'load' })
await page.waitForSelector('video.trial-snapshot__video', { timeout: 15000 })
await page.waitForTimeout(3200) // 直播视频阶段：捕获若干帧到 mediaFrame
const live = await page.evaluate(() => {
  const v = document.querySelector('video.trial-snapshot__video')
  return { videoPlayed: v ? !v.paused && v.currentTime > 0 : false, t: v ? +v.currentTime.toFixed(1) : null }
})

// 触发异常 → 碎裂
await page.getByRole('button', { name: /触发异常/ }).click()
await page.waitForTimeout(1200)

const r = await page.evaluate(() => {
  const videos = document.querySelectorAll('.shatter-puzzle video')
  const pieces = document.querySelectorAll('.shatter-puzzle .shatter-piece')
  const imgs = [...document.querySelectorAll('.shatter-puzzle .shatter-piece img.trial-snapshot__video')]
  const srcs = imgs.map((i) => (i.getAttribute('src') || '').slice(0, 40))
  const unique = new Set(srcs)
  const framesPresent = document.querySelectorAll('.shatter-puzzle .shatter-target img.trial-snapshot__video').length
  return {
    liveVideosInShatter: videos.length,
    pieceCount: pieces.length,
    frozenImgsPerPiece: imgs.length,
    uniqueSrcCount: unique.size,
    firstSrcSample: srcs[0] ?? null,
    targetFrozenImg: framesPresent,
  }
})
console.log('live阶段:', JSON.stringify(live))
console.log('碎裂阶段:', JSON.stringify(r, null, 2))
await page.screenshot({ path: OUT + '/16-冻结帧-碎裂.png' })
console.log('console 错误数:', errors.length)
if (errors.length) console.log(errors.join('\n'))
await browser.close()
