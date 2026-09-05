// 【PROTOTYPE throwaway】docs/27 可行性探查冒烟：/prototype/world 三变体 + 觉醒演出。
// 收集：截图证据 + HUD 状态（帧率/阶段）+ console 错误。vite dev 5173。
// 时序约定：门面板出现靠 hud 每 250ms 的重渲染触发，等待用 waitForSelector + 点击后等面板卸载。
import { chromium } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const BASE = process.env.GAL_BASE_URL || 'http://localhost:5173'
// 基于脚本位置推导，避免 CWD 不同导致证据错位
const OUT = process.env.GAL_OUT_DIR || fileURLToPath(new URL('../../validation-results/docs27-feasibility/evidence', import.meta.url))
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 768 } })
const errors = []
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(m.text().slice(0, 180))
})
page.on('pageerror', (e) => errors.push(String(e).slice(0, 240)))

const log = []
async function hud() {
  try {
    return await page.evaluate(() => document.querySelector('.hud')?.textContent ?? '(no hud)')
  } catch {
    return '(no hud)'
  }
}
async function waitPanel() {
  try {
    await page.waitForSelector('.gate-panel', { timeout: 400 })
    return true
  } catch {
    return false
  }
}
async function holdD(ms) {
  await page.keyboard.down('d')
  await page.waitForTimeout(ms)
  await page.keyboard.up('d')
}

// —— 变体 A：浮岛横版 ——
await page.goto(BASE + '/prototype/world?variant=A', { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)
await page.screenshot({ path: OUT + '/01-A-起点.png' })
log.push('A 起点: ' + (await hud()))

await page.keyboard.down('d')
await page.keyboard.down('Space')
await page.waitForTimeout(350)
await page.keyboard.up('Space')
await page.waitForTimeout(2600)
await page.keyboard.up('d')
await page.screenshot({ path: OUT + '/02-A-行进.png' })
log.push('A 行进: ' + (await hud()))

// gate1
for (let i = 0; i < 24 && !(await waitPanel()); i++) await holdD(450)
await page.waitForTimeout(500)
await page.screenshot({ path: OUT + '/03-A-gate1.png' })
log.push('A gate1: ' + (await hud()))
await page.getByRole('button', { name: /①/ }).click()
await page.waitForTimeout(700) // 等 gate1 面板卸载

// gate2
for (let i = 0; i < 24 && !(await waitPanel()); i++) await holdD(450)
await page.waitForTimeout(500)
await page.screenshot({ path: OUT + '/04-A-gate2.png' })
log.push('A gate2: ' + (await hud()))
await page.getByRole('button', { name: '原词：永远' }).click()
await page.waitForTimeout(700)

// 三分岔
for (let i = 0; i < 24 && !(await waitPanel()); i++) await holdD(450)
await page.waitForTimeout(500)
await page.screenshot({ path: OUT + '/05-A-三分岔.png' })
log.push('A 三分岔: ' + (await hud()))

// REFUSE：停下不选 → 镜头移交
await page.getByRole('button', { name: /停下不选/ }).click()
await page.waitForTimeout(2600)
await page.screenshot({ path: OUT + '/06-A-REFUSE镜头移交.png' })
log.push('A REFUSE: ' + (await hud()))
await page.getByRole('button', { name: '重开世界' }).click()
await page.waitForTimeout(700)

// RESET：快速推进到分岔（重走全程）
for (let i = 0; i < 70; i++) {
  const h = await hud()
  if (h.includes('phase=fork')) break
  if (await waitPanel()) {
    const btn = page.getByRole('button', { name: /①|原词/ }).first()
    if (await btn.count()) {
      await btn.click()
      await page.waitForTimeout(600)
    }
  }
  await holdD(400)
}
await page.waitForTimeout(400)
if (await waitPanel()) {
  await page.getByRole('button', { name: /回头/ }).click()
  await page.waitForTimeout(1500)
  await page.screenshot({ path: OUT + '/07-A-RESET倒放.png' })
  log.push('A RESET 倒放: ' + (await hud()))
}

// —— 觉醒演出 ——
await page.getByRole('button', { name: '觉醒演出' }).click()
await page.waitForTimeout(600)
await page.screenshot({ path: OUT + '/08-觉醒-演出前.png' })
await page.getByRole('button', { name: '触发觉醒' }).click()
await page.waitForTimeout(1100)
await page.screenshot({ path: OUT + '/09-觉醒-立绘突破.png' })
await page.waitForTimeout(1900)
await page.screenshot({ path: OUT + '/10-觉醒-黑屏虚空.png' })
log.push('觉醒 黑屏: ok')
await page.getByRole('button', { name: '进入她的世界' }).click()
await page.waitForTimeout(300)

// —— 变体 C：记忆长廊 ——
await page.goto(BASE + '/prototype/world?variant=C', { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)
await page.keyboard.down('d')
await page.waitForTimeout(2500)
await page.keyboard.up('d')
await page.screenshot({ path: OUT + '/11-C-长廊.png' })
log.push('C 长廊: ' + (await hud()))

// —— 变体 D：三扇门 ——
await page.goto(BASE + '/prototype/world?variant=D', { waitUntil: 'networkidle' })
await page.waitForTimeout(900)
await page.screenshot({ path: OUT + '/12-D-三扇门.png' })
await page.locator('.door').nth(1).click()
await page.waitForTimeout(300)
await page.screenshot({ path: OUT + '/13-D-选择.png' })
log.push('D 三扇门: ok')

// —— reduced 档：A 起步可玩 ——
await page.goto(BASE + '/prototype/world?variant=A&reduced=1', { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)
await holdD(1500)
await page.screenshot({ path: OUT + '/14-A-reduced.png' })
log.push('A reduced: ' + (await hud()))

writeFileSync(OUT + '/console-errors.txt', errors.length ? errors.join('\n') : '(无 console.error / pageerror)')
writeFileSync(OUT + '/hud-log.txt', log.join('\n'))
console.log('=== 证据已写入 ' + OUT + ' ===')
console.log(log.join('\n'))
console.log('console 错误数: ' + errors.length)
if (errors.length) console.log(errors.join('\n'))
await browser.close()
