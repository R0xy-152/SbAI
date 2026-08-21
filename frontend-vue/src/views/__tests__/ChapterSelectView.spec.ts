import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ChapterSelectView from '../ChapterSelectView.vue'
import { useGameStore } from '../../stores/game'

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

describe('ChapterSelectView', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    pushMock.mockReset()
  })

  it('按视觉稿顺序显示六章，且仅序章解锁', () => {
    const wrapper = mount(ChapterSelectView)
    const cards = wrapper.findAll('button.chapter-card')

    expect(cards.map((card) => card.find('.chapter-name').text())).toEqual([
      '序章',
      '第一章',
      '第二章',
      '第三章',
      '第四章',
      '终章',
    ])
    expect(cards[0].attributes('disabled')).toBeUndefined()
    for (const card of cards.slice(1)) {
      expect(card.attributes('disabled')).toBeDefined()
      expect(card.text()).toContain('未开发')
    }
  })

  it('进入序章时清理旧会话并进入固定剧本', async () => {
    localStorage.setItem('gal_session_id', 'old-session')
    const game = useGameStore()
    game.sessionId = 'old-session'

    const wrapper = mount(ChapterSelectView)
    await wrapper.find('button.chapter-card').trigger('click')

    expect(localStorage.getItem('gal_session_id')).toBeNull()
    expect(game.sessionId).toBeNull()
    expect(pushMock).toHaveBeenCalledWith('/story?story_id=prologue')
  })

  it('返回按钮回到标题页', async () => {
    const wrapper = mount(ChapterSelectView)
    await wrapper.find('button.chapter-back').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/')
  })
})
