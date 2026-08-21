import { http } from './http'

// 固定剧本 API：未传 story_id 时恢复既有 docs/story/07 第一章；
// story_id=prologue 时推进 docs/story/Prologue.md 的无序探班流程（docs/19）。
// 两者的后端权威游标均随会话/存档快照持久化。

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

export interface StoryChatNode {
  kind: 'chat'
  character_id: string
  scene_id: string | null
}

export type StoryNode = StoryLineNode | StoryChoiceNode | StoryEndNode | StoryChatNode

/** 场景演出指令（纯表现，后端权威；docs/17 演出接线） */
export interface StorySceneView {
  scene_id: string
  title: string
  presentation: {
    /** 场景入场脉冲播放的命名效果（SCREEN_GLITCH / SCREEN_SHAKE） */
    effects?: string[]
    /** GameBackground 光照滤镜（如 SC03 暗版 brightness 0.45） */
    lighting?: { background?: { brightness?: number } }
    /** 场景背景与权威在场角色（docs/19 序章）。 */
    background?: string
    characters?: Array<{
      character_id: string
      emotion: string
      slot?: string | null
      scale?: number
      offset_y?: number
    }>
  }
}

export interface StoryChapterOpening {
  chapter_label: string
  title: string
  /** 永远是章节首场景背景，不随当前恢复场景改变。 */
  background: string
}

export interface StoryView {
  session_id: string
  started: boolean
  finished: boolean
  node: StoryNode | null
  /** 当前节点所属场景（end 节点为 null） */
  scene: StorySceneView | null
  scene_changed: boolean
  chapter_opening: StoryChapterOpening
}

/** 当前展示节点（刷新/读档恢复；不移动游标）。 */
export async function fetchStoryCurrent(
  sessionId: string | null,
  storyId?: string,
): Promise<StoryView> {
  const { data } = await http.get<StoryView>('/story/current', {
    params: {
      ...(sessionId ? { session_id: sessionId } : {}),
      ...(storyId ? { story_id: storyId } : {}),
    },
  })
  return data
}

/** 「继续」：移动到下一节点（首次调用即开始故事）。 */
export async function storyAdvance(sessionId: string | null, storyId?: string): Promise<StoryView> {
  const { data } = await http.post<StoryView>('/story/advance', {
    session_id: sessionId,
    story_id: storyId ?? null,
  })
  return data
}

/** 提交一个 A/B/C 选项，返回该选项的第一句台词。 */
export async function storyChoose(
  sessionId: string,
  optionId: string,
  storyId?: string,
): Promise<StoryView> {
  const { data } = await http.post<StoryView>('/story/choose', {
    session_id: sessionId,
    option_id: optionId,
    story_id: storyId ?? null,
  })
  return data
}
