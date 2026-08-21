<script setup lang="ts">
// 固定剧本播放器：既有第一章存档与 docs/19 序章共用表现层；剧情选择、
// 剩余角色过滤和汇合条件全部由 Backend Runtime 权威决定。
// docs/story/07-First-Chapter-Script-v2-DeepSeek-Rewrite.md 的临时落地：
// AI 回复停用 —— 无输入框；点「继续」逐行推进（后端 /api/story/advance），
// 选项点弹 A/B/C 窗口（/api/story/choose），SC14 后显示「第一章 完」结局。
// 旧调查玩法（GameView，/game 路由）代码原样保留，只是不再有 UI 入口
//（用户确认「入口隐藏」）。存档/读档/历史/系统菜单复用既有组件；
// 后端场景边界自动写 AUTO 存档。
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useSavesStore } from '../stores/saves'
import { usePresentationStore } from '../stores/presentation'
import { useSettingsStore } from '../stores/settings'
import {
  applyPresentationAction,
  setDialogueLine,
} from '../adapters/presentation-adapter'
import {
  fetchStoryCurrent,
  storyAdvance,
  storyChoose,
} from '../api/story'
import type {
  StoryChapterOpening,
  StoryLineNode,
  StoryOptionView,
  StorySceneView,
  StoryView,
} from '../api/story'
import { saveTargetRoute, type LoadResult } from '../api/saves'
import GameBackground from '../components/game/standard/GameBackground.vue'
import GameRolesStage from '../components/game/standard/GameRolesStage.vue'
import GameDialog from '../components/game/standard/GameDialog.vue'
import StoryChoiceWindow from '../components/game/standard/StoryChoiceWindow.vue'
import StoryEnding from '../components/game/standard/StoryEnding.vue'
import ScreenEffects from '../components/game/standard/ScreenEffects.vue'
import SceneTitleCard from '../components/game/standard/SceneTitleCard.vue'
import ChapterOpening from '../components/game/standard/ChapterOpening.vue'
import SavePanel from '../components/save/SavePanel.vue'
import LoadPanel from '../components/save/LoadPanel.vue'
import SystemMenu from '../components/system/SystemMenu.vue'
import HistoryPanel from '../components/system/HistoryPanel.vue'
import LoadingTransition from '../components/effects/LoadingTransition.vue'
import EyeOpenTransition from '../components/effects/EyeOpenTransition.vue'
import { shouldIgnoreStoryAdvance } from '../utils/story-input'

const presentation = usePresentationStore()
const game = useGameStore()
const saves = useSavesStore()
const settings = useSettingsStore()
const router = useRouter()
const route = useRoute()
const storyId = computed(() => (route.query.story_id === 'prologue' ? 'prologue' : undefined))

const SESSION_KEY = 'gal_session_id'
// docs/19 §4：序章专用常驻背景 background_prologue.png；未带 story_id（第一章
// 恢复）才回落到 background1.png。避免进入序章瞬间闪现无关素材。
const BG = computed(() =>
  storyId.value === 'prologue' ? '/backgroud/background_prologue.png' : '/backgroud/background1.png',
)

// 与 GameView 同约定：viewEpoch 作废切换会话后的在途响应
let viewEpoch = 0
const invalidateView = () => {
  viewEpoch++
}
let loadingShownThisSession = false

const sessionId = ref<string | null>(null)
const busy = ref(false)
const error = ref<string | null>(null)
const node = ref<StoryView['node']>(null)
const finished = ref(false)
const showChoice = ref(false)
const showEnding = ref(false)
const chapterOpening = ref<StoryChapterOpening | null>(null)
const showChapterOpening = ref(false)
let chapterOpeningShown = false

const choiceOptions = ref<StoryOptionView[]>([])
const systemPanel = ref<'menu' | 'save' | 'load' | 'history' | null>(null)
const dialogRef = ref<InstanceType<typeof GameDialog> | null>(null)
let lastWheelAdvanceAt = 0

function storyAdvanceBlocked(): boolean {
  return Boolean(
    busy.value ||
      systemPanel.value ||
      showChoice.value ||
      showEnding.value ||
      showChapterOpening.value ||
      showLoading.value ||
      showEyeOpen.value,
  )
}

function triggerStoryAdvance() {
  if (storyAdvanceBlocked()) return
  dialogRef.value?.triggerAdvance()
}

function onStageClick(event: MouseEvent) {
  if (shouldIgnoreStoryAdvance(event.target)) return
  triggerStoryAdvance()
}

