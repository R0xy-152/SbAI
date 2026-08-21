import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ChapterOpening from '../ChapterOpening.vue'

describe('ChapterOpening', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('renders the authoritative chapter module and completes automatically', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false })))

    const wrapper = mount(ChapterOpening, {
      props: {
        chapterLabel: '序章',
        title: '制作现场突击检查！AI娘们的秘密日常',
        background: '/backgroud/background_prologue.png',
      },
    })

    expect(wrapper.get('[data-testid="chapter-opening"]').text()).toContain('序章')
    expect(wrapper.text()).toContain('制作现场突击检查！AI娘们的秘密日常')
    expect(wrapper.find('.chapter-opening-bg').attributes('style')).toContain(
      '/backgroud/background_prologue.png',
    )
    expect(wrapper.text()).not.toContain('bilibili')

    await vi.advanceTimersByTimeAsync(3800)
    expect(wrapper.emitted('complete')).toHaveLength(1)
    expect(wrapper.find('[data-testid="chapter-opening"]').exists()).toBe(false)
  })
})
