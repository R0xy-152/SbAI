// docs/13 §26.2：6 个关键 snapshot × 2 viewport = 12 张视觉基线。
// 首次生成：npx playwright test tests/visual --update-snapshots
// 之后对比：npm run test:visual
// 2026-08-21（docs/19 序章上线）：本组基线按第一章 /game 旧流程拍摄
//（startNewGame → driveClaudeAppears → 03:17），新流程为「章节选择 → 序章
// 固定剧本」；且基线为 win32 平台生成，macOS 渲染差异无法直接对比。
// 暂整体跳过，待序章视觉基线在目标环境重拍（--update-snapshots）后恢复。
import { test, expect } from '@playwright/test'
import {
  freezeAnimations,
  waitImagesComplete,
  waitTypedStable,
  waitTyped,
  startNewGame,
  driveClaudeAppears,
  manualSaveSlot1,
} from './fixtures'

const SYS_0317_WARNING = '警告：检测到与当前运行记录不一致的内存访问痕迹。'

test.describe.skip('Vue 视觉基线（docs/13 §26.2）', () => {
  test.beforeEach(async ({ page }) => {
    await freezeAnimations(page)
  })

  test('TITLE_EMPTY_SAVE', async ({ page }) => {
    await page.goto('/')
    const cont = page.locator('.title-btn', { hasText: '继续游戏' })
    await cont.waitFor()
    await expect(cont).toBeDisabled()
    await page.waitForTimeout(400)
    await expect(page).toHaveScreenshot('TITLE_EMPTY_SAVE.png')
  })

  test('OPENING_DEEPSEEK_ONLY', async ({ page }) => {
    await page.goto('/')
    await page.locator('.title-btn', { hasText: '开始游戏' }).click()
    await page.waitForURL('**/game')
    await waitTypedStable(page)
    await waitImagesComplete(page)
    await expect(page).toHaveScreenshot('OPENING_DEEPSEEK_ONLY.png')
  })

  test('CLAUDE_APPEARS_TWO_ROLE', async ({ page }) => {
    await startNewGame(page)
    await driveClaudeAppears(page)
    // 03:17 序列第 1 行（SYS，确定性文本）完整打出：两立绘 + 对话稳定
    await waitTyped(page, SYS_0317_WARNING)
    await waitImagesComplete(page)
    await expect(page).toHaveScreenshot('CLAUDE_APPEARS_TWO_ROLE.png')
  })

  test('LONG_DIALOGUE', async ({ page }) => {
    await startNewGame(page)
    await driveClaudeAppears(page)
    // 03:17 scripted 序列的最长行（SYS_0317_WARNING）完整打出
    await waitTyped(page, SYS_0317_WARNING)
    await expect(page).toHaveScreenshot('LONG_DIALOGUE.png')
  })

  test('SAVE_PANEL', async ({ page }) => {
    await startNewGame(page)
    await manualSaveSlot1(page, '视觉回归')
    await page.getByRole('button', { name: '系统菜单' }).click()
    await page.getByRole('button', { name: '保存', exact: true }).click()
    await page.getByText('视觉回归').waitFor({ timeout: 15_000 })
    await expect(page).toHaveScreenshot('SAVE_PANEL.png')
  })

  test('LOAD_PANEL', async ({ page }) => {
    await startNewGame(page)
    await manualSaveSlot1(page, '视觉回归')
    await page.getByRole('button', { name: '系统菜单' }).click()
    await page.getByRole('button', { name: '读取', exact: true }).click()
    await page.getByText('视觉回归').waitFor({ timeout: 15_000 })
    await expect(page).toHaveScreenshot('LOAD_PANEL.png')
  })
})
