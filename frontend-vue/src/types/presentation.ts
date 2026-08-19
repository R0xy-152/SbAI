// Presentation Store 数据模型（docs/13 §9）：只保存「当前应如何展示」，
// 不持有 Game Truth；角色是否出现由 Backend Narrative 决定。
export interface SceneLighting {
  brightness?: number
  hue?: number
}

export interface PresentedCharacter {
  characterId: string
  visible: boolean
  emotion: string
  scale: number
  offsetX: number
  offsetY: number
  animation?: string | null
}

export interface PresentationState {
  scene: {
    backgroundId: string | null
    lighting?: SceneLighting
  }
  characters: Record<string, PresentedCharacter>
  presentCharacterIds: string[]
  dialogue: {
    speakerId: string | null
    speakerName: string | null
    text: string
    mode: 'script' | 'ai' | 'system'
  }
  status: 'idle' | 'thinking' | 'streaming' | 'transitioning'
  effects: string[]
}
