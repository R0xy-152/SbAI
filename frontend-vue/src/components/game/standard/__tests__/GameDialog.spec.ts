// docs/13 §26.1：thinking 占位+输入禁用、长文本完整显示、响应中输入禁用。
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { usePresentationStore } from '../../../../stores/presentation'
import GameDialog from '../GameDialog.vue'

function inputValue(wrapper: ReturnType<typeof mount>): string {
  return (wrapper.find('#inputMessage').element as HTMLTextAreaElement).value
}

describe('GameDialog（输入状态与长文本打字机）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('thinking：占位「思考中…」、textarea 只读、发送按钮禁用', () => {
    const store = usePresentationStore()
    store.state.status = 'thinking'
    store.state.dialogue.mode = 'ai'
    const wrapper = mount(GameDialog)
    const ta = wrapper.find('#inputMessage')
    expect(ta.attributes('placeholder')).toBe('思考中…')
    expect(ta.attributes('readonly')).toBeDefined()
    expect(wrapper.find('#sendButton').attributes('disabled')).toBeDefined()
  })

  it('responding（响应播放）：textarea 只读；切回 input 后可输入且发送可用', async () => {
    const store = usePresentationStore()
    store.state.status = 'streaming'
    store.state.dialogue.mode = 'ai'
    const wrapper = mount(GameDialog)
    const ta = wrapper.find('#inputMessage')
    expect(ta.attributes('readonly')).toBeDefined()
    // 解锁输入（GameView setInputMode(true) 等价：mode script + status idle）
    store.state.status = 'idle'
    store.state.dialogue.mode = 'script'
    await nextTick()
    expect(wrapper.find('#inputMessage').attributes('readonly')).toBeUndefined()
    expect(wrapper.find('#sendButton').attributes('disabled')).toBeUndefined()
  })

  it('长文本经打字机完整显示（fake timers 推进）', async () => {
    vi.useFakeTimers()
    const store = usePresentationStore()
    const long = '这是一段很长的台词，用来验证打字机不截断。'.repeat(20)
    const wrapper = mount(GameDialog)
    store.state.status = 'streaming'
    store.state.dialogue.mode = 'ai'
    store.state.dialogue.text = long
    await nextTick()
    // 每字符 delay ≤ 200 + 随机抖动（speed=50），给足 250ms/字
    vi.advanceTimersByTime(long.length * 250 + 1000)
    await nextTick()
    expect(inputValue(wrapper)).toBe(long)
    wrapper.unmount()
  })
})
