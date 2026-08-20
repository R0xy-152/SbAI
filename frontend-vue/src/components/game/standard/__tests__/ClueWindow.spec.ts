// docs/16 P7：线索窗口 —— 渲染证据标题+描述；close 事件。
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ClueWindow from '../ClueWindow.vue'

describe('ClueWindow（docs/16 P7）', () => {
  it('渲染标题与描述', () => {
    const wrapper = mount(ClueWindow, { props: { title: '压痕纸条', summary: '一张有浅压痕的纸。' } })
    expect(wrapper.find('[data-testid="clue-window"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('压痕纸条')
    expect(wrapper.text()).toContain('一张有浅压痕的纸。')
  })

  it('点击关闭 emit close', async () => {
    const wrapper = mount(ClueWindow, { props: { title: 't', summary: 's' } })
    await wrapper.find('[data-testid="clue-window-close"]').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})

