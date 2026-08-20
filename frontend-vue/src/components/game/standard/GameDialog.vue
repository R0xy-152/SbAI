<template>
  <div
    class="relative z-2 flex w-full justify-center p-3.75 transition-all duration-200 ease-[cubic-bezier(0.25,0.46,0.45,0.94)] before:pointer-events-none before:absolute before:-top-10 before:right-0 before:left-0 before:h-10 before:bg-linear-to-b before:from-transparent before:via-[rgba(0,14,39,0.3)] before:to-[rgba(0,14,39,0.6)] before:content-['']"
    :class="{
      [`z-[-1]! overflow-hidden opacity-0 duration-500! ease-linear before:opacity-0 before:duration-1000!`]: isHidden,
      'max-h-[40vh]': !uiStore.isNarrowScreen,
    }"
    :style="dialogWrapperStyle"
    @wheel="handleWheelHistory"
  >
    <div :style="{ width: containerWidth + '%' }" class="relative">
      <div class="overflow-y-auto">
        <!-- 标题栏 -->
        <div class="mb-2 flex items-baseline">
          <!-- 角色名称 -->
          <div
            class="mr-3.75 font-[inherit] text-2xl font-bold text-shadow-[inherit]"
            :style="{ color: dialogTextColorValue }"
          >
            <div id="character">{{ uiStore.showCharacterTitle }}</div>
          </div>
          <!-- 角色副标题（docs/15：LingChat character-sub 行，第二轮补齐） -->
          <div
            v-show="!uiStore.isNarrowScreen"
            class="font-[inherit] text-xl font-bold text-[#6eb4ff] text-shadow-[inherit]"
          >
            <div id="character-sub">{{ uiStore.showCharacterSubtitle }}</div>
          </div>

          <!-- 情绪标签 -->
          <div
            class="mx-4 shrink-0 font-[inherit] text-xl font-bold text-[#ff77dd] text-shadow-[inherit]"
          >
            <div id="character-emotion">{{ uiStore.showCharacterEmotion }}</div>
          </div>
        </div>

        <!-- 分割线 -->
        <div class="my-1.5 h-px bg-white/30"></div>

        <!-- 输入区 -->
        <div
          class="relative my-1.25 flex min-h-10 w-full resize-none flex-col border-none bg-transparent text-xl font-bold whitespace-pre-line text-white transition-all duration-300 outline-none"
        >
          <!-- thinking 动画省略号（docs/16 P2：思考中占位改为逐点循环亮起的····） -->
          <div
            v-if="gameStore.currentStatus === 'thinking'"
            data-testid="thinking-dots"
            class="thinking-dots"
            aria-label="思考中"
          >
            <span>·</span><span>·</span><span>·</span><span>·</span>
          </div>
          <!-- 标准 textarea（显示台词 + 玩家输入） -->
          <textarea
            id="inputMessage"
            ref="textareaRef"
            class="my-1.25 max-h-[50vh] min-h-30 flex-1 resize-none border-none bg-transparent font-[inherit] text-xl font-bold transition-all duration-300 outline-none text-shadow-[inherit] placeholder:text-white/50 placeholder:shadow-none"
            :class="textareaMotionClass"
            :placeholder="placeholderText"
            v-model="inputMessage"
            @keydown.enter.exact.prevent="sendOrContinue"
            :readonly="!isInputEnabled"
          ></textarea>
        </div>
      </div>
      <!-- 发送按钮（内层右侧外部） -->
      <button
        id="sendButton"
        class="send-hit-area absolute right-0 bottom-0 translate-x-full cursor-pointer rounded-[5px] border-none bg-transparent px-2 py-2 font-[inherit] text-sm font-bold text-[#04bcff] transition-all duration-300 text-shadow-[inherit] hover:bg-transparent hover:text-[rgba(136,255,251,0.827)] disabled:cursor-not-allowed disabled:bg-[#333] disabled:opacity-70"
        :disabled="isSending"
        @click="sendOrContinue"
      >
        ▼
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
// Adapted from LingChat (AGPL-3.0): src/components/game/standard/GameDialog.vue
// Modification（docs/13 §11.4 第一轮只保留 speaker / textarea / typing / input /
// send / loading）：删除了移动端折叠菜单、场景设置/历史/截图/语音/关闭按钮、
// Tauri listen/invoke（screenshot）、LingChat stores；语音识别移除；
// 保留 auto 布局、typing/streaming、player input、thinking 占位、对话框外观。
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useGameStore, useUIStore, useSettingsStore, eventQueue } from '../../../adapters/lingchat-compat'
import { useDialogAppearance } from './useDialogAppearance'
import { useTypeWriter } from './useTypeWriter'
import { setInputHasText } from '../../../adapters/lingchat-compat'

const inputMessage = ref('')
watch(inputMessage, (val) => setInputHasText(Boolean(val.trim())), { immediate: true })
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const gameStore = useGameStore()
const uiStore = useUIStore()
const settingsStore = useSettingsStore()

