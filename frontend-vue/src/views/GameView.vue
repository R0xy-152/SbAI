<script setup lang="ts">
// 第一章 · 角色舞台（docs/13 Task 4）：接入现有 FastAPI Game Runtime。
// Player Input → Response → Presentation Directive → Character Presence →
// Emotion → Narrative Event。03:17 经「调查纸（EV01）」触发，Claude 由后端
// CH01_INCIDENT_0317 脚本登场，随后可对话。
// 所有展示变化来自 Backend presentation_actions / presentation_state，前端不
// 从剧情条件推断角色在场（docs/13 §9.2）。
// Task 7：游戏内系统菜单（§13 Save/Load/History/Return Title）+ Load 消费
//（§20.3：game.pendingLoad 在挂载时恢复新 Session）。
// 2026-08-21 用户需求：新开局不再播放前置开场白（SCRIPT_OPENING「你醒了，
// 别怕」），也不自动弹出「选择行动」选项窗口 —— 直接进入自由对话；会话由
// 首个玩家消息经 /api/chat 创建（后端 mint session 并在响应中返回 id）。
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useSavesStore } from '../stores/saves'
import { usePresentationStore } from '../stores/presentation'
import {
  applyChatResponse,
  applyPresentationStateView,
  setDialogueLine,
} from '../adapters/presentation-adapter'
import {
  fetchEvidence,
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
import type { ChatResponse, GameOption, PresentationAction } from '../api/game'
import type { LoadResult } from '../api/saves'
import GameBackground from '../components/game/standard/GameBackground.vue'
import GameRolesStage from '../components/game/standard/GameRolesStage.vue'
import GameDialog from '../components/game/standard/GameDialog.vue'
import SavePanel from '../components/save/SavePanel.vue'
import LoadPanel from '../components/save/LoadPanel.vue'
import SystemMenu from '../components/system/SystemMenu.vue'
import HistoryPanel from '../components/system/HistoryPanel.vue'
import OptionWindow from '../components/game/standard/OptionWindow.vue'
import ScreenEffects from '../components/game/standard/ScreenEffects.vue'
import ClueWindow from '../components/game/standard/ClueWindow.vue'
import SubActionPanel from '../components/game/standard/SubActionPanel.vue'
import LoadingTransition from '../components/effects/LoadingTransition.vue'
import EyeOpenTransition from '../components/effects/EyeOpenTransition.vue'
import { useSettingsStore } from '../stores/settings'
import { useAuthStore } from '../stores/auth'
import { splitTextSegments } from '../utils/text-segments'

const presentation = usePresentationStore()
const game = useGameStore()
const saves = useSavesStore()
const settings = useSettingsStore()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const SESSION_KEY = 'gal_session_id'
// AI 对话玩法常驻背景（2026-08-21 用户提供新图，原 background1.png 仅故事模式用）
const BG = '/backgroud/background_ai.png'

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
// 新开局首个回合结束不自动弹选项窗口（见 onDialogProceed；仅新会话置真）
let suppressFirstOptionPop = false

// docs/16 P5：黑幕眼睑式睁眼转场 —— 每次进入游戏画面播一次（新游戏排在猫爪
// 演出之后，读档/会话恢复直接播）；pointer-events:none 不挡点击。
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
function onEyeOpenComplete() {
  showEyeOpen.value = false
}

// docs/16 P6：统一演出队列 —— 主台词按换行切段后逐段播放，随后接
// script_sequence 行；onDialogProceed 逐行推进，播完解锁输入（P7 再叠加
// 「有选项则弹窗口」）。
interface QueuedLine {
  speaker: string
  text: string
  emotion?: string | null
}
const lineQueue = ref<QueuedLine[]>([])
let lineIndex = 0

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
    applyPresentationStateView(presentation.state, state.presentation_state, BG)
    options.value = state.options ?? []
    if (state.chat_character_id) {
      routedCharacter.value = state.chat_character_id
      prologueChatLocked.value = true
      return
    }
    prologueChatLocked.value = false
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

// 播放队列下一行（台词分段 / 剧本行）；播完返回 false
function playNextLine(): boolean {
  if (lineIndex >= lineQueue.value.length) {
    lineQueue.value = []
    lineIndex = 0
    return false
  }
  const line = lineQueue.value[lineIndex]
  lineIndex++
  setSpeakerLine(line.speaker, line.text, line.emotion)
  presentation.state.status = 'streaming'
  return true
}

// 玩家发送
async function onPlayerMessage(text?: unknown) {
  if (typeof text !== 'string' || !text.trim() || busy.value) return
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
    auth.setQuota(data.quota_remaining)
    if (epoch !== viewEpoch) return
    // 新会话：首个玩家消息即创建会话，后端在响应中带回 session_id
    sessionId.value = data.session_id
    localStorage.setItem(SESSION_KEY, data.session_id)
    currentResponse.value = data
    // 结构化指令 → 舞台（CHARACTER_SHOW / EMOTION / GLITCH 等）
    applyChatResponse(presentation.state, data)
    presentation.state.dialogue.speakerName = roleNameOf(data.character_id)
    // docs/16 P6：主台词按换行切段 → 统一队列（段在前，script_sequence 行在后）
    lineQueue.value = [
      ...splitTextSegments(data.dialogue).map((t) => ({
        speaker: data.character_id,
        text: t,
        emotion: data.emotion,
      })),
      ...(data.script_sequence ?? []).map((s) => ({
        speaker: s.speaker,
        text: s.dialogue,
        emotion: s.emotion,
      })),
    ]
    lineIndex = 0
    if (!playNextLine()) setInputMode(true)
    await reconcileStage()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    setInputMode(true)
  } finally {
    busy.value = false
  }
}

