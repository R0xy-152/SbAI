// docs/13 §26.4：第一章主线最低 E2E。
// Title → New Game → Opening → Player input → Character response →
// 调查纸(EV01) → 普通回合×2 确定性 Gate → 03:17 自动发生 → Claude 出现 →
// 手动保存 Slot 1 → 继续改变状态 → 返回标题 → Load Slot 1 → 断言恢复。
// D6：测试内所有玩家消息记录在 sent 中并断言不含 03:17 token（走轮数兜底 Gate）。
// 注：mock 的 AI 回声逐字回显上下文（很长），AI 回合只等「开始打字」即推进；
// 确定性 script 行短且文本固定，用 waitTyped 精确比对。
import { test, expect } from '@playwright/test'
import {
  freezeAnimations,
  waitTypingStarted,
  waitTyped,
  waitInputUnlocked,
  startNewGame,
  inspectPaper,
  sendPlayerMessage,
  manualSaveSlot1,
} from '../visual/fixtures'

const SYS_0317_WARNING = '警告：检测到与当前运行记录不一致的内存访问痕迹。'
const CLAUDE_0317_OPENING = '比上一次慢。'
const DS_0317_REACTION = '……你、你怎么会在这里？！'

test('第一章主线可运行（docs/13 §7.2 验收链路）', async ({ page }) => {
  await freezeAnimations(page)
  const sent: string[] = []
  const track = (m: string) => {
    if (/(03:17|0317|三点十七)/.test(m)) throw new Error('03:17 token forbidden')
    sent.push(m)
  }

  // Title → New Game → Opening 完整打出
  await startNewGame(page)
  const oldSession = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  expect(oldSession).toBeTruthy()

  // Player input → Character response（第一轮普通对话）
  track('你好')
  await sendPlayerMessage(page, '你好')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)

  // 调查桌上的纸 → EV01（03:17 前置）
  await inspectPaper(page)

  // 确定性 Gate：普通回合 ×2 → counter=2 → 03:17 自动发生
  track('你好')
  await sendPlayerMessage(page, '你好')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  track('然后呢？')
  await sendPlayerMessage(page, '然后呢？')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click() // 序列第 1 行（SYS）开始

  // Claude 出现：两个立绘（§26.4「Claude appears」断言）
  await page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll('img'))
    const has = (s: string) =>
      imgs.some((i) => i.src.includes(s) && i.complete && i.naturalWidth > 0)
    return has('deepseek_main.png') && has('claude-main.png')
  }, { timeout: 60_000 })

  // 播完 03:17 scripted 序列（确定性文本逐行比对）直到输入解锁
  await waitTyped(page, SYS_0317_WARNING)
  await page.locator('#sendButton').click()
  await waitTyped(page, CLAUDE_0317_OPENING)
  await page.locator('#sendButton').click()
  await waitTyped(page, DS_0317_REACTION)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)

  // 手动保存 Slot 1
  await manualSaveSlot1(page, 'E2E 主线存档')

  // 继续游戏改变状态（存档之后的新回合）
  track('继续')
  await sendPlayerMessage(page, '继续')
  const continuedText = await waitTypingStarted(page)
  expect(continuedText.length).toBeGreaterThan(0)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)

  // 返回标题 → 读取存档 → Load Slot 1（菜单打开后页面上有两个「返回标题」
  // 按钮：顶栏 + 系统菜单内，用菜单内的 .sys-menu-btn 精确定位）
  await page.getByRole('button', { name: '系统菜单' }).click()
  await page.locator('.sys-menu-btn', { hasText: '返回标题' }).click()
  await page.waitForURL('**/')
  await page.locator('.title-btn', { hasText: '读取存档' }).click()
  await page.waitForURL('**/load')
  await page.locator('button').filter({ hasText: '存档位 1' }).first().click()
  await page.waitForURL('**/game')

  // 断言恢复（docs/13 §19.1：Load 创建新 Active Session）
  const newSession = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  expect(newSession).toBeTruthy()
  expect(newSession).not.toBe(oldSession)

  // Claude + DeepSeek 都在场
  await page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll('img'))
    const has = (s: string) =>
      imgs.some((i) => i.src.includes(s) && i.complete && i.naturalWidth > 0)
    return has('deepseek_main.png') && has('claude-main.png')
  }, { timeout: 60_000 })

  // 显示的是存档时的对话（03:17 序列最后一行），而非「继续」回合的回应
  await waitTyped(page, DS_0317_REACTION)

  // 纸条 hotspot 状态恢复为 completed（闸门未重开）：按钮仍在（completed 热点
  // 可复查，docs/12 §41），再点一次返回 ALREADY_COMPLETED 路径；并用权威
  // /api/game/state 直接断言恢复后的 hotspot_states
  await page.getByRole('button', { name: '调查桌上的纸' }).click()
  await page.getByText('纸面拓印完成').waitFor({ timeout: 30_000 })
  const restoredSid = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  const stateRes = await page.request.get(
    'http://localhost:8000/api/game/state?session_id=' + encodeURIComponent(restoredSid ?? ''),
  )
  expect(stateRes.ok()).toBeTruthy()
  const stateJson = await stateRes.json()
  expect(stateJson.hotspots['CH1_NOTE_01']).toBe('completed')

  // 全部玩家消息不含 03:17 token：走的是确定性轮数兜底 Gate
  expect(sent.length).toBeGreaterThan(0)
})
