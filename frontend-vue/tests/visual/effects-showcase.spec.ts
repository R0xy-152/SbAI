// docs/15 §9.3：特效全开的展示截图（人工 + 视觉模型复核证据）。
// 不调用 freezeAnimations、不做 toHaveScreenshot 断言 —— canvas 动画不可确定性
// 冻结，截图只作为 validation-results 复核证据，不进视觉基线目录。
import { test, expect, type Page, type TestInfo } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { waitTypedStable, waitImagesComplete, waitInputUnlocked } from './fixtures'

/** 统计 canvas 上非透明像素数（粒子确实在绘制，docs/15 §9.3 机器证据）。 */
async function canvasPaintedPixels(page: Page, selector: string): Promise<number> {
  return page.evaluate((sel) => {
    const canvas = document.querySelector<HTMLCanvasElement>(sel)
    if (!canvas) return -1
    const ctx = canvas.getContext('2d')
    if (!ctx) return -2
    const { width, height } = canvas
    if (width === 0 || height === 0) return 0
    const data = ctx.getImageData(0, 0, width, height).data
    let painted = 0
    for (let i = 3; i < data.length; i += 4) {
      if (data[i]! > 0) painted++
    }
    return painted
  }, selector)
}

const OUT_DIR = join(process.cwd(), '..', 'validation-results', 'docs15', 'showcase')

async function save(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  mkdirSync(OUT_DIR, { recursive: true })
  const file = join(OUT_DIR, `${testInfo.project.name}-${name}`)
  await page.screenshot({ path: file })
}

test('特效展示：首页（流星星空+立绘+菜单）与加载演出', async ({ page }, testInfo) => {
  // 默认设置 = 特效全开（localStorage 无注入）
  await page.goto('/')
  await page.waitForTimeout(900) // 让星星/流星/立绘绘制
  // 机器证据：标题页星星 canvas 确实在绘制（非透明像素 > 0）
  const starPixels = await canvasPaintedPixels(page, '#stars-canvas')
  expect(starPixels).toBeGreaterThan(0)
  await save(page, testInfo, 'TITLE_EFFECTS_ON.png')

  // hover 菜单项：回弹 + 辉光
  const start = page.locator('.title-btn', { hasText: '开始游戏' })
  await start.hover()
  await page.waitForTimeout(400)
  await save(page, testInfo, 'TITLE_HOVER.png')

  // 开始游戏 → 捕获 LoadingTransition（猫爪遮罩 + 进度圈）
  await start.click()
  await page.waitForURL('**/game')
  await page.waitForTimeout(1100)
  await save(page, testInfo, 'GAME_LOADING_TRANSITION.png')
})

test('特效展示：游戏内星空粒子（binding_room → StarField）', async ({ page }, testInfo) => {
  await page.goto('/')
  const start = page.locator('.title-btn', { hasText: '开始游戏' })
  await start.waitFor()
  await start.click()
  await page.waitForURL('**/game')
  await waitTypedStable(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page) // 自动关闭选项窗口（docs/16 P8）
  await waitImagesComplete(page)
  await page.waitForTimeout(700) // 让星空粒子绘制几帧
  // 机器证据：游戏内星空粒子 canvas（StarField）确实在绘制
  const fieldPixels = await canvasPaintedPixels(page, 'canvas.starfield-canvas')
  expect(fieldPixels).toBeGreaterThan(0)
  await save(page, testInfo, 'GAME_STARFIELD.png')
})
