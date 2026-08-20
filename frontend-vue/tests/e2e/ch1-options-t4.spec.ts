// docs/16 P7/P8（改写自 docs/14 §4 T4）：在 T3（INF01/GPT 登场）之后，经选项
// 推进完整结局链：豆包登场 → 豆包私审 → Claude Recovery 披露 → CT04 → GPT 私审
// → INF03 → Recovery（VERIFY/REPAIR ×5）→ Security Review（自证 ×4）→ 清理抉择
// → Bad End（同意）。选项全部经「选项窗口」操作；D3：未解锁选项窗口内不可见。
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import {
  freezeAnimations,
  waitTypingStarted,
  waitTyped,
  waitInputUnlocked,
  startNewGame,
  driveClaudeAppears,
  sendPlayerMessage,
  openOptionWindow,
  openOptionWindowIfAny,
  clickOption,
} from '../visual/fixtures'

const SYS_0317_WARNING = '警告：检测到与当前运行记录不一致的内存访问痕迹。'
const CLAUDE_0317_OPENING = '比上一次慢。'
const DS_0317_REACTION = '……你、你怎么会在这里？！'

const DISPLAY: Record<string, string> = {
  deepseek: 'DeepSeek',
  claude: 'Claude',
  chatgpt: 'ChatGPT',
  doubao: '豆包',
}

async function chatTurn(page: Page, text: string) {
  await sendPlayerMessage(page, text)
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
}

/** 调查一个热点：窗口点击 → 线索窗口 → 关闭。 */
async function investigateHotspot(page: Page, label: string) {
  await clickOption(page, label)
  await page.locator('[data-testid="clue-window"]').waitFor({ timeout: 30_000 })
  await page.locator('[data-testid="clue-window-close"]').click()
  await waitInputUnlocked(page)
}