// 打字机完成（dialog-proceed）→ 推进队列下一行（台词分段 / 剧本行）；播完解锁输入
function onDialogProceed() {
  if (lineIndex < lineQueue.value.length) {
    playNextLine()
    return
  }
  lineQueue.value = []
  lineIndex = 0
  // docs/16 P7/P8：台词播完点继续，若有可用选项 → 弹选项窗口（否则解锁输入）
  if (options.value.length > 0) {
    // 2026-08-21 用户需求：新开局不再自动弹「选择行动」窗口（前置剧情已删），
    // 首个回合结束后直接进入自由输入；旧调查玩法仍经左上角「行动」按钮可见
    if (suppressFirstOptionPop) {
      suppressFirstOptionPop = false
      setInputMode(true)
      return
    }
    showOptionWindow.value = true
  } else {
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
const routedCharacter = ref<string | null>(
  typeof route.query.character === 'string' ? route.query.character : null,
)
const prologueChatLocked = ref(false)

// D2 一次性推理模式：非空时下一条主输入框消息提交到 /api/game/deduction
const pendingDeduction = ref<GameOption | null>(null)
// D6 小面板：当前打开需要上下文的选项（evidence_present / private_interview）
const activePanel = ref<GameOption | null>(null)
const panelBusy = ref(false)
const panelMessage = ref<string | null>(null)

const routeLabel = computed(() => {
  if (!routedCharacter.value) return null
  return prologueChatLocked.value
    ? `正在与 ${roleNameOf(routedCharacter.value)} 进行序章自由交流`
    : `正在与 ${roleNameOf(routedCharacter.value)} 对话：再点同一选项回到公共对话`
})

// docs/16 P7/P8：选项窗口 + 线索窗口。窗口取代 docs/14 D6 气泡条；AI 台词播完
// 点继续时若存在选项则弹窗（D4：窗口含「继续对话」关闭项，自由输入不受限）。
const showOptionWindow = ref(false)
const activeClue = ref<{ title: string; summary: string } | null>(null)

function openOptionWindow() {
  if (options.value.length > 0 && !llmBusy.value) showOptionWindow.value = true
}

function closeOptionWindow() {
  showOptionWindow.value = false
  if (!activeClue.value) setInputMode(true)
}

async function onOptionWindowSelect(option: GameOption) {
  if (!sessionId.value || optionBusy.value || llmBusy.value) return
  if (option.kind === 'investigate') {
    showOptionWindow.value = false
    const evidenceId = await performInvestigate(option)
    if (evidenceId) {
      await openClueWindow(evidenceId)
    } else {
      setInputMode(true)
    }
    return
  }
  showOptionWindow.value = false
  await executeOption(option)
  // 出提示行/证词行的选项（deduction；narrative 的 testify）自身控制输入态（后续点
  // 继续解锁）；evidence_present/private_interview 弹小面板（面板关闭时解锁）；
  // 其余（chat_routing/recovery/narrative 其它动作）统一解锁。
  const setsLine =
    option.kind === 'deduction' ||
    (option.kind === 'narrative' && option.payload?.action === 'testify')
  if (
    !setsLine &&
    option.kind !== 'evidence_present' &&
    option.kind !== 'private_interview'
  ) {
    setInputMode(true)
  }
}

async function performInvestigate(option: GameOption): Promise<string | null> {
  if (!sessionId.value) return null
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
        applyPresentationStateView(presentation.state, last.state.presentation_state, BG)
      }
    }
    if (epoch !== viewEpoch) return null
    await reconcileStage()
    if (epoch !== viewEpoch) return null
    if (last) {
      feedback.value =
        last.outcome === 'ALREADY_COMPLETED'
          ? '已经调查过了。'
          : last.evidence_id
            ? '调查完成，获得新线索。'
            : '调查完成。'
      return typeof last.evidence_id === 'string' ? last.evidence_id : null
    }
    return null
  } catch (e) {
    feedback.value = e instanceof Error ? e.message : '调查失败，请重试。'
    return null
  } finally {
    optionBusy.value = false
  }
}

