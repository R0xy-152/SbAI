// docs/19 序章主线最低 E2E（docs/13 §26.4 链路在新流程下的对应验收）。
// Title → 开始游戏 → /chapters → 序章（/story?story_id=prologue）→ 开场逐行
// → 探班三角色（无序循环，剩余角色过滤）→ 三人集合 → 自由交流模式 →
// 最终选择角色 → 进入 /game 自由聊天（AI 回复）。
// 序章是固定剧本（docs/story/Prologue.md）：无输入框，点「继续」（#sendButton）
// 逐行推进；选项经 story-choice-window 点选。关键台词确定性比对（waitTyped），
// 角色篇内的长台词序列用 advanceToStoryChoice 循环推进到下一选项。
import { test, expect } from '@playwright/test'
import {
  freezeAnimations,
  waitTyped,
  startNewGame,
  storyAdvanceLine,
  chooseStoryOption,
  advanceToStoryChoice,
} from '../visual/fixtures'

const INTRO_FIRST = '今天难得有空。'
const INTRO_LAST = '第一站去找谁呢？'
const DEEPSEEK_FIRST = '这里是……'
const CHATGPT_FIRST = '这里好多画稿。'
const CLAUDE_FIRST = '这里的气氛……'
const REUNION_FIRST = '看来大家都在为了这个游戏努力。'
const AFTERTALK_FIRST = '序章剧情结束。'

test('序章主线可运行（docs/19 验收链路）', async ({ page }) => {
  await freezeAnimations(page)

  // Title → /chapters → 序章 → 台词区出现第一句
  await startNewGame(page)
  await waitTyped(page, INTRO_FIRST)
  expect(page.url()).toContain('/story?story_id=prologue')
  const sessionId = await page.evaluate(() => localStorage.getItem('gal_session_id'))
  expect(sessionId).toBeTruthy()

  // 开场 16 行 → 首次探班选择：三角色齐全
  await waitTyped(page, INTRO_LAST)
  await storyAdvanceLine(page)
  const firstOptions = await advanceToStoryChoice(page)
  for (const label of ['去找 DeepSeek', '去找 ChatGPT', '去找 Claude']) {
    expect(firstOptions).toContain(label)
  }

  // 探班 DeepSeek 篇 → 选项只剩剩余角色（无 DeepSeek）
  await chooseStoryOption(page, '去找 DeepSeek')
  await waitTyped(page, DEEPSEEK_FIRST)
  const afterDS = await advanceToStoryChoice(page)
  expect(afterDS).not.toContain('去找 DeepSeek')
  expect(afterDS).toContain('去找 ChatGPT')
  expect(afterDS).toContain('去找 Claude')

  // 探班 ChatGPT 篇 → 只剩 Claude
  await chooseStoryOption(page, '去找 ChatGPT')
  await waitTyped(page, CHATGPT_FIRST)
  const afterGPT = await advanceToStoryChoice(page)
  expect(afterGPT).toEqual(['去找 Claude'])

  // 探班 Claude 篇 → 三角色访问完 → 三人集合（不再出现探班选项）
  await chooseStoryOption(page, '去找 Claude')
  await waitTyped(page, CLAUDE_FIRST)
  await storyAdvanceLine(page)
  await waitTyped(page, REUNION_FIRST)

  // 自由交流模式开启（aftertalk）→ 最终角色选择
  await waitTyped(page, AFTERTALK_FIRST)
  await storyAdvanceLine(page)
  const finalOptions = await advanceToStoryChoice(page)
  for (const label of ['与 DeepSeek 聊天', '与 ChatGPT 聊天', '与 Claude 聊天']) {
    expect(finalOptions).toContain(label)
  }

  // 选择与 DeepSeek 聊天 → 进入 /game 自由聊天（chat 节点路由，带 ?character= 参数）
  await chooseStoryOption(page, '与 DeepSeek 聊天')
  await page.waitForURL('**/game**', { timeout: 15_000 })
})
