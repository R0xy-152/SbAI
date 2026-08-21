import { type Page } from '@playwright/test'

// 视觉回归 / E2E 公共助手（docs/13 §26.2 / §26.4）。
// 打字机时序：mock 的 AI 回声逐字回显上下文（很长），不等待其完整打出；
// 确定性 script 行短且文本固定，用 waitTyped 精确比对到完整行。

/** 冻结 CSS 动画/过渡，避免截图中间帧抖动（docs/13 §26.2 风险 2/3）。
 *  docs/15 §9.3：同时注入「特效全关」设置 —— canvas 粒子（星星/流星/场景粒子/
 *  光标特效）不受 CSS 冻结控制，必须经设置关闭才能获得确定性基线；加载演出
 *  关闭保证时序稳定。 */
export async function freezeAnimations(page: Page): Promise<void> {
  await page.addInitScript(() => {
    try {
      localStorage.setItem(
        'gal_settings',
        JSON.stringify({
          textSpeed: 1,
          bgmVolume: 0.6,
          sfxVolume: 0.8,
          mainMenuStarsEnabled: false,
          mainMenuMeteorsEnabled: false,
          globalMouseTrailEnabled: false,
          clickAnimationEnabled: false,
          sceneEffectsEnabled: false,
          loadingTransitionEnabled: false,
          eyeOpenTransitionEnabled: false,
          uiZoom: 1,
        }),
      )
    } catch {
      // 存储不可用时忽略（测试仍可继续，仅特效开关未注入）
    }
  })
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

/** 反复点 #sendButton 直到 #inputMessage 值 === exactText（确定性 script 行）。
 *  docs/16 P6：台词按换行分段后，从玩家发言到目标 script 行之间可能隔着多段
 *  AI 回声（mock 回声内嵌多行上下文）。本助手仅在「当前值非空且不是目标前缀」
 * 时点继续（即跳过回声段）；一旦值成为目标的前缀（目标正在逐字打出）或为空
 *（刚推进、下一段即将打出）就等待，绝不打断目标行。 */
export async function waitTyped(
  page: Page,
  exactText: string,
  timeout = 60_000,
): Promise<void> {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    const v = await page.locator('#inputMessage').inputValue().catch(() => '')
    if (v === exactText) return
    // 仅在「非空且不是目标前缀」时点继续（跳过回声段）；空（刚推进，下一段即将
    // 打出）或目标前缀（目标正在逐字打出）一律等待，绝不跳过目标行。
    const skip = v.length > 0 && !exactText.startsWith(v)
    if (skip) {
      const disabled = await page.locator('#sendButton').isDisabled().catch(() => true)
      if (!disabled) await page.locator('#sendButton').click()
    }
    await page.waitForTimeout(100)
  }
  throw new Error('waitTyped timeout: ' + exactText)
}

/** 等待输入解锁（textarea 非 readonly）；锁定期间在按钮可用时连续点继续快速
 *  跳过多段回声（不等待整段打完，与旧 fixture「开始打字即推进」语义一致）。 */
export async function waitInputUnlocked(page: Page, timeout = 60_000): Promise<void> {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    const unlocked = await page.evaluate(() => {
      const ta = document.querySelector('textarea#inputMessage') as HTMLTextAreaElement | null
      return !!ta && !ta.readOnly
    })
    if (unlocked) return
    // 选项窗口打开 → 点「继续对话」关闭（docs/16 P8：窗口是选项唯一入口，D4 可跳过）
    const win = page.locator('[data-testid="option-window"]')
    if (await win.isVisible().catch(() => false)) {
      await page.locator('[data-testid="option-window-dismiss"]').click()
      await page.waitForTimeout(120)
      continue
    }
    const disabled = await page.locator('#sendButton').isDisabled().catch(() => true)
    if (!disabled) await page.locator('#sendButton').click()
    await page.waitForTimeout(100)
  }
  throw new Error('waitInputUnlocked timeout')
}

/** 打开选项窗口（点顶栏「行动」）；已打开则直接返回。 */
export async function openOptionWindow(page: Page): Promise<void> {
  const win = page.locator('[data-testid="option-window"]')
  if (!(await win.isVisible().catch(() => false))) {
    await page.getByRole('button', { name: '行动', exact: true }).click()
    await win.waitFor({ timeout: 15_000 })
  }
}

/** 打开选项窗口并在其中点击指定选项。 */
export async function clickOption(page: Page, name: string, exact = true): Promise<void> {
  await openOptionWindow(page)
  await page.getByRole('button', { name, exact }).click()
}

