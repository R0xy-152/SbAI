import type { PresentationState } from '../types/presentation'

// docs/13 §10：Backend → Vue 的 Presentation Contract 统一在 Adapter 归一。
// 当前骨架返回空状态；Task 4 接入现有 /api/chat + /api/game/state 后按真实字段填充。
export function toPresentationState(): PresentationState {
  return {
    scene: { backgroundId: null },
    characters: {},
    presentCharacterIds: [],
    dialogue: { speakerId: null, speakerName: null, text: '', mode: 'ai' },
    status: 'idle',
    effects: [],
  }
}
