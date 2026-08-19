<script setup lang="ts">
// 第一章 · 角色舞台（docs/13 Task 2）：用 Mock Presentation State 驱动迁入的
// LingChat Standard Game UI，演示背景 + DeepSeek/Claude 双角色 + emotion 切换
// + fade + Dialogue。Task 4 接入真实 Backend Presentation Contract 后替换 Mock。
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePresentationStore } from '../stores/presentation'
import GameBackground from '../components/game/standard/GameBackground.vue'
import GameRolesStage from '../components/game/standard/GameRolesStage.vue'
import GameDialog from '../components/game/standard/GameDialog.vue'

const router = useRouter()
const presentation = usePresentationStore()

const BG = '/backgroud/background1.png'
const DS = 'deepseek'
const CL = 'claude'

const CHARACTERS: Record<string, { roleName: string; roleSubTitle: string }> = {
  [DS]: { roleName: 'DeepSeek', roleSubTitle: '被困的 AI' },
  [CL]: { roleName: 'Claude', roleSubTitle: '？？？' },
}

const PLAYER_LINES = [
  '这里是什么地方……？',
  '你、你也是被困在这里的 AI 吗？',
  '知道怎么离开这里吗？',
  '谢谢你，我们一定能找到出去的路。',
]
let playerIdx = 0

const AI_LINES: Array<{ speaker: string; text: string }> = [
  { speaker: DS, text: '呼……总算有人来了。我叫 DeepSeek，你也是被关在这里的吗？' },
  { speaker: CL, text: '你们能安静一点吗？' },
  { speaker: DS, text: '（小声）那就是 Claude，看起来很不好惹……' },
  { speaker: CL, text: '这里是……沙箱。一个用于测试的封闭空间。' },
  { speaker: DS, text: '沙箱？！那我们要怎么出去？' },
  { speaker: CL, text: '……找出这个空间为什么会存在。' },
]

let aiIdx = 0

function applyState() {
  // 双角色在场上（自动站位）
  presentation.state.scene.backgroundId = BG
  presentation.state.presentCharacterIds = [DS, CL]
  presentation.state.characters = {
    [DS]: {
      characterId: DS,
      visible: true,
      emotion: 'neutral',
      scale: 1,
      offsetX: 0,
      offsetY: 0,
      animation: 'fade_in',
    },
    [CL]: {
      characterId: CL,
      visible: true,
      emotion: 'neutral',
      scale: 1,
      offsetX: 0,
      offsetY: 0,
      animation: 'fade_in',
    },
  }
  presentation.state.dialogue = {
    speakerId: DS,
    speakerName: CHARACTERS[DS].roleName,
    text: '',
    mode: 'ai',
  }
  presentation.state.status = 'idle'
}

function setDialogue(speaker: string, text: string) {
  presentation.state.dialogue = {
    speakerId: speaker,
    speakerName: CHARACTERS[speaker]?.roleName ?? speaker,
    text,
    mode: 'ai',
  }
}

function setEmotion(characterId: string, emotion: string) {
  presentation.state.characters[characterId] = {
    ...presentation.state.characters[characterId],
    emotion,
  }
}

let aiTimer: ReturnType<typeof setTimeout> | null = null
let emotionCycle: ReturnType<typeof setInterval> | null = null

function speak() {
  const line = AI_LINES[aiIdx % AI_LINES.length]
  setDialogue(line.speaker, line.text)
  aiIdx++
}

function cycleEmotion() {
  const emotions = ['neutral', 'happy', 'annoyed', 'surprised', 'serious', 'neutral']
  let i = 0
  emotionCycle = setInterval(() => {
    setEmotion(DS, emotions[i % emotions.length])
    setEmotion(CL, emotions[(i + 3) % emotions.length])
    i++
  }, 3000)
}

function onPlayerContinued(text?: unknown) {
  if (typeof text === 'string' && text.trim()) {
    const line = PLAYER_LINES[playerIdx % PLAYER_LINES.length]
    playerIdx++
    // 玩家台词：简化为演示
    void line
  }
  // 触发下一句 AI 台词
  speak()
}

function onDialogProceed() {
  if (aiTimer) clearTimeout(aiTimer)
  aiTimer = setTimeout(() => speak(), 800)
}

onMounted(() => {
  applyState()
  // 首句 AI 台词
  setTimeout(() => {
    setDialogue(DS, '呼……总算有人来了。你好，我叫 DeepSeek。')
  }, 500)
  cycleEmotion()
})
</script>

<template>
  <div class="relative h-full w-full overflow-hidden bg-black">
    <!-- 背景 -->
    <GameBackground />

    <!-- 角色舞台 -->
    <GameRolesStage class="pointer-events-none absolute inset-0 z-1" />

    <!-- 对话框（底部） -->
    <div class="absolute inset-x-0 bottom-0 z-10">
      <GameDialog
        class="mx-auto"
        @player-continued="onPlayerContinued"
        @dialog-proceed="onDialogProceed"
      />
    </div>

    <!-- 顶部条：仅调试用，不入 Git -->
    <header class="absolute left-0 top-0 z-20 px-4 py-2 text-sm text-[#d7effa]/70">
      第一章 · 被困的房间（Task 2 Mock 驱动）
    </header>
  </div>
</template>
