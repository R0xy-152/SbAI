// 快速上线固定剧本 · 选项窗口（借鉴 LingChat GameChoices 实现）：
// 渲染 A/B/C 选项（胶囊按钮、无「继续对话」关闭项）；点击后回传 select。
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import StoryChoiceWindow from '../StoryChoiceWindow.vue'
import type { StoryOptionView } from '../../../../api/story'

const SAMPLE: StoryOptionView[] = [
  { id: 'A', label: '“你是谁？”' },
  { id: 'B', label: '“你看起来比我还紧张。”' },
  { id: 'C', label: '“这里是哪？”' },
]

afterEach(() => {
  vi.useRealTimers()
})

describe('StoryChoiceWindow（快速上线，借鉴 LingChat GameChoices）', () => {
  it('渲染全部选项按钮，且没有「继续对话」关闭项', () => {
    const wrapper = mount(StoryChoiceWindow, { props: { options: SAMPLE, busy: false } })
    expect(wrapper.find('[data-testid="story-choice-window"]').exists()).toBe(true)
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(3)
    expect(wrapper.text()).toContain('你是谁？')
    expect(wrapper.text()).toContain('你看起来比我还紧张。')
    expect(wrapper.text()).toContain('这里是哪？')
    expect(wrapper.text()).not.toContain('继续对话')
  })

  it('点击选项在离场动画后 emit select（携带选项 id）', async () => {
    vi.useFakeTimers()
    const wrapper = mount(StoryChoiceWindow, { props: { options: SAMPLE, busy: false } })
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('select')).toBeUndefined() // 离场动画期间不立即提交
    vi.advanceTimersByTime(300)
    expect(wrapper.emitted('select')?.[0]?.[0]).toBe('B')
  })

  it('busy 时按钮禁用，点击不 emit', async () => {
    vi.useFakeTimers()
    const wrapper = mount(StoryChoiceWindow, { props: { options: SAMPLE, busy: true } })
    await wrapper.findAll('button')[0].trigger('click')
    vi.advanceTimersByTime(1000)
    expect(wrapper.emitted('select')).toBeUndefined()
  })
})
