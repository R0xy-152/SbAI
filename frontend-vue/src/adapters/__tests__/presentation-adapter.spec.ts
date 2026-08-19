// docs/15 §9.1：presentation_state 对账写入 background_effect。
import { describe, it, expect } from 'vitest'
import { applyPresentationStateView, toPresentationState } from '../presentation-adapter'
import type { PresentationStateView } from '../../api/game'

describe('presentation-adapter backgroundEffect（docs/15 §6.1）', () => {
  it('view.background_effect 写入 scene.backgroundEffect', () => {
    const state = toPresentationState()
    const view: PresentationStateView = {
      scene: 'binding_room',
      background_effect: 'StarField',
      characters: [],
      input_mode: 'investigation',
    }
    applyPresentationStateView(state, view)
    expect(state.scene.backgroundEffect).toBe('StarField')
  })

  it('缺省（旧后端）不覆盖已有 effect', () => {
    const state = toPresentationState()
    state.scene.backgroundEffect = 'Rain'
    const view: PresentationStateView = {
      scene: 'binding_room',
      characters: [],
      input_mode: 'investigation',
    }
    applyPresentationStateView(state, view)
    expect(state.scene.backgroundEffect).toBe('Rain')
  })

  it('null 明确清空 effect', () => {
    const state = toPresentationState()
    state.scene.backgroundEffect = 'StarField'
    const view: PresentationStateView = {
      scene: 'binding_room',
      background_effect: null,
      characters: [],
      input_mode: 'investigation',
    }
    applyPresentationStateView(state, view)
    expect(state.scene.backgroundEffect).toBeNull()
  })
})