async function openClueWindow(evidenceId: string) {
  if (!sessionId.value) return
  try {
    const evidence = await fetchEvidence(sessionId.value)
    const found = evidence.find((ev) => ev.evidence_id === evidenceId)
    if (found) {
      activeClue.value = { title: found.title, summary: found.summary }
    } else {
      setInputMode(true)
    }
  } catch (e) {
    console.warn('[GameView] fetch evidence failed', e)
    setInputMode(true)
  }
}

function onClueClose() {
  activeClue.value = null
  setInputMode(true)
}

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
  // investigate：payload.steps 逐条执行既有权威端点（/api/game/action）。
  // 执行细节收敛到 performInvestigate（P7 线索窗口也复用）。
  if (option.kind === 'investigate') {
    await performInvestigate(option)
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
        quota_remaining: auth.user?.quota_remaining ?? 0,
      })
    }
    const seq = Array.isArray(result.script_sequence)
      ? (result.script_sequence as ChatResponse['script_sequence'])
      : []
    lineQueue.value = seq.map((s) => ({
      speaker: s.speaker,
      text: s.dialogue,
      emotion: s.emotion,
    }))
    lineIndex = 0
    if (!playNextLine()) setInputMode(true)
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
    // docs/16 P8：面板提交成功后（activePanel 已关闭）解锁输入
    if (!activePanel.value) setInputMode(true)
  } catch (e) {
    panelMessage.value = e instanceof Error ? e.message : '提交失败，请重试。'
  } finally {
    panelBusy.value = false
  }
}

function closePanel() {
  activePanel.value = null
  setInputMode(true)
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
    applyPresentationStateView(presentation.state, view, BG)
  }
  options.value = result.state?.options ?? []
  // 新 Active Session：本地粘性路由 / 推理 / 面板状态不复用
  routedCharacter.value = result.story_cursor?.chat_character_id ?? null
  prologueChatLocked.value = Boolean(routedCharacter.value)
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
  // docs/16 P5：猫爪揭幕结束后播睁眼转场
  armEyeOpen()
}

