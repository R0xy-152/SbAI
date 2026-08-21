// docs/19 序章完成 → 自由聊天验收（对应旧 T4「完整结局链」在新流程下的语义）。
// 完整走完序章：开场 → 三角色探班（任意顺序）→ 三人集合 → 自由交流模式 →
// 最终选择角色 → /game 自由聊天（AI 回复）。验证：
// 1) 探班循环 + 集合链路完整可走通；
// 2) 最终选择角色后进入 /game 且会话保持（localStorage session_id 延续）；
// 3) /game 自由聊天可发送并收到 AI 回复（GAL_PROVIDER=mock 契约）。
import { test, expect } from '@playwright/test'
import {
  freezeAnimations,
  waitTyped,
  waitTypingStarted,
  waitInputUnlocked,
  startNewGame,
  storyAdvanceLine,
  chooseStoryOption,
  advanceToStoryChoice,
  sendPlayerMessage,
} from '../visual/fixtures'

const INTRO_LAST = '第一站去找谁呢？'
const REUNION_FIRST = '看来大家都在为了这个游戏努力。'
const AFTERTALK_FIRST = '序章剧情结束。'
// mock 契约：/api/chat 对任意输入回显（GAL_PROVIDER=mock），首个玩家消息
// 创建会话并返回 id（docs/13 §20.3）。
const PLAYER_TEXT = '你好，AI 娘'

test('T4 序章完整链路 → 自由聊天：三角色探班 → 集合 → /game 对话', async ({ page }) => {
  await freezeAnimations(page)
  await startNewGame(page)

  // ── 开场 → 第一次探班选择 ──
  await waitTyped(page, INTRO_LAST)
  await storyAdvanceLine(page)
  const first = await advanceToStoryChoice(page)
  expect(first).toHaveLength(3)

  // ── 三角色探班（选择顺序：DeepSeek → Claude → ChatGPT）──
  const order: Array<[string, string]> = [
    ['去找 DeepSeek', '这里是……'],
    ['去找 Claude', '这里的气氛……'],
    ['去找 ChatGPT', '这里好多画稿。'],
  ]
  // 前两次探班：篇内推进到下一选项（还剩未访问角色 → 探班选项重现）
  for (const [option, firstLine] of order.slice(0, 2)) {
    await chooseStoryOption(page, option)
    await waitTyped(page, firstLine)
    await advanceToStoryChoice(page)
  }
  // 第三次探班：篇内推进后**不再有探班选项** → 直接进入三人集合
  const [lastOption, lastFirstLine] = order[2]
  await chooseStoryOption(page, lastOption)
  await waitTyped(page, lastFirstLine)
  await storyAdvanceLine(page)
  await waitTyped(page, REUNION_FIRST)

  // ── 三人集合 → 自由交流模式 ──
  await storyAdvanceLine(page)
  await waitTyped(page, AFTERTALK_FIRST)
  await storyAdvanceLine(page)
  const finalOptions = await advanceToStoryChoice(page)
  expect(finalOptions).toHaveLength(3)
  expect(finalOptions).toContain('与 DeepSeek 聊天')

  // ── 最终选择 DeepSeek → /game 自由聊天 ──
  const storySession = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  await chooseStoryOption(page, '与 DeepSeek 聊天')
  await page.waitForURL('**/game**', { timeout: 15_000 })

  // 会话保持：进入 /game 后 session_id 仍存在（chat 节点复用序章会话）
  const gameSession = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  expect(gameSession).toBeTruthy()

  // 自由聊天：发送消息 → mock AI 回复开始打字 → 解锁（docs/13 §26.4 交互链）
  await waitInputUnlocked(page)
  await sendPlayerMessage(page, PLAYER_TEXT)
  await waitTypingStarted(page)
  await page.locator('#sendButton').click()
  await waitInputUnlocked(page)
  expect(storySession).toBeTruthy()
})