const { isHidden, hide, dialogWrapperStyle, dialogTextColorValue, handleWheelHistory } =
  useDialogAppearance({
    openHistory: () => {},
  })

// 内联显示模式：设置开启 + 回应状态 → 用 div 做混色显示（当前固定关闭）
const isInlineDisplayMode = computed(
  () => settingsStore.text.inlineMotionText && gameStore.currentStatus === 'responding',
)

// 响应式容器宽度（窄屏判断从 uiStore 读取）
const containerWidth = ref(60)

const updateContainerWidth = () => {
  containerWidth.value = Math.max(60, uiStore.aspectRatio > 1 ? 70 : 90)
}

const currentDisplayedText = ref('')

// 立即把当前台词写入显示元素（不经过打字动画；供挂载恢复使用）
function renderLineInstant(line: string) {
  currentDisplayedText.value = line
  if (textareaRef.value) {
    textareaRef.value.value = line
    inputMessage.value = line // 与 v-model 同步，防止重渲染把值重置为空
  }
}

// 标准模式 TypeWriter（textarea）
const {
  startTyping: startTextTyping,
  stopTyping: stopTextTyping,
  isTyping: isTextTyping,
  finishTyping: finishTextTyping,
} = useTypeWriter(textareaRef, (text) => {
  currentDisplayedText.value = text
})

const isTyping = computed(() => isTextTyping.value)

const isSending = computed(() => gameStore.currentStatus === 'thinking')

// textarea 动态样式
const textareaMotionClass = computed(() => ({}))

const emit = defineEmits(['player-continued', 'dialog-proceed'])

const placeholderText = computed(() => {
  switch (gameStore.currentStatus) {
    case 'input':
      return '输入你的台词…'
    case 'thinking':
      // docs/16 P2：占位由 thinking-dots 动画省略号呈现，textarea placeholder 留空
      return ''
    case 'responding':
    case 'presenting':
      return ''
    default:
      return '输入你的台词…'
  }
})

const isInputEnabled = computed(() => gameStore.currentStatus === 'input')

watch([() => uiStore.showCharacterLine, () => gameStore.currentStatus], ([newLine, newStatus]) => {
  if (newLine && newLine !== '' && newStatus === 'responding') {
    inputMessage.value = ''
    currentDisplayedText.value = ''
    startTextTyping(newLine, uiStore.typeWriterSpeed)
  } else if (newStatus === 'input') {
    stopTextTyping()
    inputMessage.value = ''
    currentDisplayedText.value = ''
  }
})

onMounted(() => {
  // 模式切换重挂载：立即从 store 恢复当前台词（不重播打字动画）
  const restoreLine = uiStore.showCharacterLine
  if (restoreLine && restoreLine !== '' && gameStore.currentStatus === 'responding') {
    renderLineInstant(restoreLine)
  }
  updateContainerWidth()
  window.addEventListener('resize', updateContainerWidth)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateContainerWidth)
})

function sendOrContinue() {
  if (gameStore.currentStatus === 'input') {
    send()
  } else if (gameStore.currentStatus === 'responding') {
    continueDialog(true)
  }
}

function send() {
  const text = inputMessage.value
  if (!text.trim()) return
  emit('player-continued', text)
  inputMessage.value = ''
}

function continueDialog(isPlayerTrigger: boolean): boolean {
  // 内联动作文本模式：第一轮不迁移，直接推进
  const needWait = eventQueue.continue()
  if (!needWait) {
    if (isPlayerTrigger) emit('player-continued')
    emit('dialog-proceed')
  }
  return needWait
}

defineExpose({
  continueDialog,
  isTyping,
})
</script>

<style scoped>
/* 兼容 Chrome / Edge / Safari */
.custom-scroll::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

/* docs/16 P4：继续/发送按钮命中区扩大 —— 视觉按钮不动，用透明 ::after 向
   右/下/上方扩展触发范围（不向左，避免压到 textarea 右侧输入区；上方扩展
   停在选项气泡条下方，不与其它功能按键重合）。 */
.send-hit-area::after {
  content: '';
  position: absolute;
  top: -40px;
  bottom: -24px;
  left: 0;
  right: -24px;
}

/* docs/16 P2：思考中动画省略号 —— 4 个点逐点循环亮起（纯 CSS，无素材） */
.thinking-dots {
  position: absolute;
  top: 0.25rem;
  left: 0.25rem;
  display: flex;
  gap: 0.15em;
  align-items: baseline;
  pointer-events: none;
  z-index: 1;
}
.thinking-dots span {
  animation: dot-pulse 1.2s ease-in-out infinite;
}
.thinking-dots span:nth-child(2) {
  animation-delay: 0.15s;
}
.thinking-dots span:nth-child(3) {
  animation-delay: 0.3s;
}
.thinking-dots span:nth-child(4) {
  animation-delay: 0.45s;
}
@keyframes dot-pulse {
  0%,
  60%,
  100% {
    opacity: 0.25;
  }
  30% {
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .thinking-dots span {
    animation: none;
    opacity: 0.6;
  }
}
</style>
