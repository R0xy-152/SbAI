<script setup lang="ts">
// 第一章 · 角色舞台（docs/13 Task 4）：接入现有 FastAPI Game Runtime。
// New Session → Player Input → Response → Presentation Directive → Character
// Presence → Emotion → Narrative Event。03:17 经「调查纸（EV01）」触发，
// Claude 由后端 CH01_INCIDENT_0317 脚本登场，随后可对话。
// 所有展示变化来自 Backend presentation_actions / presentation_state，前端不
// 从剧情条件推断角色在场（docs/13 §9.2）。
// Task 7：游戏内系统菜单（§13 Save/Load/History/Return Title）+ Load 消费
//（§20.3：game.pendingLoad 在挂载时恢复新 Session）。
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useSavesStore } from '../stores/saves'
import { usePresentationStore } from '../stores/presentation'
import {
  applyChatResponse,
  applyPresentationStateView,
  setDialogueLine,
} from '../adapters/presentation-adapter'
import {
  createOpening,
  fetchGameState,
  fetchHistory,
  sendChat,
  sendInvestigationAction,
} from '../api/game'
import type { ChatResponse, GameOption } from '../api/game'
import type { LoadResult } from '../api/saves'
import GameBackground from '../components/game/standard/GameBackground.vue'
import GameRolesStage from '../components/game/standard/GameRolesStage.vue'
import GameDialog from '../components/game/standard/GameDialog.vue'
import SavePanel from '../components/save/SavePanel.vue'
import LoadPanel from '../components/save/LoadPanel.vue'
import SystemMenu from '../components/system/SystemMenu.vue'
import HistoryPanel from '../components/system/HistoryPanel.vue'
import OptionsPanel from '../components/game/standard/OptionsPanel.vue'

const presentation = usePresentationStore()
const game = useGameStore()
const saves = useSavesStore()
const router = useRouter()

const SESSION_KEY = 'gal_session_id'
const BG = '/backgroud/background1.png'

// 无角色切换器：玩家发言是公共对话（后端 _public_audience 记录 heard_by =
// 全体在场角色，docs/13 §9.2），回应者由后端 SpeakerSelector 权威决定；
// 交互选择 / 私审 / 关键剧情节点经「选项功能」实现（见 docs/14 计划）。

const sessionId = ref<string | null>(null)
const canInput = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const currentResponse = ref<ChatResponse | null>(null)

// 剧本序列逐行播放队列（03:17 / GPT / 豆包 / FINAL_REVEAL 等多行演出）
const scriptQueue = ref<ChatResponse['script_sequence']>([])
let scriptIndex = 0

// 系统菜单 / 面板（docs/13 §13）。systemPanel 表示当前打开的面板：
// null 无，'menu' 系统菜单，'save'/'load'/'history' 对应面板。
const systemPanel = ref<'menu' | 'save' | 'load' | 'history' | null>(null)

// LLM 中间态（docs/13 §22）：thinking/streaming 时手动 Save / Load 禁用。
const llmBusy = computed(() =>
  ['thinking', 'streaming'].includes(presentation.state.status),
)

function roleNameOf(id: string): string {
  const names: Record<string, string> = {
    deepseek: 'DeepSeek',
    claude: 'Claude',
    chatgpt: 'ChatGPT',
    doubao: '豆包',
    system: '系统',
  }
  return names[id] ?? id
}

function setSpeakerLine(speaker: string, text: string, emotion?: string | null) {
  setDialogueLine(presentation.state, speaker, text, emotion)
  presentation.state.dialogue.speakerName = roleNameOf(speaker)
}

// 输入可用性由 dialogue.mode 表达（GameDialog 的 currentStatus 依赖它）：
// mode 'ai' → responding（只读 + 打字机）；否则 input（可输入）。
function setInputMode(canType: boolean) {
  canInput.value = canType
  presentation.state.dialogue.mode = canType ? 'script' : 'ai'
  presentation.state.status = canType ? 'idle' : 'thinking'
}

