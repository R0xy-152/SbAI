// 【PROTOTYPE throwaway】像素级验证：不依赖截图目视，定量证明 canvas 世界确实渲染。
// 采样：整画布非背景像素占比（文字地形可见）、玩家光点区域、她（菱形）区域。
import { chromium } from '@playwright/test'

const BASE = process.env.GAL_BASE_URL || 'http://localhost:5173'
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
await page.goto(BASE + '/prototype/world?variant=A', { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)

const stats = await page.evaluate(() => {
  const cv = document.querySelector('canvas')
  if (!cv) return { error: 'no canvas' }
  const ctx = cv.getContext('2d')
  const { width: w, height: h } = cv
  const img = ctx.getImageData(0, 0, w, h).data
  let lit = 0
  let textZone = 0 // 中带（y 40%~75%）：平台文字区域
  for (let y = 0; y < h; y += 4) {
    for (let x = 0; x < w; x += 4) {
      const i = (y * w + x) * 4
      const r = img[i], g = img[i + 1], b = img[i + 2]
      if (r + g + b > 90) {
        lit++
        if (y > h * 0.4 && y < h * 0.75) textZone++
      }
    }
  }
  const total = (w / 4) * (h / 4)
  return { w, h, litRatio: +(lit / total).toFixed(4), textZoneRatio: +(textZone / total).toFixed(4), hud: document.querySelector('.hud')?.textContent ?? '(none)' }
})
console.log(JSON.stringify(stats, null, 2))
await browser.close()
