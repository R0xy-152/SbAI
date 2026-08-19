// docs/13 §26.1：Load Slot empty/occupied（空槽「暂无存档」、占用槽点击 emit load）。
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LoadPanel from '../LoadPanel.vue'
import ManualSaveSlot from '../ManualSaveSlot.vue'

vi.mock('../../../api/saves', () => ({
  listSaves: vi.fn(),
  manualSave: vi.fn(),
  autoSave: vi.fn(),
  loadSave: vi.fn(),
  deleteSave: vi.fn(),
  getPlayerId: vi.fn(() => 'test-player'),
}))

import { listSaves } from '../../../api/saves'
import type { GameSaveInfo } from '../../../api/saves'
const listSavesMock = vi.mocked(listSaves)

function makeSave(slot: number): GameSaveInfo {
  return {
    id: 'save-' + slot,
    player_id: 'test-player',
    slot_type: 'MANUAL',
    slot_index: slot,
    title: null,
    source_session_id: 'sess',
    chapter_id: 'ch1',
    phase: 'opening',
    created_at: '2026-08-19T10:00:00Z',
    updated_at: '2026-08-19T11:00:00Z',
  }
}

const EMPTY: Array<GameSaveInfo | null> = [null, null, null, null, null, null]

describe('LoadPanel（存档位空/占用与 load 回调）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listSavesMock.mockReset()
  })

  it('全部空槽：6 个「暂无存档」+「暂无自动存档」', async () => {
    listSavesMock.mockResolvedValue({ auto: null, manual: EMPTY })
    const wrapper = mount(LoadPanel)
    await flushPromises()
    expect(wrapper.text().match(/暂无存档/g)).toHaveLength(6)
    expect(wrapper.text()).toContain('暂无自动存档')
  })

  it('占用槽点击：emit load 且携带存档 id', async () => {
    const manual = [...EMPTY]
    manual[0] = makeSave(1)
    listSavesMock.mockResolvedValue({ auto: null, manual })
    const wrapper = mount(LoadPanel)
    await flushPromises()
    wrapper.findAllComponents(ManualSaveSlot)[0].vm.$emit('action', 1)
    await flushPromises()
    const loads = wrapper.emitted('load')
    expect(loads).toBeTruthy()
    expect(loads![0][0]).toBe('save-1')
  })
})