function onStageWheel(event: WheelEvent) {
  if (shouldIgnoreStoryAdvance(event.target) || storyAdvanceBlocked()) return
  if (event.deltaY < 0) {
    event.preventDefault()
    systemPanel.value = 'history'
    return
  }
  if (event.deltaY === 0) return
  event.preventDefault()
  const now = performance.now()
  if (now - lastWheelAdvanceAt < 160) return
  lastWheelAdvanceAt = now
  triggerStoryAdvance()
}

function onStoryKeyDown(event: KeyboardEvent) {
  if (event.code !== 'Space' || event.repeat || shouldIgnoreStoryAdvance(event.target)) return
  if (storyAdvanceBlocked()) return
  event.preventDefault()
  triggerStoryAdvance()
}

// ── 场景演出接线（docs/17）───────────────────────────────────────────────
const sceneView = ref<StorySceneView | null>(null)
const showTitleCard = ref(false)
let titleCardKey = 0
let effectTimer: ReturnType<typeof setTimeout> | null = null

// 光照随场景常驻；入场效果（glitch/shake）脉冲播放；标题卡在场景切换时淡入淡出。
function applyScene(scene: StorySceneView | null, changed: boolean) {
  sceneView.value = scene
  presentation.state.scene.backgroundId = scene?.presentation?.background ?? BG.value
  presentation.state.scene.lighting = scene?.presentation?.lighting ?? undefined
  const authoritativeCharacters = scene?.presentation?.characters
  if (authoritativeCharacters) {
    for (const characterId of [...presentation.state.presentCharacterIds]) {
      applyPresentationAction(presentation.state, {
        type: 'CHARACTER_HIDE',
        character_id: characterId,
      })
    }
    for (const character of authoritativeCharacters) {
      applyPresentationAction(presentation.state, {
        type: 'CHARACTER_SHOW',
        character_id: character.character_id,
        emotion: character.emotion,
        slot: character.slot,
      })
      if (character.scale != null) {
        applyPresentationAction(presentation.state, {
          type: 'CHARACTER_EMOTION',
          character_id: character.character_id,
          scale: character.scale,
          offset_y: character.offset_y,
        })
      }
    }
  }
  if (changed) {
    const fx = scene?.presentation?.effects ?? []
    if (effectTimer) {
      clearTimeout(effectTimer)
      effectTimer = null
    }
    presentation.state.effects = fx
    if (fx.length > 0) {
      effectTimer = setTimeout(() => {
        presentation.state.effects = []
      }, 2600)
    }
    if (scene?.title) {
      titleCardKey++
      showTitleCard.value = true
    }
  }
}

function roleNameOf(id: string): string {
  const names: Record<string, string> = {
    deepseek: 'DeepSeek',
    claude: 'Claude',
    chatgpt: 'ChatGPT',
    doubao: '豆包',
    system: '系统',
    player: '我',
  }
  return names[id] ?? id
}

// 说话的角色即登台（台词本身是后端下发的权威剧本内容）；system/player 不登台。
function presentSpeaker(speaker: string, emotion: string | null) {
  if (speaker === 'system' || speaker === 'player') return
  applyPresentationAction(presentation.state, {
    type: 'CHARACTER_SHOW',
    character_id: speaker,
    emotion: emotion ?? undefined,
  })
}

function showLine(line: StoryLineNode) {
  presentSpeaker(line.speaker, line.emotion)
  setDialogueLine(presentation.state, line.speaker, line.text, line.emotion)
  presentation.state.dialogue.speakerName = roleNameOf(line.speaker)
  // status 'streaming' = responding：GameDialog 显示台词 + 「▼ 继续」；
  // 故事模式永远不进入 input 态（AI 停用，无输入框）。
  presentation.state.status = 'streaming'
}

function applyView(data: StoryView) {
  finished.value = data.finished
  node.value = data.node
  applyScene(data.scene, data.scene_changed)
  if (!chapterOpeningShown && data.chapter_opening) {
    chapterOpeningShown = true
    chapterOpening.value = data.chapter_opening
    showChapterOpening.value = true
  }
  if (!data.node) return
  if (data.node.kind === 'line') {
    showLine(data.node)
  } else if (data.node.kind === 'choice') {
    choiceOptions.value = data.node.options
    showChoice.value = true
  } else if (data.node.kind === 'end') {
    showEnding.value = true
  } else if (data.node.kind === 'chat') {
    void router.push({ path: '/game', query: { character: data.node.character_id } })
  }
}

