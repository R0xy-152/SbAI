import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import RoleSprite from '../RoleSprite.vue'

class ControlledImage {
  static instances: ControlledImage[] = []
  onload: (() => void) | null = null
  onerror: ((error: unknown) => void) | null = null
  src = ''

  constructor() {
    ControlledImage.instances.push(this)
  }

  decode() {
    return Promise.resolve()
  }

  completeLoad() {
    this.onload?.()
  }
}

describe('RoleSprite', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    ControlledImage.instances = []
  })

  it('预加载完成后在单一 img 上原子切换差分', async () => {
    vi.stubGlobal('Image', ControlledImage)
    const wrapper = mount(RoleSprite, { props: { src: '/neutral.png' } })
    expect(wrapper.findAll('img')).toHaveLength(1)

    ControlledImage.instances[0]?.completeLoad()
    await flushPromises()
    await nextTick()
    expect(wrapper.find('img').attributes('src')).toBe('/neutral.png')

    await wrapper.setProps({ src: '/embarrassed.png' })
    expect(wrapper.findAll('img')).toHaveLength(1)
    expect(wrapper.find('img').attributes('src')).toBe('/neutral.png')

    ControlledImage.instances[1]?.completeLoad()
    await flushPromises()
    await nextTick()
    expect(wrapper.findAll('img')).toHaveLength(1)
    expect(wrapper.find('img').attributes('src')).toBe('/embarrassed.png')
  })
})
