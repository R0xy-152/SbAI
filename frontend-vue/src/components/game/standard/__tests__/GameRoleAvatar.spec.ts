// docs/13 §26.1：emotion 变化应用动画类、show=false 隐藏（opacity 0）。
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { usePresentationStore } from '../../../../stores/presentation'
import GameRoleAvatar from '../GameRoleAvatar.vue'
import { FakeImage } from './fake-image'

const baseRole = {
  roleId: 'deepseek',
  emotion: 'neutral',
  scale: 1,
  offsetY: 0,
  offsetX: 0,
  show: true,
  character_folder: 'deepseek',
  clothesName: 'default',
  bubbleTop: 0,
  bubbleLeft: 0,
}

describe('GameRoleAvatar（emotion 动画与显隐）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('Image', FakeImage)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function seedStage() {
    const store = usePresentationStore()
    store.state.characters['deepseek'] = {
      characterId: 'deepseek',
      visible: true,
      emotion: 'neutral',
      scale: 1,
      offsetX: 0,
      offsetY: 0,
      animation: null,
    }
    store.state.presentCharacterIds = ['deepseek']
  }

  it('emotion 变化应用对应动画类（neutral → happy-bounce）', async () => {
    seedStage()
    const wrapper = mount(GameRoleAvatar, { props: { role: baseRole } })
    await flushPromises()
    expect(wrapper.find('.happy-bounce').exists()).toBe(false)
    await wrapper.setProps({ role: { ...baseRole, emotion: 'happy' } })
    await flushPromises()
    expect(wrapper.find('.happy-bounce').exists()).toBe(true)
  })

  it('show=false 时容器 opacity 为 0（隐藏）', async () => {
    seedStage()
    const wrapper = mount(GameRoleAvatar, {
      props: { role: { ...baseRole, show: false } },
    })
    await flushPromises()
    const el = wrapper.find('.role-container-transition').element as HTMLElement
    expect(el.style.opacity).toBe('0')
  })
})
