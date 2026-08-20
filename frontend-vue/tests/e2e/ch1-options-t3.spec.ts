// docs/16 P7/P8（改写自 docs/14 §4 T3）：选项推进 03:17 → 调查 3 热点 →
// 出示证据（小面板）→ 取证词（chat_routing）→ CT01（引导提示 + 一次性推理）
// → Claude 私审（小面板）→ INF01 → GPT 登场。选项全部经「选项窗口」操作，
// D3：未解锁选项窗口内不可见。
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

/** 推进演出序列直到输入解锁（waitInputUnlocked 已含窗口自动关闭）。 */
async function advanceUntilUnlocked(page: Page) {
  await waitInputUnlocked(page)
}

/** 调查一个热点：窗口点击 → 线索窗口 → 关闭（热点随完成从窗口消失）。 */
async function investigateHotspot(page: Page, label: string) {
  await clickOption(page, label)
  await page.locator('[data-testid="clue-window"]').waitFor({ timeout: 30_000 })
  await page.locator('[data-testid="clue-window-close"]').click()
  await waitInputUnlocked(page)
  await openOptionWindowIfAny(page)
  await expect(page.getByRole('button', { name: label, exact: true })).toHaveCount(0)
}

test('T3 选项推进：调查 → 出示 → CT01 → Claude 私审 → INF01', async ({ page }) => {
  await freezeAnimations(page)

  // ── 03:17（T2 已覆盖路径，此处复用）──
  await startNewGame(page)
  await driveClaudeAppears(page)
  await waitTyped(page, SYS_0317_WARNING)
  await page.locator('#sendButton').click()
  await waitTyped(page, CLAUDE_0317_OPENING)
  await page.locator('#sendButton').click()
  await waitTyped(page, DS_0317_REACTION)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)

  // D3：出示证据尚未解锁（FIRST_IMPOSSIBLE_EVENT_RESOLVED 未触发）
  await openOptionWindowIfAny(page)
  await expect(page.getByRole('button', { name: '出示证据' })).toHaveCount(0)

  // ── 调查 3 个热点（主终端先：EV02 触发 RESOLVE_IMPOSSIBLE_EVENT）──
  for (const label of ['主终端', 'C-02 隔离门', '角色注册表']) {
    await investigateHotspot(page, label)
  }

  // ── 出示证据：小面板选择「压痕纸条」× Claude ──
  await clickOption(page, '出示证据')
  await page.locator("[data-testid='sub-action-panel']").waitFor()
  await page.getByText('压痕纸条', { exact: true }).click()
  await page.getByText('Claude', { exact: true }).click()
  await page.getByRole('button', { name: '出示', exact: true }).click()
  await page.getByText('已出示证据。').waitFor({ timeout: 30_000 })
  const sid = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  const evRes = await page.request.get(
    'http://localhost:8000/api/game/evidence?session_id=' + encodeURIComponent(sid ?? ''),
  )
  expect(evRes.ok()).toBeTruthy()
  const evJson = await evRes.json()
  const ev01 = evJson.find((e: { evidence_id: string }) => e.evidence_id === 'EV01_NOTE_V03')
  expect(ev01.presented_to).toContain('claude')

  // D3：证词不足时无 CT01 选项
  await openOptionWindowIfAny(page)
  await expect(page.getByRole('button', { name: '质疑 Claude 的说辞（信息断层）' })).toHaveCount(0)

  // ── 路由 Claude 取两条公开证词（确定性 inquiry 路径）──
  await clickOption(page, '找 Claude 谈谈')
  await sendPlayerMessage(page, '谁打开的 C-02 门？')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, '你亲眼看到 DeepSeek 了吗？')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await clickOption(page, '找 Claude 谈谈')  // 取消路由

  // ── CT01：引导提示 → 一次性推理模式提交 ──
  await openOptionWindow(page)
  const ct01Btn = page.getByRole('button', { name: '质疑 Claude 的说辞（信息断层）' })
  await expect(ct01Btn).toBeVisible()
  await ct01Btn.click()
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()  // 播完系统提示行
  await waitInputUnlocked(page)
  await expect(page.getByText('推理模式：下一条输入将作为推理提交。')).toBeVisible()
  await sendPlayerMessage(page, '为什么说门是 DeepSeek 打开的？你又说没看到她')
  await page.getByText('推理成立。').waitFor({ timeout: 30_000 })
  await advanceUntilUnlocked(page)

  // D3：CT01 选项消失；Claude 私审选项出现
  await openOptionWindowIfAny(page)
  await expect(ct01Btn).toHaveCount(0)
  await expect(page.getByRole('button', { name: '与 Claude 对质（私审）' })).toBeVisible()

  // ── Claude 私审：勾选两条证词 → UNLOCKED → EV05 → INF01 解锁 ──
  await page.getByRole('button', { name: '与 Claude 对质（私审）' }).click()
  await page.locator("[data-testid='sub-action-panel']").waitFor()
  await page.getByText('门是DeepSeek打开的。').click()
  await page.getByText('Claude没有看到DeepSeek本人。').click()
  await page.getByRole('button', { name: '提交质询' }).click()
  await page.getByText('私审完成。').waitFor({ timeout: 30_000 })
  await openOptionWindowIfAny(page)
  await expect(page.getByRole('button', { name: '与 Claude 对质（私审）' })).toHaveCount(0)

  // ── INF01：提示 → 推理 → GPT 登场 ──
  await openOptionWindow(page)
  const inf01Btn = page.getByRole('button', { name: '质疑当前 DeepSeek 与 03:17 的关系' })
  await expect(inf01Btn).toBeVisible()
  await inf01Btn.click()
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, '#03 和 #04 不是同一个实例')
  await page.getByText('推理成立。').waitFor({ timeout: 30_000 })
  await page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll('img'))
    return imgs.some((i) => i.src.includes('chatgpt_main.png') && i.complete && i.naturalWidth > 0)
  }, { timeout: 60_000 })
  await advanceUntilUnlocked(page)

  // D3：INF01 选项消失；GPT 路由出现；CT04（EV11 未齐）不出现
  await openOptionWindowIfAny(page)
  await expect(inf01Btn).toHaveCount(0)
  await expect(page.getByRole('button', { name: '找 ChatGPT 谈谈' })).toBeVisible()
  await expect(page.getByRole('button', { name: '质疑 GPT 的摘要（关键遗漏）' })).toHaveCount(0)
})
