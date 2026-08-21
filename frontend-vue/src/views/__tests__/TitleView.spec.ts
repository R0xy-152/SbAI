// docs/13 §26.1：Continue no-save（无存档禁用 / 有存档启用）。
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import TitleView from '../TitleView.vue'

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('../../api/saves', () => ({
  listSaves: vi.fn(),
  manualSave: vi.fn(),
  autoSave: vi.fn(),
  loadSave: vi.fn(),
  deleteSave: vi.fn(),
  getPlayerId: vi.fn(() => 'test-player'),
  saveTargetRoute: vi.fn(() => '/story'),
}))

import { listSaves } from '../../api/saves'
import type { GameSaveInfo } from '../../api/saves'
const listSavesMock = vi.mocked(listSaves)

const EMPTY: Array<GameSaveInfo | null> = [null, null, null, null, null, null]

function continueButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button.title-btn')[1]
}

describe('TitleView（Continue 无存档禁用）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listSavesMock.mockReset()
    pushMock.mockReset()
  })

  it('一级菜单固定为四项单列，并由开始游戏进入章节选择', async () => {
    listSavesMock.mockResolvedValue({ auto: null, manual: EMPTY })
    const wrapper = mount(TitleView)
    await flushPromises()

    const buttons = wrapper.findAll('button.title-btn')
    expect(buttons.map((button) => button.text())).toEqual([
      '开始游戏',
      '继续游戏',
      '读取存档',
      '设置',
    ])
    expect(wrapper.find('nav').classes()).not.toContain('grid-cols-2')

    await buttons[0].trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/chapters')
  })

  it('无任何存档：Continue 按钮禁用', async () => {
    listSavesMock.mockResolvedValue({ auto: null, manual: EMPTY })
    const wrapper = mount(TitleView)
    await flushPromises()
    expect(continueButton(wrapper).attributes('disabled')).toBeDefined()
  })

  it('有存档（手动 slot1）：Continue 按钮启用', async () => {
    const save: GameSaveInfo = {
      id: 'save-1',
      player_id: 'test-player',
      slot_type: 'MANUAL',
      slot_index: 1,
      title: null,
      source_session_id: 'sess',
      chapter_id: 'ch1',
      phase: 'opening',
      created_at: '2026-08-19T10:00:00Z',
      updated_at: '2026-08-19T11:00:00Z',
    }
    const manual = [...EMPTY]
    manual[0] = save
    listSavesMock.mockResolvedValue({ auto: null, manual })
    const wrapper = mount(TitleView)
    await flushPromises()
    expect(continueButton(wrapper).attributes('disabled')).toBeUndefined()
  })
})
