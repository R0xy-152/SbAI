// docs/15 §9.1：GameBackground 场景粒子层 —— effect 映射与设置开关。
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import GameBackground from '../GameBackground.vue'
import { usePresentationStore } from '../../../../stores/presentation'
import { useSettingsStore } from '../../../../stores/settings'

describe('GameBackground 场景粒子层（docs/15 §6.2）', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  function setEffect(effect: string | null) {
    const presentation = usePresentationStore()
    presentation.state.scene.backgroundId = '/backgroud/background1.png'
    presentation.state.scene.backgroundEffect = effect
  }

  it('effect=null：不渲染粒子组件', () => {
    setEffect(null)
    const wrapper = mount(GameBackground)
    expect(wrapper.findAll('canvas').length).toBe(0)
    wrapper.unmount()
  })

  it('effect=StarField + 开关开：渲染 StarField（canvas）', () => {
    setEffect('StarField')
    const wrapper = mount(GameBackground)
    // 无 2d context 环境：canvas 存在但不绘制，组件不抛错（docs/15 §6.3）
    expect(wrapper.findAll('canvas').length).toBe(1)
    wrapper.unmount()
  })

  it('sceneEffectsEnabled=false：即使 effect 存在也不渲染', () => {
    setEffect('StarField')
    const settings = useSettingsStore()
    settings.sceneEffectsEnabled = false
    const wrapper = mount(GameBackground)
    expect(wrapper.findAll('canvas').length).toBe(0)
    wrapper.unmount()
  })

  it('五种 effect 均能挂载对应组件且不抛错', () => {
    for (const effect of ['StarField', 'Rain', 'Sakura', 'Snow', 'Fireworks']) {
      setEffect(effect)
      const wrapper = mount(GameBackground)
      expect(wrapper.exists()).toBe(true)
      wrapper.unmount()
    }
  })
})
