import type { PresentationState } from '../types/presentation'
import type { ChatResponse, PresentationAction, PresentationStateView } from '../api/game'

// docs/13 §10：Backend → Vue 的 Presentation Contract 统一在 Adapter 归一。
// 前端 Store 只保存「当前应如何展示」，所有展示变化来自 Backend 的
// presentation_actions / presentation_state（docs/13 §9.2：禁止 Store 做剧情判断）。

// 自动站位公式（docs/13 §9.1）：position = (index+1)/(count+1)*100%。
// 显式 slot 覆盖自动站位（docs/12 §10.1）：explicit slot > manual offset > auto。
const SLOT_PCT: Record<string, number> = {
  LEFT: 25,
  CENTER_LEFT: 40,
  CENTER: 50,
  CENTER_RIGHT: 60,
  RIGHT: 75,
}

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

function ensureCharacter(state: PresentationState, characterId: string): void {
  if (!state.characters[characterId]) {
    state.characters[characterId] = {
      characterId,
      visible: false,
      emotion: 'neutral',
      scale: 1,
      offsetX: 0,
      offsetY: 0,
      animation: null,
    }
  }
}

/** 一个已注册 Presentation Action（docs/12 §13 白名单）落到 Store。未知 type
 * 拒绝执行并记录（docs/12 §13：任何未知 Action 拒绝执行并记录日志）。 */
export function applyPresentationAction(state: PresentationState, action: PresentationAction): boolean {
  switch (action.type) {
    case 'CHARACTER_SHOW': {
      if (!action.character_id) return false
      ensureCharacter(state, action.character_id)
      state.characters[action.character_id].visible = true
      if (action.slot) {
        state.characters[action.character_id].offsetX = SLOT_PCT[action.slot]
      }
      if (action.emotion) {
        state.characters[action.character_id].emotion = action.emotion
      }
      if (action.animation) {
        state.characters[action.character_id].animation = action.animation
      }
      // 出场即成为在场角色（docs/12 §10 自动站位按 presentCharacterIds 排位）
      if (!state.presentCharacterIds.includes(action.character_id)) {
        state.presentCharacterIds.push(action.character_id)
      }
      return true
    }
    case 'CHARACTER_HIDE': {
      if (!action.character_id) return false
      ensureCharacter(state, action.character_id)
      state.characters[action.character_id].visible = false
      state.presentCharacterIds = state.presentCharacterIds.filter(
        (id) => id !== action.character_id,
      )
      return true
    }
    case 'CHARACTER_EMOTION': {
      if (!action.character_id) return false
      ensureCharacter(state, action.character_id)
      if (action.emotion) state.characters[action.character_id].emotion = action.emotion
      if (action.slot) state.characters[action.character_id].offsetX = SLOT_PCT[action.slot]
      if (action.scale != null) state.characters[action.character_id].scale = action.scale
      if (action.offset_x != null) state.characters[action.character_id].offsetX = action.offset_x
      if (action.offset_y != null) state.characters[action.character_id].offsetY = action.offset_y
      return true
    }
    case 'CHARACTER_ANIMATION': {
      if (!action.character_id) return false
      ensureCharacter(state, action.character_id)
      if (action.animation) state.characters[action.character_id].animation = action.animation
      return true
    }
    case 'BACKGROUND_SET':
    case 'BACKGROUND_FADE': {
      if (action.background) state.scene.backgroundId = action.background
      return true
    }
    case 'SCREEN_SHAKE':
    case 'SCREEN_GLITCH':
      state.effects = [...state.effects.filter((e) => e !== action.type), action.type]
      return true
    case 'DIALOGUE_FOCUS':
    case 'INPUT_LOCK':
    case 'INPUT_UNLOCK':
      // 对话框/输入焦点由 GameDialog 自身状态处理；此处仅接受，不产生表现变化。
      return true
    default:
      // 未知 Action：拒绝执行并记录（docs/12 §13）
      console.warn(`[presentation-adapter] 未知 presentation action: ${action.type}`)
      return false
  }
}

/** 应用一轮响应的结构化 Presentation Actions（docs/12 §13 主通道）。 */
export function applyPresentationActions(
  state: PresentationState,
  actions: PresentationAction[],
): void {
  for (const action of actions ?? []) {
    applyPresentationAction(state, action)
  }
}

