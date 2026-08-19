// docs/13 §26.1：Save Slot empty/occupied（空槽「空存档位」、占用槽标题+阶段）。
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SavePanel from '../SavePanel.vue'

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

function makeSave(slot: number, title: string | null = null): GameSaveInfo {
  return {
    id: 'save-' + slot,
    player_id: 'test-player',
    slot_type: 'MANUAL',
    slot_index: slot,
    title,
    source_session_id: 'sess',
    chapter_id: 'ch1',
    phase: 'investigation',
    created_at: '2026-08-19T10:00:00Z',
    updated_at: '2026-08-19T11:00:00Z',
  }
}

const EMPTY: Array<GameSaveInfo | null> = [null, null, null, null, null, null]

describe('SavePanel（存档位空/占用渲染）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    listSavesMock.mockReset()
  })

  it('全部空槽：6 个「空存档位」+「暂无自动存档」', async () => {
    listSavesMock.mockResolvedValue({ auto: null, manual: EMPTY })
    const wrapper = mount(SavePanel, { props: { sessionId: 'sess', busy: false } })
    await flushPromises()
    expect(wrapper.text().match(/空存档位/g)).toHaveLength(6)
    expect(wrapper.text()).toContain('暂无自动存档')
  })

  it('占用槽：显示标题与章节·阶段', async () => {
    const manual = [...EMPTY]
    manual[0] = makeSave(1, '自定义标题')
    listSavesMock.mockResolvedValue({ auto: null, manual })
    const wrapper = mount(SavePanel, { props: { sessionId: 'sess', busy: false } })
    await flushPromises()
    expect(wrapper.text()).toContain('自定义标题')
    expect(wrapper.text()).toContain('第一章 · 调查')
    expect(wrapper.text().match(/空存档位/g)).toHaveLength(5)
  })
})
