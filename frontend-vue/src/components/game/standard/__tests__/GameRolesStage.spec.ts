// docs/13 §26.1：0/1/2/3 角色在场数量与 show/hide（只验证表现层，
// 剧情判断属于 Backend，docs/13 §9.2）。
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { usePresentationStore } from '../../../../stores/presentation'
import GameRolesStage from '../GameRolesStage.vue'
import GameRoleAvatar from '../GameRoleAvatar.vue'
import { FakeImage } from './fake-image'

function present(id: string, visible: boolean, emotion = 'neutral') {
  return {
    characterId: id,
    visible,
    emotion,
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    animation: null,
  }
}

describe('GameRolesStage（角色数量与可见性）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('Image', FakeImage)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('0 角色：不渲染任何角色头像', () => {
    const wrapper = mount(GameRolesStage)
    expect(wrapper.findAllComponents(GameRoleAvatar)).toHaveLength(0)
  })

  it.each([1, 2, 3])('%i 角色：渲染对应数量头像且顺序与在场名单一致', async (count) => {
    const store = usePresentationStore()
    const ids = ['deepseek', 'claude', 'chatgpt'].slice(0, count)
    for (const id of ids) store.state.characters[id] = present(id, true)
    store.state.presentCharacterIds = ids
    const wrapper = mount(GameRolesStage)
    await flushPromises()
    const avatars = wrapper.findAllComponents(GameRoleAvatar)
    expect(avatars).toHaveLength(count)
    expect(avatars.map((a) => a.props('role').roleId)).toEqual(ids)
  })

  it('visible=false 的角色从舞台移除（show/hide）', async () => {
    const store = usePresentationStore()
    store.state.characters['deepseek'] = present('deepseek', true)
    store.state.characters['claude'] = present('claude', true)
    store.state.presentCharacterIds = ['deepseek', 'claude']
    const wrapper = mount(GameRolesStage)
    await flushPromises()
    expect(wrapper.findAllComponents(GameRoleAvatar)).toHaveLength(2)
    store.state.characters['claude'].visible = false
    await flushPromises()
    expect(wrapper.findAllComponents(GameRoleAvatar)).toHaveLength(1)
  })
})
