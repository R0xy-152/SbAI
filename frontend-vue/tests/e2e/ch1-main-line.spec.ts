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

  // D3：开场只下发「桌上的纸」调查选项；Claude 未登场 → 无对话路由选项，
  // 默认回应者 DeepSeek 也不占路由选项（docs/14 §2.3 / D5）
  await expect(page.getByRole('button', { name: '桌上的纸', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '找 Claude 谈谈' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '找 DeepSeek 谈谈' })).toHaveCount(0)

  // 调查桌上的纸 → EV01（03:17 前置），经选项气泡执行（docs/14 T2）
  await inspectPaper(page)
  // D3：拓印完成后「桌上的纸」选项随热点 completed 消失
  await expect(page.getByRole('button', { name: '桌上的纸', exact: true })).toHaveCount(0)

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
    return has('deepseek_main.png') && has('claude_main.png')
  }, { timeout: 60_000 })

  // 播完 03:17 scripted 序列（确定性文本逐行比对）直到输入解锁
  await waitTyped(page, SYS_0317_WARNING)
  await page.locator('#sendButton').click()
  await waitTyped(page, CLAUDE_0317_OPENING)
  await page.locator('#sendButton').click()
  await waitTyped(page, DS_0317_REACTION)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)

  // D3 + D5：Claude 登场后下发「找 Claude 谈谈」；默认回应者 DeepSeek 不占选项
  await expect(page.getByRole('button', { name: '找 Claude 谈谈' })).toBeVisible()
  await expect(page.getByRole('button', { name: '找 DeepSeek 谈谈' })).toHaveCount(0)
  // T2 其余 3 个热点（docs/14 §2.3）：后端下发 investigate 选项（BEGIN_CHAPTER
  // 已在纸调查时触发，requires claude 的热点随登场解锁）
  for (const label of ['主终端', 'C-02 隔离门', '角色注册表']) {
    await expect(page.getByRole('button', { name: label, exact: true })).toBeVisible()
  }

  // 手动保存 Slot 1
  await manualSaveSlot1(page, 'E2E 主线存档')

  // D5 粘性路由：点「找 Claude 谈谈」→ 下一条消息由 Claude 回应（后端历史权威断言）；
  // 再点同一气泡取消 → 回到公共对话（mock SpeakerSelector 恒选 DeepSeek）
  await page.getByRole('button', { name: '找 Claude 谈谈' }).click()
  track('你好呀')
  await sendPlayerMessage(page, '你好呀')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  const routedSid = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  const assertLastCharacter = async (expected: string) => {
    const res = await page.request.get(
      'http://localhost:8000/api/chat/history?session_id=' + encodeURIComponent(routedSid ?? ''),
    )
    expect(res.ok()).toBeTruthy()
    const hist = await res.json()
    const lastChar = [...hist.messages].reverse().find((m) => m.role === 'character')
    expect(lastChar.character_id).toBe(expected)
  }
  await assertLastCharacter('claude')
  await page.getByRole('button', { name: '找 Claude 谈谈' }).click()
  track('回到公共对话')
  await sendPlayerMessage(page, '回到公共对话')
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  await assertLastCharacter('deepseek')

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

  // 断言恢复（docs/13 §19.1：Load 创建新 Active Session）。
  // docs/15 §8：路由淡入过渡（out-in）使 GameView 挂载晚于 URL 变化，
  // 等待 session 落盘后再断言（此前直接 evaluate 存在竞态）。
  await page.waitForFunction(() => localStorage.getItem('gal_session_id') !== null)
  const newSession = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  expect(newSession).toBeTruthy()
  expect(newSession).not.toBe(oldSession)

  // Claude + DeepSeek 都在场
  await page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll('img'))
    const has = (s: string) =>
      imgs.some((i) => i.src.includes(s) && i.complete && i.naturalWidth > 0)
    return has('deepseek_main.png') && has('claude_main.png')
  }, { timeout: 60_000 })

  // 显示的是存档时的对话（03:17 序列最后一行），而非「继续」回合的回应
  await waitTyped(page, DS_0317_REACTION)

  // 纸条 hotspot 状态恢复为 completed（闸门未重开）：T2 起已完成热点的调查
  // 选项不再下发（D3：气泡条无「桌上的纸」）；Claude 仍在场 → 路由选项恢复。
  // 并用权威 /api/game/state 直接断言恢复后的 hotspot_states
  await expect(page.getByRole('button', { name: '桌上的纸', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '找 Claude 谈谈' })).toBeVisible()
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