// 对账权威角色在场（docs/12 §39 Task 1）：每次响应/调查后调用。
async function reconcileStage() {
  if (!sessionId.value) return
  try {
    const state = await fetchGameState(sessionId.value)
    applyPresentationStateView(presentation.state, state.presentation_state)
    options.value = state.options ?? []
    // 粘性路由自动复位（D5）：路由对象离场 → 对应 chat_routing 选项消失
    if (routedCharacter.value) {
      const stillRoutable = options.value.some(
        (o) =>
          o.kind === 'chat_routing' &&
          o.payload?.character_id === routedCharacter.value,
      )
      if (!stillRoutable) routedCharacter.value = null
    }
  } catch (e) {
    console.warn('[GameView] reconcile stage failed', e)
  }
}

// 播放剧本序列（逐行打字机推进；多角色演出由后端 script_sequence 下发）
function playNextScriptLine(): boolean {
  if (scriptIndex >= scriptQueue.value.length) {
    scriptQueue.value = []
    scriptIndex = 0
    return false
  }
  const line = scriptQueue.value[scriptIndex]
  scriptIndex++
  setSpeakerLine(line.speaker, line.dialogue, line.emotion)
  presentation.state.status = 'streaming'
  return true
}

// 玩家发送
async function onPlayerMessage(text?: unknown) {
  if (!sessionId.value || typeof text !== 'string' || !text.trim() || busy.value) return
  busy.value = true
  error.value = null
  // 进入 AI 回复态前清空旧台词：GameDialog 的 watch 依赖 dialogue.text +
  // currentStatus 触发打字机，若留着上一句会先把旧台词重打一遍。
  presentation.state.dialogue.text = ''
  setInputMode(false)
  try {
    const data = await sendChat(sessionId.value, text.trim(), routedCharacter.value ?? undefined)
    currentResponse.value = data
    // 结构化指令 → 舞台（CHARACTER_SHOW / EMOTION / GLITCH 等）
    applyChatResponse(presentation.state, data)
    presentation.state.dialogue.speakerName = roleNameOf(data.character_id)
    scriptQueue.value = data.script_sequence ?? []
    scriptIndex = 0
    // 主台词（若有剧本序列，主台词后仍依次播放序列）
    if (!data.dialogue) {
      playNextScriptLine()
    } else {
      presentation.state.status = 'streaming'
    }
    await reconcileStage()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    setInputMode(true)
  } finally {
    busy.value = false
  }
}

// 打字机完成（dialog-proceed）→ 推进下一句剧本序列；播完解锁输入
let pendingOpeningAdvance = false
function onDialogProceed() {
  if (pendingOpeningAdvance) {
    pendingOpeningAdvance = false
    setInputMode(true)
    return
  }
  if (scriptQueue.value.length > 0 && scriptIndex < scriptQueue.value.length) {
    playNextScriptLine()
  } else {
    scriptQueue.value = []
    scriptIndex = 0
    setInputMode(true)
  }
}

// 选项功能（docs/14 T2）：后端权威下发当前合法选项（D3），前端只回传
// payload（D7）。investigate 逐步骤执行 payload.steps；chat_routing 是粘性
// 路由（用户确认：再点同一气泡取消；角色离场自动复位，见 reconcileStage）。
const options = ref<GameOption[]>([])
const optionBusy = ref(false)
const feedback = ref<string | null>(null)
const routedCharacter = ref<string | null>(null)

const routeLabel = computed(() => {
  if (!routedCharacter.value) return null
  return `正在与 ${roleNameOf(routedCharacter.value)} 对话：再点同一气泡回到公共对话`
})

