import { http } from './http'
import { getPlayerId } from './saves'

// 快速上线固定剧本 API（临时）：AI 停用期间前端只用这三个端点推进
// docs/story/07 剧本。后端权威游标（node_index）随会话/存档快照持久化。

export interface StoryLineNode {
  kind: 'line'
  speaker: string
  text: string
  emotion: string | null
  scene_id: string | null
}

export interface StoryOptionView {
  id: string
  label: string
}

export interface StoryChoiceNode {
  kind: 'choice'
  choice_id: string
  scene_id: string | null
  options: StoryOptionView[]
}

export interface StoryEndNode {
  kind: 'end'
  scene_id: string | null
}

export type StoryNode = StoryLineNode | StoryChoiceNode | StoryEndNode

/** 场景演出指令（纯表现，后端权威；docs/17 演出接线） */
export interface StorySceneView {
  scene_id: string
  title: string
  presentation: {
    /** 场景入场脉冲播放的命名效果（SCREEN_GLITCH / SCREEN_SHAKE） */
    effects?: string[]
    /** GameBackground 光照滤镜（如 SC03 暗版 brightness 0.45） */
    lighting?: { background?: { brightness?: number } }
  }
}

export interface StoryView {
  session_id: string
  started: boolean
  finished: boolean
  node: StoryNode | null
  /** 当前节点所属场景（end 节点为 null） */
  scene: StorySceneView | null
  scene_changed: boolean
}

/** 当前展示节点（刷新/读档恢复；不移动游标）。 */
export async function fetchStoryCurrent(sessionId: string | null): Promise<StoryView> {
  const { data } = await http.get<StoryView>('/story/current', {
    params: sessionId ? { session_id: sessionId } : {},
  })
  return data
}

/** 「继续」：移动到下一节点（首次调用即开始故事）。 */
export async function storyAdvance(sessionId: string | null): Promise<StoryView> {
  const { data } = await http.post<StoryView>('/story/advance', {
    session_id: sessionId,
    player_id: getPlayerId(),
  })
  return data
}

/** 提交一个 A/B/C 选项，返回该选项的第一句台词。 */
export async function storyChoose(sessionId: string, optionId: string): Promise<StoryView> {
  const { data } = await http.post<StoryView>('/story/choose', {
    session_id: sessionId,
    option_id: optionId,
    player_id: getPlayerId(),
  })
  return data
}
