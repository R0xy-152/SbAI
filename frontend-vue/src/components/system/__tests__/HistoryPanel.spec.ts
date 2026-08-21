import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import HistoryPanel from '../HistoryPanel.vue'

const { fetchHistory } = vi.hoisted(() => ({ fetchHistory: vi.fn() }))

vi.mock('../../../api/game', () => ({ fetchHistory }))

describe('HistoryPanel', () => {
  it('在半透明窗口中显示说话人与对话，并以 X 关闭', async () => {
    fetchHistory.mockResolvedValueOnce({
      session_id: 'session-1',
      messages: [
        { role: 'character', character_id: 'deepseek', content: '你好。' },
        { role: 'player', character_id: null, content: '你好！' },
      ],
    })
    const wrapper = mount(HistoryPanel, { props: { sessionId: 'session-1' } })
    await flushPromises()

    expect(wrapper.find('.history-mask').exists()).toBe(true)
    expect(wrapper.find('.history-panel').exists()).toBe(true)
    expect(wrapper.find('.history-panel').classes()).toContain('gal-font-sans')
    expect(wrapper.find('.history-scroll').classes()).toContain('overflow-y-auto')
    expect(wrapper.text()).toContain('DeepSeek')
    expect(wrapper.text()).toContain('你好。')
    expect(wrapper.text()).toContain('你好！')

    await wrapper.get('button[aria-label="关闭对话历史"]').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