/** 应用权威 presentation_state（GET /api/game/state 对账）。前端展示完全
 * 对账于此 —— 谁在场上、表情如何，由 Backend Narrative 决定（docs/13 §9.2）。
 * 舞台以权威列表为准：不在列表中的角色从在场名单移除（CHARACTER_HIDE 等价）。 */
export function applyPresentationStateView(
  state: PresentationState,
  view: PresentationStateView,
): void {
  if (view.scene) {
    // 当前仓库只有一张背景图（background1.png）；scene 是后端权威事实，但
    // 背景素材按绑定房间处理，避免 ROOM_A 等 scene 映射到不存在的图。
    state.scene.backgroundId = '/backgroud/background1.png'
  }
  const authoritativeIds = new Set<string>()
  for (const c of view.characters ?? []) {
    authoritativeIds.add(c.character_id)
    ensureCharacter(state, c.character_id)
    const target = state.characters[c.character_id]
    target.visible = c.visible
    if (c.emotion) target.emotion = c.emotion
    if (c.slot && SLOT_PCT[c.slot]) target.offsetX = SLOT_PCT[c.slot]
  }
  // 权威在场名单驱动 presentCharacterIds（顺序稳定：按 view.characters 顺序）
  state.presentCharacterIds = (view.characters ?? [])
    .filter((c) => authoritativeIds.has(c.character_id))
    .map((c) => c.character_id)
    .filter((id) => state.characters[id]?.visible)
  // 不在权威列表中的角色退场（fail-closed：宁可少显示，不臆造在场）
  for (const id of Object.keys(state.characters)) {
    if (!authoritativeIds.has(id)) {
      state.characters[id].visible = false
    }
  }
  state.status = view.input_mode === 'locked' ? 'transitioning' : 'idle'
}

/** 一轮 ChatResponse → Store：说话角色 + 台词 + 结构化指令 + 剧本演出行。 */
export function applyChatResponse(
  state: PresentationState,
  data: ChatResponse,
): { presentedCharacter: string | null } {
  // 1. 结构化 Presentation Actions（优先于 legacy 字符串，docs/12 §13）
  let presentedCharacter: string | null = null
  if (data.presentation_actions?.length) {
    applyPresentationActions(state, data.presentation_actions)
    const show = data.presentation_actions.find((a) => a.type === 'CHARACTER_SHOW')
    if (show?.character_id) presentedCharacter = show.character_id
  } else if (data.presentation?.length) {
    // legacy 回退（docs/12 §13：迁移期保留）
    for (const directive of data.presentation) {
      const [kind, ...tokens] = directive.split(/\s+/)
      if (kind === 'SHOW_CHARACTER' && tokens[0]) {
        applyPresentationAction(state, { type: 'CHARACTER_SHOW', character_id: tokens[0] })
        presentedCharacter = tokens[0]
      } else if (kind === 'SET_EMOTION' && tokens[0] && tokens[1]) {
        applyPresentationAction(state, {
          type: 'CHARACTER_EMOTION',
          character_id: tokens[0],
          emotion: tokens[1],
        })
      }
    }
  }
  // 2. 说话角色：若本轮无剧情指令指定焦点，则以实际说话者为准（docs/01 §10.1）。
  ensureCharacter(state, data.character_id)
  if (!presentedCharacter || presentedCharacter === data.character_id) {
    presentedCharacter = data.character_id
  }
  // 3. 说话者表情/动画（docs/02 §7：模型 propose 的 emotion/animation）
  if (data.emotion) state.characters[data.character_id].emotion = data.emotion
  if (data.animation && data.animation !== 'none') {
    state.characters[data.character_id].animation = data.animation
  }
  // 4. 对话状态：当前说话者 + 台词。剧本序列多行时由 GameView 逐行播放。
  state.dialogue = {
    speakerId: data.character_id,
    speakerName: data.character_id,
    text: data.dialogue,
    mode: 'ai',
  }
  return { presentedCharacter }
}

/** 设置对话行（剧本序列逐行播放 / 恢复历史时用）。 */
export function setDialogueLine(
  state: PresentationState,
  speakerId: string,
  text: string,
  emotion?: string | null,
): void {
  ensureCharacter(state, speakerId)
  if (emotion) state.characters[speakerId].emotion = emotion
  state.dialogue = {
    speakerId,
    speakerName: speakerId,
    text,
    mode: 'ai',
  }
}

export function setInputStatus(state: PresentationState, canInput: boolean): void {
  state.status = canInput ? 'idle' : state.status
}
