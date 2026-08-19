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
  presentEvidence,
  recoveryAction,
  securityReviewCleanup,
  securityReviewRejectCleanup,
  securityReviewStart,
  securityReviewTestify,
  sendChat,
  sendInvestigationAction,
  startRecovery,
  submitDeduction,
  submitPrivateInterviewChallenge,
} from '../api/game'
import type { ChatResponse, GameOption, OpeningResponse, PresentationAction } from '../api/game'
import type { LoadResult } from '../api/saves'
import GameBackground from '../components/game/standard/GameBackground.vue'
import GameRolesStage from '../components/game/standard/GameRolesStage.vue'
import GameDialog from '../components/game/standard/GameDialog.vue'
import SavePanel from '../components/save/SavePanel.vue'
import LoadPanel from '../components/save/LoadPanel.vue'
import SystemMenu from '../components/system/SystemMenu.vue'
import HistoryPanel from '../components/system/HistoryPanel.vue'
import OptionsPanel from '../components/game/standard/OptionsPanel.vue'
import SubActionPanel from '../components/game/standard/SubActionPanel.vue'
import LoadingTransition from '../components/effects/LoadingTransition.vue'
import { useSettingsStore } from '../stores/settings'

const presentation = usePresentationStore()
const game = useGameStore()
const saves = useSavesStore()
const settings = useSettingsStore()
const router = useRouter()

const SESSION_KEY = 'gal_session_id'
const BG = '/backgroud/background1.png'

// docs/15 §7：首次加载演出仅「New Game」路径显示，且同一页面会话只播一次。
let loadingShownThisSession = false

// T2review P1-7：请求 fencing——viewEpoch 标识当前画面会话代次；任何 await
// 返回后若 epoch 已变（Load / New Game / 卸载），丢弃响应，不再写入 Pinia。
let viewEpoch = 0
const invalidateView = () => {
  viewEpoch++
}

// 无角色切换器：玩家发言是公共对话（后端 _public_audience 记录 heard_by =
// 全体在场角色，docs/13 §9.2），回应者由后端 SpeakerSelector 权威决定；
// 交互选择 / 私审 / 关键剧情节点经「选项功能」实现（见 docs/14 计划）。

const sessionId = ref<string | null>(null)
const canInput = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const currentResponse = ref<ChatResponse | null>(null)