/** 有选项则打开选项窗口（无选项时静默跳过）。用于 D3「未解锁选项不可见」断言。 */
export async function openOptionWindowIfAny(page: Page): Promise<void> {
  const act = page.getByRole('button', { name: '行动', exact: true })
  if (await act.isVisible().catch(() => false)) {
    await openOptionWindow(page)
  }
}

/** Title → 开始游戏 → 章节选择 → 序章 → /story 播放器（docs/19 新流程）。
 *  序章为固定剧本：无输入框，点「继续」（#sendButton）逐行推进；
 *  选项经 [data-testid="story-choice-window"] 点选。首次进入有章节卡
 *  （data-testid="chapter-opening"）自动消失（~3.8s / reduce-motion 1.5s）。
 *  返回后即可点「继续」推进第一句台词。 */
export async function startNewGame(page: Page): Promise<void> {
  await page.goto('/')
  const start = page.locator('.title-btn', { hasText: '开始游戏' })
  await start.waitFor()
  await start.click()
  await page.waitForURL('**/chapters')
  const prologue = page.locator('.chapter-card', { hasText: '序章' })
  await prologue.waitFor()
  await prologue.click()
  await page.waitForURL('**/story?story_id=prologue')
  // 章节开场卡自动消失（docs/19 序章标题卡），等它离开舞台
  const opening = page.locator('[data-testid="chapter-opening"]')
  if (await opening.isVisible().catch(() => false)) {
    await opening.waitFor({ state: 'hidden', timeout: 15_000 })
  }
}

/** 故事模式推进：等对话区出现可点「继续」（#sendButton），点击推进一行。
 *  故事模式无输入框（AI 停用），#inputMessage 为只读台词区。 */
export async function storyAdvanceLine(page: Page, timeout = 15_000): Promise<void> {
  const proceed = page.locator('#sendButton')
  await proceed.waitFor({ state: 'visible', timeout })
  await proceed.click()
}

/** 等待并点选故事选项（story-choice-window 内按 label 精确匹配）。 */
export async function chooseStoryOption(page: Page, label: string, timeout = 15_000): Promise<void> {
  const win = page.locator('[data-testid="story-choice-window"]')
  await win.waitFor({ state: 'visible', timeout })
  const opt = win.getByRole('button', { name: label, exact: true })
  await opt.waitFor({ state: 'visible', timeout })
  await opt.click()
}

/** 等待对话区当前台词完整显示指定文本（#inputMessage 为只读台词区，
 *  故事模式逐行替换，无打字机长回声；直接比对输入框值）。 */
export async function waitStoryLine(page: Page, exactText: string, timeout = 20_000): Promise<void> {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    const v = await page.locator('#inputMessage').inputValue().catch(() => '')
    if (v === exactText) return
    // 点击「继续」推进直到目标行出现
    const proceed = page.locator('#sendButton')
    if (await proceed.isVisible().catch(() => false) && !(await proceed.isDisabled().catch(() => true))) {
      await proceed.click()
    }
    await page.waitForTimeout(120)
  }
  throw new Error('waitStoryLine timeout: ' + exactText)
}

/** 循环推进台词直到故事选项窗口出现（返回其可见选项文本列表）。 */
export async function advanceToStoryChoice(
  page: Page,
  timeout = 120_000,
): Promise<string[]> {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    const win = page.locator('[data-testid="story-choice-window"]')
    if (await win.isVisible().catch(() => false)) {
      return win.locator('button').allTextContents()
    }
    const proceed = page.locator('#sendButton')
    if (await proceed.isVisible().catch(() => false) && !(await proceed.isDisabled().catch(() => true))) {
      await proceed.click()
    }
    await page.waitForTimeout(120)
  }
  throw new Error('advanceToStoryChoice timeout')
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

/** 调查桌上的纸（inspect + 自动拓印 → EV01）。docs/16 P7/P8：经选项窗口执行，
 *  成功后弹线索窗口展示获得证据，点「关闭」继续。完成后该选项消失（D3）。 */
export async function inspectPaper(page: Page): Promise<void> {
  await clickOption(page, '桌上的纸')
  await page.locator('[data-testid="clue-window"]').waitFor({ timeout: 30_000 })
  await page.locator('[data-testid="clue-window-close"]').click()
  await waitInputUnlocked(page)
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
      return has('deepseek_main.png') && has('claude_main.png')
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
