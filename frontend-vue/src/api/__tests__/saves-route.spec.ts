// docs/17 结局后自由聊天：存档目标路由助手（纯函数）。
import { describe, expect, it } from 'vitest'
import { saveTargetRoute } from '../saves'

describe('saveTargetRoute（故事存档 → /story；已完结/旧玩法 → /game）', () => {
  it('试玩版存档优先恢复到 /trial', () => {
    expect(saveTargetRoute(null, false, 'trial_v2')).toBe('/trial')
  })

  it('故事中段存档（有游标、未完结）→ /story', () => {
    expect(saveTargetRoute({ node_index: 42 }, false)).toBe('/story')
  })

  it('序章中段存档 → 带 story_id 的播放器', () => {
    expect(saveTargetRoute({ story_id: 'prologue', phase: 'branch' }, false)).toBe(
      '/story?story_id=prologue',
    )
  })

  it('故事结局后自由聊天存档（游标=end、已完结）→ /game', () => {
    expect(saveTargetRoute({ node_index: 197 }, true)).toBe('/game')
  })

  it('旧玩法存档（无故事游标）→ /game', () => {
    expect(saveTargetRoute(null, false)).toBe('/game')
    expect(saveTargetRoute(null, true)).toBe('/game')
  })
})