// docs/15 §7：New Game 的 opening 响应在加载演出结束前先缓冲，避免打字机在
// 遮罩后提前播放（LingChat 用 eventQueue 暂停，本项目改为缓冲应用）。
const showLoading = ref(false)
const openingReady = ref(false)
const bufferedOpening = ref<OpeningResponse | null>(null)

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
  const epoch = viewEpoch
  try {
    const state = await fetchGameState(sessionId.value)
    if (epoch !== viewEpoch) return
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
  // D2 一次性推理模式：下一条消息提交推理端点而非对话（判定仍走后端）
  if (pendingDeduction.value) {
    await submitPlayerDeduction(text.trim())
    return
  }
  busy.value = true
  error.value = null
  const epoch = viewEpoch
  // 进入 AI 回复态前清空旧台词：GameDialog 的 watch 依赖 dialogue.text +
  // currentStatus 触发打字机，若留着上一句会先把旧台词重打一遍。
  presentation.state.dialogue.text = ''
  setInputMode(false)
  try {
    const data = await sendChat(sessionId.value, text.trim(), routedCharacter.value ?? undefined)
    if (epoch !== viewEpoch) return
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

// 选项功能（docs/14 T2/T3）：后端权威下发当前合法选项（D3），前端只回传
// payload（D7）。investigate 逐步骤执行 payload.steps；chat_routing 是粘性
// 路由（用户确认：再点同一气泡取消；角色离场自动复位，见 reconcileStage）；
// deduction 是引导式提示 + 主输入框一次性推理模式（D2，判定仍走既有端点）；
// evidence_present / private_interview 弹小面板（D6），组装后回传既有端点。
const options = ref<GameOption[]>([])
const optionBusy = ref(false)
const feedback = ref<string | null>(null)
const routedCharacter = ref<string | null>(null)

// D2 一次性推理模式：非空时下一条主输入框消息提交到 /api/game/deduction
const pendingDeduction = ref<GameOption | null>(null)
// D6 小面板：当前打开需要上下文的选项（evidence_present / private_interview）
const activePanel = ref<GameOption | null>(null)
const panelBusy = ref(false)
const panelMessage = ref<string | null>(null)

const routeLabel = computed(() => {
  if (!routedCharacter.value) return null
  return `正在与 ${roleNameOf(routedCharacter.value)} 对话：再点同一气泡回到公共对话`
})

async function executeOption(option: GameOption) {
  if (!sessionId.value || optionBusy.value || llmBusy.value) return
  feedback.value = null
  // 点其它选项会退出推理模式 / 面板状态，避免通道混淆
  if (option.kind !== 'deduction') pendingDeduction.value = null
  // D5 对话路由：仅本地切换目标，下一条玩家消息经 sendChat 透传 character_id
  if (option.kind === 'chat_routing') {
    const cid = option.payload?.character_id
    if (typeof cid === 'string') {
      routedCharacter.value = routedCharacter.value === cid ? null : cid
    }
    return
  }
  // deduction（D2）：系统台词展示引导提示；玩家随后自由输入推理原文
  if (option.kind === 'deduction') {
    const hint = typeof option.hint === 'string' && option.hint ? option.hint : option.label
    setSpeakerLine('system', hint)
    presentation.state.status = 'streaming'
    pendingDeduction.value = option
    feedback.value = '推理模式：下一条输入将作为推理提交。'
    return
  }
  // evidence_present / private_interview（D6）：弹小面板
  if (option.kind === 'evidence_present' || option.kind === 'private_interview') {
    activePanel.value = option
    panelMessage.value = null
    return
  }
  // investigate：payload.steps 逐条执行既有权威端点（/api/game/action）
  if (option.kind === 'investigate') {
    optionBusy.value = true
    const epoch = viewEpoch
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
      if (epoch !== viewEpoch) return
      // 先对账（选项随热点完成而消失，D3），再给反馈，避免测试先看到文案
      await reconcileStage()
      if (epoch !== viewEpoch) return
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
  // recovery（T4）：进入 Recovery / 单步节点操作，均走既有权威端点
  if (option.kind === 'recovery') {
    optionBusy.value = true
    const epoch = viewEpoch
    try {
      if (option.payload?.action === 'start') {
        await startRecovery(sessionId.value)
        feedback.value = '已进入 Recovery。'
      } else {
        const action = option.payload?.action
        const target = option.payload?.target
        const actor = option.payload?.actor
        if (typeof action !== 'string' || typeof target !== 'string' || typeof actor !== 'string') return
        const result = await recoveryAction(sessionId.value, action, target, actor)
        if (epoch !== viewEpoch) return
        feedback.value =
          result.outcome === 'RETRY'
            ? '该节点需要先校验（Claude VERIFY）后才能修复。'
            : 'Recovery 操作已应用。'
      }
      await reconcileStage()
    } catch (e) {
      feedback.value = e instanceof Error ? e.message : 'Recovery 操作失败，请重试。'
    } finally {
      optionBusy.value = false
    }
    return
  }
  // narrative（T4 结局）：进入 Security Review / 听取自证 / 清理抉择（Bad End）
  if (option.kind === 'narrative') {
    optionBusy.value = true
    const epoch = viewEpoch
    try {
      const action = option.payload?.action
      if (action === 'security_review_start') {
        await securityReviewStart(sessionId.value)
        feedback.value = 'Security Review 开始。'
      } else if (action === 'testify') {
        const cid = option.payload?.character_id
        if (typeof cid !== 'string') return
        const result = await securityReviewTestify(sessionId.value, cid)
        if (epoch !== viewEpoch) return
        const statement = typeof result.statement === 'string' ? result.statement : ''
        if (statement) {
          setSpeakerLine(cid, statement)
          presentation.state.status = 'streaming'
        }
        feedback.value = `已听取 ${roleNameOf(cid)} 的自证。`
      } else if (action === 'delete') {
        const cid = option.payload?.character_id
        if (typeof cid !== 'string') return
        const cleanupAction = (
          { deepseek: 'DELETE_DEEPSEEK', claude: 'DELETE_CLAUDE', doubao: 'DELETE_DOUBAO' } as Record<
            string,
            string
          >
        )[cid]
        if (!cleanupAction) return
        await securityReviewCleanup(sessionId.value, cleanupAction)
        feedback.value = `已删除 ${roleNameOf(cid)}。`
      } else if (action === 'confirm_keep_chatgpt') {
        await securityReviewCleanup(sessionId.value, 'CONFIRM_KEEP_CHATGPT')
        feedback.value = '清理完成（Bad End：同意）。'
      } else if (action === 'delegate') {
        await securityReviewCleanup(sessionId.value, 'DELEGATE')
        feedback.value = '已委托 ChatGPT 执行清理（Bad End：委托）。'
      } else if (action === 'reject_cleanup') {
        await securityReviewRejectCleanup(sessionId.value)
        feedback.value = '已拒绝清理（To Be Continued）。'
      } else {
        return
      }
      await reconcileStage()
    } catch (e) {
      feedback.value = e instanceof Error ? e.message : '操作失败，请重试。'
    } finally {
      optionBusy.value = false
    }
    return
  }
}

// D2 一次性推理提交（判定走后端 /api/game/deduction；前端只透传原文）。
async function submitPlayerDeduction(message: string) {
  pendingDeduction.value = null
  if (!sessionId.value) return
  busy.value = true
  error.value = null
  const epoch = viewEpoch
  presentation.state.dialogue.text = ''
  setInputMode(false)
  try {
    const result = await submitDeduction(sessionId.value, message)
    if (epoch !== viewEpoch) return
    const accepted =
      result.outcome === 'ACCEPTED' || result.outcome === 'ALREADY_ACCEPTED'
    feedback.value = accepted
      ? result.outcome === 'ACCEPTED'
        ? '推理成立。'
        : '这条推理已被接受过了。'
      : result.outcome === 'BLOCKED'
        ? '推理还缺少关键证据或证词。'
        : '暂时无法确认这条推理，请换一种更具体的说法。'
    // 推理成立可能带回演出序列（GPT 登场 / 最终揭示，docs/12 §33）
    const actions = Array.isArray(result.presentation_actions)
      ? (result.presentation_actions as PresentationAction[])
      : []
    if (actions.length) {
      applyChatResponse(presentation.state, {
        session_id: sessionId.value,
        character_id: 'system',
        dialogue: '',
        message_count: 0,
        emotion: 'neutral',
        animation: 'none',
        presentation: [],
        presentation_actions: actions,
        claim_refs: [],
        script_sequence: [],
      })
    }
    const seq = Array.isArray(result.script_sequence)
      ? (result.script_sequence as ChatResponse['script_sequence'])
      : []
    scriptQueue.value = seq
    scriptIndex = 0
    if (seq.length > 0) {
      playNextScriptLine()
    } else {
      setInputMode(true)
    }
    await reconcileStage()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    setInputMode(true)
  } finally {
    busy.value = false
  }
}

// D6 小面板提交：按 kind 回传既有权威端点（D7）。
async function onPanelSubmit(payload: {
  character_id: string
  claim_ids: string[]
  evidence_ids: string[]
}) {
  if (!sessionId.value || !activePanel.value || panelBusy.value) return
  const option = activePanel.value
  panelBusy.value = true
  panelMessage.value = null
  const epoch = viewEpoch
  try {
    if (option.kind === 'evidence_present') {
      const evidenceId = payload.evidence_ids[0]
      if (!evidenceId) return
      await presentEvidence(sessionId.value, payload.character_id, evidenceId)
      if (epoch !== viewEpoch) return
      feedback.value = '已出示证据。'
      activePanel.value = null
    } else if (option.kind === 'private_interview') {
      const result = await submitPrivateInterviewChallenge(
        sessionId.value,
        payload.character_id,
        payload.claim_ids,
        payload.evidence_ids,
      )
      if (epoch !== viewEpoch) return
      if (result.outcome === 'UNLOCKED' || result.outcome === 'ALREADY_UNLOCKED') {
        feedback.value =
          result.outcome === 'UNLOCKED' ? '私审完成。' : '该角色私审已解锁。'
        activePanel.value = null
      } else {
        panelMessage.value = '质询未成立，请重新选择。'
        return
      }
    }
    await reconcileStage()
  } catch (e) {
    panelMessage.value = e instanceof Error ? e.message : '提交失败，请重试。'
  } finally {
    panelBusy.value = false
  }
}

async function startOpening() {
  const epoch = viewEpoch
  try {
    const opening = await createOpening(sessionId.value)
    if (epoch !== viewEpoch) return
    if (showLoading.value) {
      // 加载演出中：缓冲 opening，等演出结束再应用（docs/15 §7）
      bufferedOpening.value = opening
      openingReady.value = true
      return
    }
    applyOpeningResponse(opening)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    setInputMode(true)
    // 出错也要让加载演出按最长时限揭幕，错误在演出后可见
    if (showLoading.value) openingReady.value = true
  }
}

function applyOpeningResponse(opening: OpeningResponse) {
  invalidateView()  // 新会话 = 新画面代次，作废旧代次的在途响应
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
  invalidateView()  // Load 切换会话：作废一切在途响应
  sessionId.value = result.session_id
  localStorage.setItem(SESSION_KEY, result.session_id)
  const view = result.state?.presentation_state
  if (view) {
    applyPresentationStateView(presentation.state, view)
  }
  options.value = result.state?.options ?? []
  // 新 Active Session：本地粘性路由 / 推理 / 面板状态不复用
  routedCharacter.value = null
  pendingDeduction.value = null
  activePanel.value = null
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

function onLoadingComplete() {
  showLoading.value = false
  loadingShownThisSession = true
  const opening = bufferedOpening.value
  bufferedOpening.value = null
  if (opening) {
    applyOpeningResponse(opening)
  }
}

onMounted(async () => {
  // 0. 优先消费 Load 结果（docs/13 §20.3：LoadView/TitleView 暂存的 new
  // Active Session + GameViewState）
  if (game.pendingLoad) {
    applyLoadedSession(game.pendingLoad)
    return
  }
  // 0.5 首次加载演出：仅无存量会话的新游戏入口（docs/15 §7）
  if (
    !localStorage.getItem(SESSION_KEY) &&
    settings.loadingTransitionEnabled &&
    !loadingShownThisSession
  ) {
    showLoading.value = true
  }
  // 1. 恢复已有会话（localStorage）—— refresh 后 Session restore（docs/13 §27）
  const stored = localStorage.getItem(SESSION_KEY)
  if (stored) {
    sessionId.value = stored
    const epoch = viewEpoch
    try {
      await reconcileStage()
      if (epoch !== viewEpoch) return
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
  // T2review P1-7：卸载即作废在途请求；会话持久化由后端完成
  invalidateView()
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

    <!-- 顶部条：会话信息 + 系统菜单 + 返回标题（docs/13 §13 / Task 5）。
         docs/15 §8：pill 按钮组 + backdrop blur，与全站皮肤一致。 -->
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

    <!-- 面板打开时的场景模糊层（docs/15 §8：backdrop blur，面板本身保持清晰） -->
    <div
      v-if="systemPanel"
      class="pointer-events-none fixed inset-0 z-[25] bg-black/20 backdrop-blur-[6px]"
    ></div>

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

    <!-- 选项小面板（docs/14 §2.2 D6：出示证据 / 私审质询） -->
    <SubActionPanel
      v-if="activePanel"
      :option="activePanel"
      :busy="panelBusy"
      :message="panelMessage"
      @close="activePanel = null"
      @submit="onPanelSubmit"
    />

    <!-- 首次加载演出（docs/15 §7：New Game 专用；ready = opening 数据就绪） -->
    <LoadingTransition v-if="showLoading" :ready="openingReady" @complete="onLoadingComplete" />
  </div>
</template>
