// docs/16 P7/P8：选项窗口 —— 渲染选项 + 继续对话关闭项；select/dismiss 事件。
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OptionWindow from '../OptionWindow.vue'
import type { GameOption } from '../../../../api/game'

function opt(id: string, label: string, kind: GameOption['kind'] = 'investigate'): GameOption {
  return { id, label, kind, payload: {} }
}

describe('OptionWindow（docs/16 P7/P8）', () => {
  it('渲染选项与「继续对话」关闭项', () => {
    const wrapper = mount(OptionWindow, {
      props: { options: [opt('a', '桌上的纸'), opt('b', '找 Claude 谈谈', 'chat_routing')], busy: false, activeRouteId: null },
    })
    expect(wrapper.find('[data-testid="option-window"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('桌上的纸')
    expect(wrapper.text()).toContain('找 Claude 谈谈')
    expect(wrapper.text()).toContain('继续对话')
  })

  it('点击选项 emit select；点击继续对话 emit dismiss', async () => {
    const wrapper = mount(OptionWindow, {
      props: { options: [opt('a', '桌上的纸')], busy: false, activeRouteId: null },
    })
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted('select')?.[0]?.[0]).toEqual(expect.objectContaining({ id: 'a' }))
    await wrapper.find('[data-testid="option-window-dismiss"]').trigger('click')
    expect(wrapper.emitted('dismiss')).toHaveLength(1)
  })
})