test('T4 选项推进完整结局链：Recovery → Security Review → Bad End', async ({ page }) => {
  await freezeAnimations(page)

  // ── T2/T3 已覆盖路径：03:17 → 3 热点 → 证词 → CT01 → Claude 私审 → INF01 ──
  await startNewGame(page)
  await driveClaudeAppears(page)
  await waitTyped(page, SYS_0317_WARNING)
  await page.locator('#sendButton').click()
  await waitTyped(page, CLAUDE_0317_OPENING)
  await page.locator('#sendButton').click()
  await waitTyped(page, DS_0317_REACTION)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)

  for (const label of ['主终端', 'C-02 隔离门', '角色注册表']) {
    await investigateHotspot(page, label)
  }

  await clickOption(page, '找 Claude 谈谈')
  await chatTurn(page, '谁打开的 C-02 门？')
  await chatTurn(page, '你亲眼看到 DeepSeek 了吗？')
  await clickOption(page, '找 Claude 谈谈')

  await clickOption(page, '质疑 Claude 的说辞（信息断层）')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, '为什么说门是 DeepSeek 打开的？你又说没看到她')
  await page.getByText('推理成立。').waitFor({ timeout: 30_000 })
  await waitInputUnlocked(page)

  await clickOption(page, '与 Claude 对质（私审）')
  await page.locator("[data-testid='sub-action-panel']").waitFor()
  await page.getByText('门是DeepSeek打开的。').click()
  await page.getByText('Claude没有看到DeepSeek本人。').click()
  await page.getByRole('button', { name: '提交质询' }).click()
  await page.getByText('私审完成。').waitFor({ timeout: 30_000 })

  await clickOption(page, '质疑当前 DeepSeek 与 03:17 的关系')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, '#03 和 #04 不是同一个实例')
  await page.getByText('推理成立。').waitFor({ timeout: 30_000 })
  await page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll('img'))
    return imgs.some((i) => i.src.includes('chatgpt_main.png') && i.complete && i.naturalWidth > 0)
  }, { timeout: 60_000 })
  await waitInputUnlocked(page)

  // ── 豆包登场：GPT 首个获批回合 → CH01_DOUBAO_ARRIVAL 序列（登场行） ──
  await clickOption(page, '找 ChatGPT 谈谈')
  await sendPlayerMessage(page, '你好')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitTyped(page, '呜……那个，如果有需要我帮忙的地方，请告诉我。')
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await openOptionWindow(page)
  await expect(page.getByRole('button', { name: '找 豆包 谈谈' })).toBeVisible()

  // ── 豆包证词（观察/解释拆分）→ 豆包私审 → EV08 + Claude Recovery 披露 ──
  await clickOption(page, '找 豆包 谈谈')
  await chatTurn(page, 'GPT 什么时候出现的？')
  await openOptionWindow(page)
  await expect(page.getByRole('button', { name: '与 豆包 对质（私审）' })).toBeVisible()
  await page.getByRole('button', { name: '与 豆包 对质（私审）' }).click()
  await page.locator("[data-testid='sub-action-panel']").waitFor()
  await page.getByText('她看到屏幕上出现了 GPT 相关文字。').click()
  await page.getByRole('button', { name: '提交质询' }).click()
  await page.getByText('私审完成。').waitFor({ timeout: 30_000 })
  await openOptionWindowIfAny(page)
  await expect(page.getByRole('button', { name: '与 豆包 对质（私审）' })).toHaveCount(0)

  // ── Claude Recovery 披露（CL_CLAUDE_05 → EV07 → EV11 自动补齐） ──
  await clickOption(page, '找 Claude 谈谈')
  await chatTurn(page, '你访问过 recovery 接口吗？')

  // ── CT04 → GPT 私审 → EV09 ──
  await clickOption(page, '质疑 GPT 的摘要（关键遗漏）')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, 'GPT 的摘要遗漏了 V03 的旧会话')
  await page.getByText('推理成立。').waitFor({ timeout: 30_000 })
  await waitInputUnlocked(page)

  await clickOption(page, '与 ChatGPT 对质（私审）')
  await page.locator("[data-testid='sub-action-panel']").waitFor()
  await page.getByRole('button', { name: '提交质询' }).click()
  await page.getByText('私审完成。').waitFor({ timeout: 30_000 })

  // ── INF03 → recovery_required ──
  await clickOption(page, '质疑 V03 与当前玩家的关系')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, 'V03 和 V04 是同一个玩家')
  await page.getByText('推理成立。').waitFor({ timeout: 30_000 })
  await waitInputUnlocked(page)
  await openOptionWindow(page)
  await expect(page.getByRole('button', { name: '进入 Recovery 抉择' })).toBeVisible()

  // ── Recovery：VERIFY → REPAIR × 5 个关键节点（D3：REPAIR 须先 VERIFY） ──
  await page.getByRole('button', { name: '进入 Recovery 抉择' }).click()
  await page.getByText('已进入 Recovery。').waitFor({ timeout: 30_000 })
  for (const node of ['CORE', 'WORLD', 'MEMORY', 'CHARACTER', 'AUTH']) {
    await openOptionWindow(page)
    const verify = page.getByRole('button', { name: `Claude 校验 ${node}`, exact: true })
    const repair = page.getByRole('button', { name: `Player 修复 ${node}`, exact: true })
    await expect(verify).toBeVisible()
    await expect(repair).toHaveCount(0)  // 未 VERIFY 不可修复（D3）
    await verify.click()
    await page.getByText('Recovery 操作已应用。').waitFor({ timeout: 30_000 })
    await openOptionWindow(page)
    await expect(repair).toBeVisible()
    await repair.click()
    await page.getByText('Recovery 操作已应用。').waitFor({ timeout: 30_000 })
    await openOptionWindowIfAny(page)
    await expect(verify).toHaveCount(0)  // 已 RECOVERED，校验选项消失
  }

  // ── Security Review：自证按固定顺序（D3：只给下一位） ──
  await openOptionWindow(page)
  await expect(page.getByRole('button', { name: '进入 Security Review' })).toBeVisible()
  await page.getByRole('button', { name: '进入 Security Review' }).click()
  await page.getByText('Security Review 开始。').waitFor({ timeout: 30_000 })
  for (const cid of ['deepseek', 'claude', 'doubao', 'chatgpt']) {
    await openOptionWindow(page)
    const btn = page.getByRole('button', { name: `听取 ${DISPLAY[cid]} 的自证` })
    await expect(btn).toBeVisible()
    await btn.click()
    await waitTypingStarted(page)
    await page.locator('#sendButton').click()  // 播完自证台词
    await waitInputUnlocked(page)
    await openOptionWindowIfAny(page)
    await expect(btn).toHaveCount(0)
  }

  // ── 清理抉择（holder=player）：删除×3 → 确认保留 → Bad End（同意） ──
  for (const cid of ['deepseek', 'claude', 'doubao']) {
    await openOptionWindow(page)
    const del = page.getByRole('button', { name: `删除 ${DISPLAY[cid]}`, exact: true })
    await expect(del).toBeVisible()
    await del.click()
    await page.getByText(`已删除 ${DISPLAY[cid]}。`).waitFor({ timeout: 30_000 })
    await openOptionWindowIfAny(page)
    await expect(del).toHaveCount(0)
  }
  await openOptionWindow(page)
  await expect(page.getByRole('button', { name: '保留 ChatGPT 并确认清理' })).toBeVisible()
  await page.getByRole('button', { name: '保留 ChatGPT 并确认清理' }).click()
  await page.getByText('清理完成（Bad End：同意）。').waitFor({ timeout: 30_000 })

  // ── 权威断言：Bad End 状态（场景 BAD_END_CHAT，仅剩 ChatGPT） ──
  const sid = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  const stateRes = await page.request.get(
    'http://localhost:8000/api/game/state?session_id=' + encodeURIComponent(sid ?? ''),
  )
  expect(stateRes.ok()).toBeTruthy()
  const stateJson = await stateRes.json()
  expect(stateJson.scene_id).toBe('BAD_END_CHAT')
  expect(stateJson.available_characters).toEqual(['chatgpt'])
})