async function executeOption(option: GameOption) {
  if (!sessionId.value || optionBusy.value || llmBusy.value) return
  feedback.value = null
  // D5 对话路由：仅本地切换目标，下一条玩家消息经 sendChat 透传 character_id
  if (option.kind === 'chat_routing') {
    const cid = option.payload?.character_id
    if (typeof cid === 'string') {
      routedCharacter.value = routedCharacter.value === cid ? null : cid
    }
    return
  }
  // investigate：payload.steps 逐条执行既有权威端点（/api/game/action）
  if (option.kind === 'investigate') {
    optionBusy.value = true
    try {
      const steps = Array.isArray(option.payload?.steps) ? option.payload.steps : []
      let last: Awaited<ReturnType<typeof sendInvestigationAction>> | null = null
      for (const step of steps) {
        const action = (step as { action?: unknown })?.action
        const hotspotId = (step as { hotspot_id?: unknown })?.hotspot_id
        if (typeof action !== 'string' || typeof hotspotId !== 'string') continue
        last = await sendInvestigationAction(
          sessionId.value,
          action as 'INSPECT_HOTSPOT' | 'PAPER_RUBBING_COMPLETE',
          hotspotId,
        )
        if (last.state?.presentation_state) {
          applyPresentationStateView(presentation.state, last.state.presentation_state)
        }
      }
      // 先对账（选项随热点完成而消失，D3），再给反馈，避免测试先看到文案
      await reconcileStage()
      if (last) {
        feedback.value =
          last.outcome === 'ALREADY_COMPLETED'
            ? '已经调查过了。'
            : last.evidence_id
              ? '调查完成，获得新线索。'
              : '调查完成。'
      }
    } catch (e) {
      feedback.value = e instanceof Error ? e.message : '调查失败，请重试。'
    } finally {
      optionBusy.value = false
    }
    return
  }
  // 其余 kind（evidence_present / deduction / private_interview / recovery /
  // narrative）为 T3/T4 预留：后端届时才下发，当前不处理（D7）。
}

async function startOpening() {
  try {
    const opening = await createOpening(sessionId.value)
    sessionId.value = opening.session_id
    localStorage.setItem(SESSION_KEY, opening.session_id)
    if (opening.dialogue) {
      setSpeakerLine(opening.character_id, opening.dialogue, opening.emotion)
      presentation.state.status = 'streaming'
      // 初始场景背景（binding_room → background1）；后续由 reconcileStage 对账
      presentation.state.scene.backgroundId = BG
      // opening 角色（DeepSeek）已在场
      presentation.state.presentCharacterIds = ['deepseek']
      presentation.state.characters['deepseek'] = {
        ...presentation.state.characters['deepseek'],
        visible: true,
        emotion: opening.emotion || 'neutral',
      }
      // opening 是开场演出：播放中不可输入（dialogue.mode 已由 setSpeakerLine
      // 置为 'ai'，status 'streaming' 即 responding；勿再调用 setInputMode(false)，
      // 其会把 status 覆盖为 thinking 使打字机永远不启动），玩家点击推进后解锁
      pendingOpeningAdvance = true
    } else {
      setInputMode(true)
    }
    // 初始选项（调查纸等）由后端权威 options 决定（docs/14 T2，D3）
    void reconcileStage()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    setInputMode(true)
  }
}

// 游戏内 Load（docs/13 §20.3）：Backend 创建新 Active Session，返回
// GameViewState；此处就地恢复（applyLoadedSession），不离开 GameView。
const loadBusy = ref(false)

