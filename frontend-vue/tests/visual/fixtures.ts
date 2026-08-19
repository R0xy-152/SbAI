import { type Page } from '@playwright/test'

// 视觉回归 / E2E 公共助手（docs/13 §26.2 / §26.4）。
// 打字机时序：mock 的 AI 回声逐字回显上下文（很长），不等待其完整打出；
// 确定性 script 行短且文本固定，用 waitTyped 精确比对到完整行。

/** 冻结 CSS 动画/过渡，避免截图中间帧抖动（docs/13 §26.2 风险 2/3）。 */
export async function freezeAnimations(page: Page): Promise<void> {
  await page.addStyleTag({
    content:
      '*,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;transition-duration:0s!important;transition-delay:0s!important;}',
  })
}

/** 全部 <img> 加载完成（立绘截图前置条件）。 */
export async function waitImagesComplete(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const images = Array.from(document.images)
    return images.length > 0 && images.every((i) => i.complete && i.naturalWidth > 0)
  })
}

/** 等待 #inputMessage 打字机打出非空且稳定的文本，返回最终文本。 */
export async function waitTypedStable(page: Page, timeout = 60_000): Promise<string> {
  const deadline = Date.now() + timeout
  let last = ''
  while (Date.now() < deadline) {
    const v = await page.locator('#inputMessage').inputValue().catch(() => '')
    if (v.length > 0 && v === last) return v
    last = v
    await page.waitForTimeout(400)
  }
  throw new Error('typing never stabilized')
}

/** 等待 #inputMessage 开始打字（AI 回声很长，不等待完整打出），返回当前文本。 */
export async function waitTypingStarted(page: Page, timeout = 60_000): Promise<string> {
  await page.waitForFunction(() => {
    const ta = document.querySelector<HTMLTextAreaElement>('#inputMessage')
    return !!ta && ta.value.length > 0
  }, { timeout })
  return page.locator('#inputMessage').inputValue()
}

/** 等待 #inputMessage 打出精确文本（确定性 script 行）。 */
export async function waitTyped(
  page: Page,
  exactText: string,
  timeout = 60_000,
): Promise<void> {
  await page.waitForFunction(
    (t) => {
      const ta = document.querySelector<HTMLTextAreaElement>('#inputMessage')
      return ta !== null && ta.value === t
    },
    exactText,
    { timeout },
  )
}

/** 等待输入解锁（textarea 非 readonly）。 */
export async function waitInputUnlocked(page: Page): Promise<void> {
  await page.waitForFunction(() => {
    const ta = document.querySelector<HTMLTextAreaElement>('#inputMessage')
    return !!ta && !ta.readOnly
  })
}

/** Title → 开始游戏 → opening 完整打出 → 推进解锁输入。 */
export async function startNewGame(page: Page): Promise<void> {
  await page.goto('/')
  const start = page.locator('.title-btn', { hasText: '开始游戏' })
  await start.waitFor()
  await start.click()
  await page.waitForURL('**/game')
  await waitTypedStable(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
}

/** 输入一句话并回车（需输入已解锁）。 */
export async function sendPlayerMessage(page: Page, text: string): Promise<void> {
  const ta = page.locator('#inputMessage')
  await ta.click()
  await ta.fill(text)
  await ta.press('Enter')
}

/** 一轮普通对话：发送 → 开始打字即推进（跳过漫长的 AI 回声）→ 解锁输入。 */
export async function chatRound(page: Page, text: string): Promise<void> {
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, text)
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
}

/** 调查桌上的纸（inspect + 自动拓印 → EV01）。完成后按钮仍在（后端
 * available_hotspots 保留已完成热点供复查，docs/12 §41），以拓印消息为准。 */
export async function inspectPaper(page: Page): Promise<void> {
  await page.getByRole('button', { name: '调查桌上的纸' }).click()
  await page.getByText('纸面拓印完成').waitFor({ timeout: 30_000 })
}

/** 确定性 Gate 驱动 Claude 出现（D6：任何消息不得含 03:17 字样）。 */
export async function driveClaudeAppears(
  page: Page,
  messages: string[] = ['你好', '然后呢？'],
): Promise<void> {
  for (const m of messages) {
    if (/(03:17|0317|三点十七)/.test(m)) throw new Error('03:17 token forbidden')
  }
  await inspectPaper(page)
  await chatRound(page, messages[0])
  // 触发回合：回应开始打字即推进 → 03:17 scripted 序列第 1 行（SYS）开始
  await sendPlayerMessage(page, messages[1])
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  // 两立绘（deepseek + claude）加载完成
  await page.waitForFunction(
    () => {
      const imgs = Array.from(document.querySelectorAll<HTMLImageElement>('img'))
      const has = (s: string) =>
        imgs.some((i) => i.src.includes(s) && i.complete && i.naturalWidth > 0)
      return has('deepseek_main.png') && has('claude-main.png')
    },
    { timeout: 60_000 },
  )
}

/** 系统菜单 → 手动保存到 slot1 → 关闭面板。 */
export async function manualSaveSlot1(page: Page, title = '视觉回归存档'): Promise<void> {
  await page.getByRole('button', { name: '系统菜单' }).click()
  await page.getByRole('button', { name: '保存', exact: true }).click()
  const input = page.locator('input[placeholder="存档标题（可选）"]').first()
  await input.fill(title)
  await page.getByRole('button', { name: '保存', exact: true }).first().click()
  await page.getByText('已保存到存档位 1').waitFor({ timeout: 30_000 })
  await page.getByRole('button', { name: '关闭' }).click()
}