onMounted(async () => {
  // 0. 优先消费 Load 结果（docs/13 §20.3：LoadView/TitleView 暂存的 new
  // Active Session + GameViewState）
  if (game.pendingLoad) {
    applyLoadedSession(game.pendingLoad)
    armEyeOpen()
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
      armEyeOpen()
      return
    } catch (e) {
      // 会话未知/已失效 → 视为新开
      console.warn('[GameView] restore session failed, starting new', e)
      localStorage.removeItem(SESSION_KEY)
      sessionId.value = null
    }
  }
  // 2. 新会话 → 直接自由对话（前置剧情已删除：不播开场白、不弹「选择行动」
  //    窗口；会话由首个玩家消息经 /api/chat 创建，响应带回 session_id 后写回
  //    localStorage —— 见 onPlayerMessage）
  presentation.state.scene.backgroundId = BG
  setInputMode(true)
  suppressFirstOptionPop = true
  // docs/16 P5：无加载演出（设置关闭）的新游戏路径直接播睁眼
  if (!showLoading.value) armEyeOpen()
})

onUnmounted(() => {
  // T2review P1-7：卸载即作废在途请求；会话持久化由后端完成
  invalidateView()
})
</script>

<template>
  <div
    class="relative h-full w-full overflow-hidden bg-black"
    :class="{ 'screen-shake': presentation.state.effects.includes('SCREEN_SHAKE') }"
  >
    <!-- 背景 -->
    <GameBackground />

    <!-- 角色舞台 -->
    <GameRolesStage class="pointer-events-none absolute inset-0 z-1" />

    <!-- 屏幕故障特效层（SCREEN_GLITCH 脉冲；docs/17 演出接线） -->
    <ScreenEffects :effects="presentation.state.effects" />

    <!-- 对话框（底部）+ 状态行（routeLabel / feedback，docs/16 P8 取代气泡条） -->
    <div class="absolute inset-x-0 bottom-0 z-10 flex flex-col">
      <div
        v-if="routeLabel || feedback"
        class="flex w-full flex-col items-center gap-1 pb-1"
      >
        <div v-if="routeLabel" class="px-4 text-xs text-[#a9e8ff]">{{ routeLabel }}</div>
        <div v-if="feedback" class="max-w-[560px] px-4 text-xs text-[#a9e8ff]/80">{{ feedback }}</div>
      </div>
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
          v-if="options.length"
          class="rounded-full border border-white/15 bg-black/40 px-3 py-1 text-xs text-[#d7effa]/85 backdrop-blur-sm transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="llmBusy"
          @click="openOptionWindow"
        >
          行动
        </button>
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
      @close="closePanel"
      @submit="onPanelSubmit"
    />

    <!-- 选项窗口（docs/16 P7/P8：取代气泡条；AI 台词播完点继续 / 点「行动」打开） -->
    <OptionWindow
      v-if="showOptionWindow"
      :options="options"
      :busy="optionBusy || llmBusy"
      :active-route-id="routedCharacter ? 'chat_routing:' + routedCharacter : null"
      @select="onOptionWindowSelect"
      @dismiss="closeOptionWindow"
    />

    <!-- 线索窗口（docs/16 P7：调查成功后展示获得证据的标题 + 描述） -->
    <ClueWindow
      v-if="activeClue"
      :title="activeClue.title"
      :summary="activeClue.summary"
      @close="onClueClose"
    />

    <!-- 首次加载演出（docs/15 §7：New Game 专用；无 opening 数据，ready 恒真） -->
    <LoadingTransition v-if="showLoading" :ready="true" @complete="onLoadingComplete" />

    <!-- 睁眼转场（docs/16 P5：每次进入游戏画面播一次，纯视觉、不挡点击） -->
    <EyeOpenTransition v-if="showEyeOpen" @complete="onEyeOpenComplete" />
  </div>
</template>
