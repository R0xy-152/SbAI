<script setup lang="ts">
// 第一章 · 角色舞台（docs/13 Task 4）：接入现有 FastAPI Game Runtime。
// New Session → Player Input → Response → Presentation Directive → Character
// Presence → Emotion → Narrative Event。03:17 经「调查纸（EV01）」触发，
// Claude 由后端 CH01_INCIDENT_0317 脚本登场，随后可对话。
// 所有展示变化来自 Backend presentation_actions / presentation_state，前端不
// 从剧情条件推断角色在场（docs/13 §9.2）。
import { onMounted, onUnmounted, ref } from 'vue'
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
import type { ChatResponse } from '../api/game'
import GameBackground from '../components/game/standard/GameBackground.vue'
import GameRolesStage from '../components/game/standard/GameRolesStage.vue'
import GameDialog from '../components/game/standard/GameDialog.vue'

const presentation = usePresentationStore()

const SESSION_KEY = 'gal_session_id'
const BG = '/backgroud/background1.png'

// 角色切换器（docs/13 §27：Claude 可对话 —— 经 SpeakerSelector 在 mock 下只会
// 返回 deepseek，前端显式选择可对话角色，Availability 仍由后端 Presence Gate 把关）。
const AVAILABLE_ROLE_IDS = ['deepseek', 'claude', 'chatgpt', 'doubao'] as const
type RoleId = (typeof AVAILABLE_ROLE_IDS)[number]
const selectedRole = ref<RoleId>('deepseek')

const sessionId = ref<string | null>(null)
const canInput = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const currentResponse = ref<ChatResponse | null>(null)

// 剧本序列逐行播放队列（03:17 / GPT / 豆包 / FINAL_REVEAL 等多行演出）
const scriptQueue = ref<ChatResponse['script_sequence']>([])
let scriptIndex = 0

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
    const data = await sendChat(sessionId.value, text.trim(), selectedRole.value)
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

// 调查纸（03:17 前置：EV01_NOTE_V03）
const investigationBusy = ref(false)
const investigationMsg = ref('')
const investigationDone = ref(false)

async function inspectPaper() {
  if (!sessionId.value || investigationBusy.value) return
  investigationBusy.value = true
  investigationMsg.value = ''
  try {
    const res = await sendInvestigationAction(sessionId.value, 'INSPECT_HOTSPOT', 'CH1_NOTE_01')
    if (res.state?.presentation_state) {
      applyPresentationStateView(presentation.state, res.state.presentation_state)
    }
    // 纸面拓印：inspect 后立即可做 PAPER_RUBBING_COMPLETE（后端要求先 inspect）
    const rubbed = await sendInvestigationAction(
      sessionId.value,
      'PAPER_RUBBING_COMPLETE',
      'CH1_NOTE_01',
    )
    if (rubbed.evidence_id) {
      investigationDone.value = true
      investigationMsg.value = '纸面拓印完成，获得了「03:17 的笔记」线索。'
    } else if (rubbed.outcome === 'ALREADY_COMPLETED') {
      investigationDone.value = true
      investigationMsg.value = '这张纸已经拓印过了。'
    }
  } catch (e) {
    investigationMsg.value = e instanceof Error ? e.message : '调查失败，请重试。'
  } finally {
    investigationBusy.value = false
  }
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
      // opening 是开场演出：播放中不可输入，玩家点击推进后解锁
      setInputMode(false)
      // 让下一句（无剧本序列时）直接解锁：opening 单句，推进后进入输入
      pendingOpeningAdvance = true
    } else {
      setInputMode(true)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    setInputMode(true)
  }
}

onMounted(async () => {
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
        presentation.state.status = 'streaming'
        setInputMode(false)
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

    <!-- 调查纸入口（03:17 前置，docs/13 §27 最小闭环） -->
    <div
      v-if="!investigationDone"
      class="absolute bottom-40 left-4 z-20 flex flex-col gap-2 rounded-lg border border-white/15 bg-black/60 p-3 text-sm text-[#d7effa]"
    >
      <button
        class="rounded bg-[#123c63]/80 px-3 py-1.5 hover:bg-[#1b527f] disabled:opacity-50"
        :disabled="investigationBusy"
        @click="inspectPaper"
      >
        {{ investigationBusy ? '调查中…' : '调查桌上的纸' }}
      </button>
      <span v-if="investigationMsg" class="max-w-[240px] text-xs text-[#a9e8ff]/80">
        {{ investigationMsg }}
      </span>
    </div>

    <!-- 角色切换器（Claude 可对话） -->
    <div class="absolute right-4 top-4 z-20 flex gap-2 rounded-lg border border-white/15 bg-black/60 p-2">
      <button
        v-for="id in AVAILABLE_ROLE_IDS"
        :key="id"
        class="rounded px-2.5 py-1 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40"
        :class="
          selectedRole === id
            ? 'bg-[#04bcff]/30 text-[#9ff]'
            : 'text-[#d7effa]/70 hover:bg-white/10'
        "
        @click="selectedRole = id"
      >
        {{ roleNameOf(id) }}
      </button>
    </div>

    <!-- 对话框（底部） -->
    <div class="absolute inset-x-0 bottom-0 z-10">
      <GameDialog
        class="mx-auto"
        @player-continued="onPlayerMessage"
        @dialog-proceed="onDialogProceed"
      />
    </div>

    <!-- 顶部条：会话信息 -->
    <header class="absolute left-0 top-0 z-20 px-4 py-2 text-sm text-[#d7effa]/70">
      <span v-if="sessionId">会话 {{ sessionId.slice(0, 8) }}…</span>
      <span v-else>未连接</span>
      <span v-if="error" class="ml-3 text-red-300">{{ error }}</span>
    </header>
  </div>
</template>
