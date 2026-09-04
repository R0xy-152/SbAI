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

  it('试玩版独立置顶，保留并冻结原章节入口', () => {
    const wrapper = mount(ChapterSelectView)
    const cards = wrapper.findAll('button.chapter-card')

    expect(cards.map((card) => card.find('.chapter-name').text())).toEqual([
      '试玩版',
      '序章',
      '第一章',
      '第二章',
      '第三章',
      '第四章',
      '终章',
    ])
    expect(cards[0].attributes('disabled')).toBeUndefined()
    expect(cards[1].attributes('disabled')).toBeUndefined()
    for (const card of cards.slice(2)) {
      expect(card.attributes('disabled')).toBeDefined()
      expect(card.text()).toContain('未开发')
    }
  })

  it('进入试玩版时清理旧会话并进入独立体验', async () => {
    localStorage.setItem('gal_session_id', 'old-session')
    const game = useGameStore()
    game.sessionId = 'old-session'

    const wrapper = mount(ChapterSelectView)
    await wrapper.find('button.chapter-card').trigger('click')

    expect(localStorage.getItem('gal_session_id')).toBeNull()
    expect(game.sessionId).toBeNull()
    expect(pushMock).toHaveBeenCalledWith('/trial')
  })

  it('仍可进入原序章', async () => {
    const wrapper = mount(ChapterSelectView)
    await wrapper.findAll('button.chapter-card')[1].trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/story?story_id=prologue')
  })

  it('返回按钮回到标题页', async () => {
    const wrapper = mount(ChapterSelectView)
    await wrapper.find('button.chapter-back').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/')
  })
})