async function doAdvance() {
  if (busy.value || showChoice.value || showEnding.value || showChapterOpening.value) return
  busy.value = true
  error.value = null
  const epoch = viewEpoch
  try {
    const data = await storyAdvance(sessionId.value, storyId.value)
    if (epoch !== viewEpoch) return
    sessionId.value = data.session_id
    localStorage.setItem(SESSION_KEY, data.session_id)
    applyView(data)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

async function onChoose(optionId: string) {
  if (!sessionId.value || busy.value) return
  busy.value = true
  error.value = null
  showChoice.value = false
  const epoch = viewEpoch
  try {
    const data = await storyChoose(sessionId.value, optionId, storyId.value)
    if (epoch !== viewEpoch) return
    applyView(data)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    showChoice.value = true
  } finally {
    busy.value = false
  }
}

// 台词播完点「继续」→ 取下一节点
function onDialogProceed() {
  if (showChoice.value || showEnding.value || showChapterOpening.value) return
  void doAdvance()
}

// ── 会话恢复 / 新游戏 ──────────────────────────────────────────────────────

async function fetchCurrentAndApply() {
  const data = await fetchStoryCurrent(sessionId.value, storyId.value)
  sessionId.value = data.session_id
  localStorage.setItem(SESSION_KEY, data.session_id)
  if (!data.started) {
    // 旧调查玩法存档（无 story_cursor）载入后从头开始故事
    await doAdvance()
    return
  }
  applyView(data)
}

// 新游戏路径：首次加载演出（docs/15 §7，与 GameView 同约定）
const showLoading = ref(false)
const openingReady = ref(false)
const bufferedFirst = ref<StoryView | null>(null)

async function startStory() {
  const epoch = viewEpoch
  try {
    const data = await storyAdvance(sessionId.value, storyId.value)
    if (epoch !== viewEpoch) return
    sessionId.value = data.session_id
    localStorage.setItem(SESSION_KEY, data.session_id)
    if (showLoading.value) {
      bufferedFirst.value = data
      openingReady.value = true
      return
    }
    applyView(data)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    if (showLoading.value) openingReady.value = true
  }
}

function onLoadingComplete() {
  showLoading.value = false
  loadingShownThisSession = true
  const buffered = bufferedFirst.value
  bufferedFirst.value = null
  if (buffered) applyView(buffered)
  armEyeOpen()
}

// 睁眼转场（docs/16 P5，与 GameView 同约定）
const prefersReducedMotion =
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches
const showEyeOpen = ref(false)
function armEyeOpen() {
  if (settings.eyeOpenTransitionEnabled && !prefersReducedMotion) {
    showEyeOpen.value = true
  }
}

// ── 游戏内读档 ─────────────────────────────────────────────────────────────

const loadBusy = ref(false)

async function onLoadFromGame(saveId: string) {
  if (loadBusy.value || busy.value) return
  loadBusy.value = true
  error.value = null
  try {
    const result = await saves.load(saveId)
    applyLoadedSession(result)
    systemPanel.value = null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loadBusy.value = false
  }
}

function applyLoadedSession(result: LoadResult) {
  invalidateView()
  sessionId.value = result.session_id
  localStorage.setItem(SESSION_KEY, result.session_id)
  showChoice.value = false
  showEnding.value = false
  const target = saveTargetRoute(result.story_cursor, result.story_finished)
  const currentTarget = storyId.value === 'prologue' ? '/story?story_id=prologue' : '/story'
  if (target !== currentTarget) {
    game.pendingLoad = result
    void router.push(target)
    return
  }
  game.pendingLoad = null
  void fetchCurrentAndApply()
}

// ── 挂载 ───────────────────────────────────────────────────────────────────

onMounted(async () => {
  window.addEventListener('keydown', onStoryKeyDown)
  presentation.state.scene.backgroundId = BG.value
  // 0. 优先消费 Load 结果（docs/13 §20.3：Title/Load 页暂存的新 Active Session）
  if (game.pendingLoad) {
    applyLoadedSession(game.pendingLoad)
    armEyeOpen()
    return
  }
  // 0.5 首次加载演出：仅无存量会话的新游戏入口
  if (
    !localStorage.getItem(SESSION_KEY) &&
    settings.loadingTransitionEnabled &&
    !loadingShownThisSession
  ) {
    showLoading.value = true
  }
  // 1. 恢复已有会话（刷新后 Session restore）
  const stored = localStorage.getItem(SESSION_KEY)
  if (stored) {
    sessionId.value = stored
    try {
      await fetchCurrentAndApply()
      armEyeOpen()
      return
    } catch (e) {
      console.warn('[StoryView] restore session failed, starting new', e)
      localStorage.removeItem(SESSION_KEY)
      sessionId.value = null
    }
  }
  // 2. 新会话 → 开始故事
  await startStory()
  if (!showLoading.value) armEyeOpen()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onStoryKeyDown)
  invalidateView()
  if (effectTimer) {
    clearTimeout(effectTimer)
    effectTimer = null
  }
})

// 结局 → 自由聊天：复用同一会话进入 /game（AI 回复，docs/17）
function onContinueChat() {
  showEnding.value = false
  router.push('/game')
}
</script>

<template>
  <div
    class="relative h-full w-full overflow-hidden bg-black"
    :class="{ 'screen-shake': presentation.state.effects.includes('SCREEN_SHAKE') }"
    @click="onStageClick"
    @wheel="onStageWheel"
  >
    <!-- 背景 -->
    <GameBackground />

    <!-- 角色舞台 -->
    <GameRolesStage class="pointer-events-none absolute inset-0 z-1" />

    <!-- 屏幕故障特效层（SCREEN_GLITCH 脉冲） -->
    <ScreenEffects :effects="presentation.state.effects" />

    <!-- 场景标题卡（场景切换时淡入淡出） -->
    <SceneTitleCard
      v-if="showTitleCard"
      :key="titleCardKey"
      :title="sceneView?.title ?? ''"
      @complete="showTitleCard = false"
    />

    <!-- 每次进入章节播放一次；文字与首场景背景均由后端权威下发。 -->
    <ChapterOpening
      v-if="showChapterOpening && chapterOpening"
      :chapter-label="chapterOpening.chapter_label"
      :title="chapterOpening.title"
      :background="chapterOpening.background"
      @complete="showChapterOpening = false"
    />

    <!-- 对话框（底部） -->
    <div class="absolute inset-x-0 bottom-0 z-10 flex flex-col">
      <GameDialog ref="dialogRef" class="mx-auto" @dialog-proceed="onDialogProceed" />
    </div>

    <!-- 顶部条：会话信息 + 系统菜单 + 返回标题 -->
    <header class="absolute left-0 top-0 z-20 flex items-center gap-3 px-4 py-2 text-sm text-[#d7effa]/70">
      <span
        v-if="sessionId"
        class="rounded-full border border-white/10 bg-black/40 px-3 py-1 text-xs text-[#a9e8ff]/85 backdrop-blur-sm"
      >
        会话 {{ sessionId.slice(0, 8) }}…
      </span>
      <span v-else class="rounded-full border border-white/10 bg-black/40 px-3 py-1 text-xs text-[#a9e8ff]/85 backdrop-blur-sm">
        未连接
      </span>
      <span v-if="error" class="ml-3 text-red-300">{{ error }}</span>
      <div class="ml-auto flex items-center gap-2">
        <button
          class="rounded-full border border-white/15 bg-black/40 px-3 py-1 text-xs text-[#d7effa]/85 backdrop-blur-sm transition-colors hover:bg-white/10"
          @click="systemPanel = 'menu'"
        >
          系统菜单
        </button>
        <button
          class="rounded-full border border-white/15 bg-black/40 px-3 py-1 text-xs text-[#d7effa]/85 backdrop-blur-sm transition-colors hover:bg-white/10"
          @click="router.push('/')"
        >
          返回标题
        </button>
      </div>
    </header>

    <!-- 面板打开时的场景模糊层 -->
    <div
      v-if="systemPanel && systemPanel !== 'history'"
      class="pointer-events-none fixed inset-0 z-[25] bg-black/20 backdrop-blur-[6px]"
    ></div>

    <!-- 系统菜单 / 面板（docs/13 §13） -->
    <SystemMenu v-if="systemPanel === 'menu'" @open="systemPanel = $event" @close="systemPanel = null" />
    <SavePanel
      v-if="systemPanel === 'save'"
      :session-id="sessionId ?? ''"
      :busy="busy"
      @close="systemPanel = null"
    />
    <LoadPanel
      v-if="systemPanel === 'load'"
      :busy="busy || loadBusy"
      @load="onLoadFromGame"
      @close="systemPanel = null"
    />
    <HistoryPanel
      v-if="systemPanel === 'history'"
      :session-id="sessionId"
      @close="systemPanel = null"
    />

    <!-- 剧本选项窗口（A/B/C，必须选择） -->
    <StoryChoiceWindow
      v-if="showChoice"
      :options="choiceOptions"
      :busy="busy"
      @select="onChoose"
    />

    <!-- 结局画面 -->
    <StoryEnding v-if="showEnding" @return-title="router.push('/')" @continue-chat="onContinueChat" />

    <!-- 首次加载演出（docs/15 §7：New Game 专用） -->
    <LoadingTransition v-if="showLoading" :ready="openingReady" @complete="onLoadingComplete" />

    <!-- 睁眼转场（docs/16 P5） -->
    <EyeOpenTransition v-if="showEyeOpen" @complete="showEyeOpen = false" />
  </div>
</template>
