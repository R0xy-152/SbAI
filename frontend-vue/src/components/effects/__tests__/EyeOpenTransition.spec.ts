// docs/16 P5：睁眼转场 —— 正常 ~1s 后完成；reduced-motion 立即完成。
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import EyeOpenTransition from '../EyeOpenTransition.vue'

describe('EyeOpenTransition（docs/16 P5）', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('正常路径：渲染黑幕，约 1s 后 emit complete', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => setTimeout(() => cb(0), 0))
    const wrapper = mount(EyeOpenTransition)
    expect(wrapper.find('[data-testid="eye-open"]').exists()).toBe(true)
    await vi.advanceTimersByTimeAsync(1300)
    expect(wrapper.emitted('complete')).toHaveLength(1)
    wrapper.unmount()
  })

  it('reduced-motion：立即 emit complete，不播动画', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const wrapper = mount(EyeOpenTransition)
    expect(wrapper.emitted('complete')).toHaveLength(1)
    wrapper.unmount()
  })
})
