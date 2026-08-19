// Presentation Store 数据模型（docs/13 §9）：只保存「当前应如何展示」，
// 不持有 Game Truth；角色是否出现由 Backend Narrative 决定。
export interface SceneLighting {
  brightness?: number
  hue?: number
  // 场景光照（LingChat currentScene.lighting 的完整契约，docs/13 §11 保留光照叠层）
  background?: {
    brightness?: number
    contrast?: number
    saturation?: number
    glow_radius?: number
    glow_color?: string
    sepia?: number
  }
  character?: {
    brightness?: number
    contrast?: number
    saturation?: number
    glow_radius?: number
    glow_color?: string
    sepia?: number
  }
  overlay_enabled?: boolean
  overlay_target?: 'background' | 'character' | 'both'
  blend_mode?: string
  light_x?: number
  light_y?: number
  overlay_color1?: string
  overlay_color2?: string
  overlay_radius?: number
  overlay_opacity?: number
}

export interface PresentedCharacter {
  characterId: string
  visible: boolean
  emotion: string
  scale: number
  offsetX: number
  offsetY: number
  /** 显式 slot（LEFT/RIGHT/…）：百分比站位，覆盖自动排位（T2review P1-13）。 */
  slot?: string | null
  animation?: string | null
}

export interface PresentationState {
  scene: {
    backgroundId: string | null
    /** 场景粒子氛围层（docs/15 §6.1：StarField/Rain/Sakura/Snow/Fireworks/null） */
    backgroundEffect?: string | null
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
