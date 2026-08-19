// docs/13 Task 9 Step 7：旧前端（frontend-deprecated，vanilla HTML/CSS/JS）
// 可渲染的 3 场景 × 2 viewport = 6 张对比证据。旧前端无 Title Screen /
// Save-Load 面板——这种缺失本身就是 Vue 优势的证据（result.md 记录，不强行补拍）。
// 证据进 validation-results（CLAUDE.md 约定），截图不进视觉基线目录。
import { test, expect, type Page } from '@playwright/test'
import { freezeAnimations } from './fixtures'

const OLD = 'http://localhost:8000/frontend-deprecated/index.html'

async function waitOpeningDone(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const overlay = document.querySelector('#opening-overlay') as HTMLElement | null
    const sprite = document.querySelector('#character-sprite') as HTMLElement | null
    const text = document.querySelector('#dialogue-text') as HTMLElement | null
    return (
      (!overlay || overlay.hidden) &&
      !!sprite &&
      !sprite.classList.contains('is-hidden') &&
      !!text &&
      text.textContent!.trim().length > 0
    )
  })
}

async function rubPaper(page: Page): Promise<void> {
  // 点「桌上的纸」→ 纸面拓印面板（INSPECT 对纸无 evidence_on_inspect，不弹窗）
  await page.locator('[data-hotspot-id="CH1_NOTE_01"]').click()
  await page.waitForFunction(() => {
    const panel = document.querySelector('#paper-panel') as HTMLElement
    return panel && !panel.hidden
  }, { timeout: 30_000 })

  // 扫动鼠标覆盖画布 → 达到 38% 覆盖率自动提交拓印（PAPER_RUBBING_COMPLETE）
  const box = await page.locator('#rubbing-canvas').boundingBox()
  if (!box) throw new Error('rubbing canvas not visible')
  // 阈值 = 28×15×0.38 ≈ 160 格；蛇形逐行扫动并在达到阈值后立即退出
  await page.mouse.move(box.x + 2, box.y + 2)
  const rows = 24
  for (let row = 0; row < rows; row++) {
    const y = box.y + 2 + ((box.height - 4) * row) / (rows - 1)
    const targetX = row % 2 === 0 ? box.x + box.width - 2 : box.x + 2
    await page.mouse.move(targetX, y, { steps: 24 })
    if ((await page.locator('#rubbing-surface.is-revealed').count()) > 0) break
  }
  await page.waitForFunction(() => {
    const surface = document.querySelector('#rubbing-surface') as HTMLElement
    return surface.classList.contains('is-revealed')
  }, { timeout: 30_000 })
  // 拓印完成弹出证据弹窗（EV01）→ 关闭；纸张面板也收起
  await page.waitForFunction(() => {
    const modal = document.querySelector('#game-modal') as HTMLElement
    return modal && !modal.hidden
  }, { timeout: 30_000 })
  await page.locator('#modal-close').click()
  await page.locator('#paper-close').click()
  await page.waitForFunction(() => {
    const st = document.querySelector('#form-status') as HTMLElement
    return st && st.textContent!.includes('发现了一条重要线索')
  }, { timeout: 30_000 })
}

async function oldSendRaw(page: Page, text: string): Promise<void> {
  await page.locator('#player-message').fill(text)
  await page.locator('#player-message').press('Enter')
}

function shot(page: Page, name: string): Promise<Buffer> {
  return page.screenshot({
    path: '../validation-results/docs13-task9/evidence/old-frontend/' + name + '-' + test.info().project.name + '.png',
  })
}

test.describe('旧前端（vanilla）对比证据', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(OLD)
    await freezeAnimations(page)
  })

  test('OPENING_DEEPSEEK_ONLY', async ({ page }) => {
    await waitOpeningDone(page)
    await page.waitForTimeout(300)
    await shot(page, 'OPENING_DEEPSEEK_ONLY')
  })

  test('CLAUDE_APPEARS_TWO_ROLE', async ({ page }) => {
    await waitOpeningDone(page)
    await rubPaper(page)
    await oldSendRaw(page, '你好')
    await page.waitForFunction(() => {
      const st = document.querySelector('#form-status') as HTMLElement
      return st && st.textContent!.startsWith('已收到角色回应')
    }, { timeout: 60_000 })
    await oldSendRaw(page, '然后呢？')
    // 03:17 序列：Claude 登场行（两立绘 + 对话）
    await expect
      .poll(() => page.locator('#dialogue-text').textContent(), { timeout: 60_000 })
      .toBe('比上一次慢。')
    await page.waitForFunction(() => {
      const sprites = Array.from(document.querySelectorAll('.character-sprite'))
      return sprites.filter((s) => !s.classList.contains('is-hidden')).length >= 2
    })
    await shot(page, 'CLAUDE_APPEARS_TWO_ROLE')
  })

  test('LONG_DIALOGUE', async ({ page }) => {
    await waitOpeningDone(page)
    await rubPaper(page)
    await oldSendRaw(page, '你好')
    await page.waitForFunction(() => {
      const st = document.querySelector('#form-status') as HTMLElement
      return st && st.textContent!.startsWith('已收到角色回应')
    }, { timeout: 60_000 })
    await oldSendRaw(page, '然后呢？')
    // 03:17 序列最长行（SYS_0317_WARNING）显示时截图
    await expect
      .poll(() => page.locator('#dialogue-text').textContent(), { timeout: 60_000 })
      .toBe('警告：检测到与当前运行记录不一致的内存访问痕迹。')
    await shot(page, 'LONG_DIALOGUE')
  })
})