async function onLoadFromGame(saveId: string) {
  if (loadBusy.value || llmBusy.value) return
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

// Load 消费（docs/13 §20.3 / §19.1）：Backend 已创建新 Active Session 并
// 返回 initial GameViewState；此处就地渲染，不重新走 Opening。
function applyLoadedSession(result: LoadResult) {
  sessionId.value = result.session_id
  localStorage.setItem(SESSION_KEY, result.session_id)
  const view = result.state?.presentation_state
  if (view) {
    applyPresentationStateView(presentation.state, view)
  }
  options.value = result.state?.options ?? []
  // 新 Active Session：本地粘性路由状态不复用
  routedCharacter.value = null
  // 恢复最后一句角色台词（画面回到对话流，docs/13 §19.2 restore order 末端）
  const messages = result.history?.messages ?? []
  const lastCharacter = [...messages]
    .reverse()
    .find((m) => m.role === 'character' && m.content)
  if (lastCharacter && lastCharacter.character_id) {
    setSpeakerLine(lastCharacter.character_id, lastCharacter.content)
    // status 'streaming' 即 responding：勿再 setInputMode(false)（会覆盖为
    // thinking 使恢复的最后一句台词永远不打字）
    presentation.state.status = 'streaming'
  } else {
    setInputMode(true)
  }
  game.pendingLoad = null
}

onMounted(async () => {
  // 0. 优先消费 Load 结果（docs/13 §20.3：LoadView/TitleView 暂存的 new
  // Active Session + GameViewState）
  if (game.pendingLoad) {
    applyLoadedSession(game.pendingLoad)
    return
  }
  // 1. 恢复已有会话（localStorage）—— refresh 后 Session restore（docs/13 §27）
  const stored = localStorage.getItem(SESSION_KEY)
  if (stored) {
    sessionId.value = stored
    try {
      await reconcileStage()
      // 恢复最后一句角色台词（docs/13 §27：Session restore 后画面回到对话流）
      const history = await fetchHistory(stored)
      const lastCharacter = [...history.messages]
        .reverse()
        .find((m) => m.role === 'character' && m.content)
      if (lastCharacter && lastCharacter.character_id) {
        setSpeakerLine(lastCharacter.character_id, lastCharacter.content)
        // 同上：status 'streaming' 即 responding，勿覆盖为 thinking
        presentation.state.status = 'streaming'
      } else {
        setInputMode(true)
      }
      return
    } catch (e) {
      // 会话未知/已失效 → 视为新开
      console.warn('[GameView] restore session failed, starting new', e)
      localStorage.removeItem(SESSION_KEY)
      sessionId.value = null
    }
  }
  // 2. 新会话 → Opening
  await startOpening()
})

onUnmounted(() => {
  // 无清理：会话持久化由后端完成
})
</script>

<template>
  <div class="relative h-full w-full overflow-hidden bg-black">
    <!-- 背景 -->
    <GameBackground />

    <!-- 角色舞台 -->
    <GameRolesStage class="pointer-events-none absolute inset-0 z-1" />

    <!-- 对话框（底部）+ 选项气泡条（docs/14 §2.2：选项在对话框上方，D6；
         选项由后端权威下发，可调查性不再由前端 hotspot 推断） -->
    <div class="absolute inset-x-0 bottom-0 z-10 flex flex-col">
      <OptionsPanel
        :options="options"
        :busy="optionBusy || llmBusy"
        :feedback="feedback"
        :route-label="routeLabel"
        :active-route-id="routedCharacter ? 'chat_routing:' + routedCharacter : null"
        @select="executeOption"
      />
      <GameDialog
        class="mx-auto"
        @player-continued="onPlayerMessage"
        @dialog-proceed="onDialogProceed"
      />
    </div>

    <!-- 顶部条：会话信息 + 系统菜单 + 返回标题（docs/13 §13 / Task 5） -->
    <header class="absolute left-0 top-0 z-20 flex items-center gap-3 px-4 py-2 text-sm text-[#d7effa]/70">
      <span v-if="sessionId">会话 {{ sessionId.slice(0, 8) }}…</span>
      <span v-else>未连接</span>
      <span v-if="error" class="ml-3 text-red-300">{{ error }}</span>
      <div class="ml-auto flex items-center gap-2">
        <button
          class="rounded border border-white/15 px-2 py-1 text-xs text-[#d7effa]/80 hover:bg-white/10"
          @click="systemPanel = 'menu'"
        >
          系统菜单
        </button>
        <button
          class="rounded border border-white/15 px-2 py-1 text-xs text-[#d7effa]/80 hover:bg-white/10"
          @click="router.push('/')"
        >
          返回标题
        </button>
      </div>
    </header>

    <!-- 系统菜单 / 面板（docs/13 §13；Save/Load 在 LLM 中间态禁用 §22） -->
    <SystemMenu v-if="systemPanel === 'menu'" @open="systemPanel = $event" @close="systemPanel = null" />
    <SavePanel
      v-if="systemPanel === 'save'"
      :session-id="sessionId ?? ''"
      :busy="llmBusy"
      @close="systemPanel = null"
    />
    <LoadPanel
      v-if="systemPanel === 'load'"
      :busy="llmBusy || loadBusy"
      @load="onLoadFromGame"
      @close="systemPanel = null"
    />
    <HistoryPanel
      v-if="systemPanel === 'history'"
      :session-id="sessionId"
      @close="systemPanel = null"
    />
  </div>
</template>
