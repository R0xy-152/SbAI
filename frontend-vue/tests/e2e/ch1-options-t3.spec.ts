// docs/19 序章探班循环验收（对应旧 T3「选项推进」在新流程下的语义）。
// 权威规则（docs/story/Prologue.md）：三角色并列分支、无固定顺序；每次只能选
// 尚未访问的角色；访问后选项只剩剩余角色；三角色全访问后进入「三人集合」，
// 不再出现探班选项。D3 语义：未解锁/已完成的选项在窗口内不可见。
import { test, expect } from '@playwright/test'
import {
  freezeAnimations,
  waitTyped,
  startNewGame,
  storyAdvanceLine,
  chooseStoryOption,
  advanceToStoryChoice,
} from '../visual/fixtures'

const INTRO_LAST = '第一站去找谁呢？'
const DEEPSEEK_FIRST = '这里是……'
const CHATGPT_FIRST = '这里好多画稿。'
const CLAUDE_FIRST = '这里的气氛……'
const REUNION_FIRST = '看来大家都在为了这个游戏努力。'

test('T3 探班循环：剩余角色过滤，三角色全部访问后进入集合', async ({ page }) => {
  await freezeAnimations(page)
  await startNewGame(page)

  // 开场 → 首次探班选择：三角色齐全
  await waitTyped(page, INTRO_LAST)
  await storyAdvanceLine(page)
  let options = await advanceToStoryChoice(page)
  expect(options).toHaveLength(3)
  expect(options).toEqual(['去找 DeepSeek', '去找 ChatGPT', '去找 Claude'])

  // 访问 Claude → 选项只剩 DeepSeek / ChatGPT（D3：已访问角色消失）
  await chooseStoryOption(page, '去找 Claude')
  await waitTyped(page, CLAUDE_FIRST)
  options = await advanceToStoryChoice(page)
  expect(options).toEqual(['去找 DeepSeek', '去找 ChatGPT'])

  // 访问 DeepSeek → 只剩 ChatGPT
  await chooseStoryOption(page, '去找 DeepSeek')
  await waitTyped(page, DEEPSEEK_FIRST)
  options = await advanceToStoryChoice(page)
  expect(options).toEqual(['去找 ChatGPT'])

  // 访问 ChatGPT → 三角色全部访问 → 直接进入三人集合（无探班选项）
  await chooseStoryOption(page, '去找 ChatGPT')
  await waitTyped(page, CHATGPT_FIRST)
  await storyAdvanceLine(page)
  await waitTyped(page, REUNION_FIRST)
  await expect(page.locator('[data-testid="story-choice-window"]')).toHaveCount(0)
})
