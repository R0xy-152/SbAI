// docs/14 §2.2（T2）：选项气泡条渲染 / busy 禁用 / 路由高亮 / payload 原样回传。
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import OptionsPanel from '../OptionsPanel.vue'
import type { GameOption } from '../../../../api/game'

function opt(
  partial: Partial<GameOption> & { id: string; label: string },
): GameOption {
  return { kind: 'investigate', payload: {}, ...partial }
}

describe('OptionsPanel（选项气泡条）', () => {
  it('渲染后端下发的选项气泡（hint 挂在 title）', () => {
    const wrapper = mount(OptionsPanel, {
      props: {
        options: [
          opt({ id: 'investigate:CH1_NOTE_01', label: '桌上的纸', hint: '预览文案' }),
          opt({
            id: 'chat_routing:claude',
            label: '找 Claude 谈谈',
            kind: 'chat_routing',
            payload: { character_id: 'claude' },
          }),
        ],
        busy: false,
        feedback: null,
        routeLabel: null,
        activeRouteId: null,
      },
    })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(2)
    expect(buttons[0].text()).toContain('桌上的纸')
    expect(buttons[0].attributes('title')).toBe('预览文案')
  })

  it('点击气泡原样回传选项对象（前端不解释 payload，D7）', async () => {
    const target = opt({
      id: 'chat_routing:claude',
      label: '找 Claude 谈谈',
      kind: 'chat_routing',
      payload: { character_id: 'claude' },
    })
    const wrapper = mount(OptionsPanel, {
      props: {
        options: [target],
        busy: false,
        feedback: null,
        routeLabel: null,
        activeRouteId: null,
      },
    })
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted('select')?.[0]?.[0]).toEqual(target)
  })

  it('busy 时全部禁用；无选项且无反馈/路由提示时不渲染', () => {
    const wrapper = mount(OptionsPanel, {
      props: {
        options: [opt({ id: 'x', label: 'A' })],
        busy: true,
        feedback: null,
        routeLabel: null,
        activeRouteId: null,
      },
    })
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
    const empty = mount(OptionsPanel, {
      props: {
        options: [],
        busy: false,
        feedback: null,
        routeLabel: null,
        activeRouteId: null,
      },
    })
    expect(empty.find('[data-testid="options-panel"]').exists()).toBe(false)
  })

  it('路由激活时高亮对应气泡并显示提示；否则显示反馈文案', () => {
    const wrapper = mount(OptionsPanel, {
      props: {
        options: [
          opt({
            id: 'chat_routing:claude',
            label: '找 Claude 谈谈',
            kind: 'chat_routing',
            payload: { character_id: 'claude' },
          }),
        ],
        busy: false,
        feedback: null,
        routeLabel: '正在与 Claude 对话：再点同一气泡回到公共对话',
        activeRouteId: 'chat_routing:claude',
      },
    })
    expect(wrapper.text()).toContain('正在与 Claude 对话')
    expect(wrapper.find('button').classes()).toContain('bg-[#123c63]')
    const withFeedback = mount(OptionsPanel, {
      props: {
        options: [],
        busy: false,
        feedback: '调查完成，获得新线索。',
        routeLabel: null,
        activeRouteId: null,
      },
    })
    expect(withFeedback.text()).toContain('调查完成，获得新线索。')
  })
})
