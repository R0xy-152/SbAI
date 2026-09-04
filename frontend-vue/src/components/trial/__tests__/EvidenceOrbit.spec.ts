import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import EvidenceOrbit from '../EvidenceOrbit.vue'

describe('EvidenceOrbit 拖拽层级', () => {
  let rectSpy: ReturnType<typeof vi.spyOn>
  let originalSetPointerCapture: typeof HTMLElement.prototype.setPointerCapture | undefined

  beforeEach(() => {
    vi.stubGlobal('requestAnimationFrame', () => 1)
    vi.stubGlobal('cancelAnimationFrame', () => undefined)
    vi.stubGlobal('ResizeObserver', class {
      observe() {}
      disconnect() {}
    })
    rectSpy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
      function getBoundingClientRect(this: HTMLElement) {
        const width = this.classList.contains('evidence-orbit') ? 400 : 120
        const height = this.classList.contains('evidence-orbit') ? 300 : 48
        return {
          x: 0,
          y: 0,
          top: 0,
          left: 0,
          width,
          height,
          right: width,
          bottom: height,
          toJSON: () => ({}),
        } as DOMRect
      },
    )
    originalSetPointerCapture = HTMLElement.prototype.setPointerCapture
    HTMLElement.prototype.setPointerCapture = vi.fn()
  })

  afterEach(() => {
    rectSpy.mockRestore()
    if (originalSetPointerCapture) {
      HTMLElement.prototype.setPointerCapture = originalSetPointerCapture
    } else {
      Reflect.deleteProperty(HTMLElement.prototype, 'setPointerCapture')
    }
    vi.unstubAllGlobals()
  })

  it('拖动期间允许证据越过物理场边界并标记为顶层拖动态', async () => {
    const wrapper = mount(EvidenceOrbit, {
      props: {
        evidence: [{ evidence_id: 'memory', title: '记忆断层', summary: 'test' }],
        selectedIds: [],
        seed: 7,
      },
    })
    await nextTick()

    const orbit = wrapper.get('[data-testid="evidence-orbit"]')
    const body = wrapper.get('.evidence-body')
    await body.trigger('pointerdown', { pointerId: 1, clientX: 100, clientY: 120 })
    await body.trigger('pointermove', { pointerId: 1, clientX: 620, clientY: 120 })

    expect(orbit.classes()).toContain('evidence-orbit--dragging')
    expect(body.classes()).toContain('evidence-body--dragging')
    expect(body.attributes('style')).toMatch(/translate3d\((?:[4-9]\d\d|\d{4,})/)

    await body.trigger('pointerup', { pointerId: 1, clientX: 620, clientY: 120 })
    expect(orbit.classes()).not.toContain('evidence-orbit--dragging')
    expect(wrapper.emitted('drop')?.[0]).toEqual([
      { evidenceId: 'memory', clientX: 620, clientY: 120 },
    ])
  })
})
