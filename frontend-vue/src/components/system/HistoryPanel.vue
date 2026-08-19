<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchHistory } from '../../api/game'

// 游戏内「历史」面板（docs/13 §13.3）：展示当前 Session 合法的已显示对话
// History（docs/01 §18）。History ≠ Character Memory，绝不展示 Memory 内容。
const props = defineProps<{
  sessionId: string | null
}>()

const emit = defineEmits<{ close: [] }>()

interface HistoryLine {
  role: string
  character_id: string | null
  content: string
}

const lines = ref<HistoryLine[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const ROLE_NAMES: Record<string, string> = {
  player: '你',
  character: '',
  system: '系统',
}

function speakerLabel(line: HistoryLine): string {
  const name = ROLE_NAMES[line.role] ?? line.role
  if (name !== '') return name
  const charNames: Record<string, string> = {
    deepseek: 'DeepSeek',
    claude: 'Claude',
    chatgpt: 'ChatGPT',
    doubao: '豆包',
  }
  return line.character_id ? (charNames[line.character_id] ?? line.character_id) : '角色'
}

async function loadHistory() {
  if (!props.sessionId) return
  loading.value = true
  error.value = null
  try {
    const data = await fetchHistory(props.sessionId)
    lines.value = data.messages ?? []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '读取历史失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)

watch(
  () => props.sessionId,
  () => {
    if (props.sessionId) void loadHistory()
  },
)
</script>

<template>
  <div
    class="fixed inset-0 z-30 flex items-center justify-center bg-black/70"
    @click.self="emit('close')"
  >
    <div class="flex max-h-[85vh] w-[min(92vw,640px)] flex-col rounded-xl border border-white/15 bg-[#0b1424]/95 p-5 text-[#f4f8ff] shadow-2xl">
      <header class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-bold text-[#dff7ff]">对话历史</h2>
        <button class="text-sm text-[#d7effa]/70 hover:text-[#dff7ff]" @click="emit('close')">关闭</button>
      </header>

      <main class="flex-1 overflow-y-auto pr-1">
        <p v-if="loading" class="text-sm text-[#a9e8ff]/60">读取历史…</p>
        <p v-else-if="error" class="text-sm text-red-300">{{ error }}</p>
        <p v-else-if="lines.length === 0" class="text-sm text-[#d7effa]/50">暂无对话记录。</p>
        <ul v-else class="flex flex-col gap-2.5">
          <li v-for="(line, i) in lines" :key="i" class="flex gap-2 text-sm">
            <span
              class="w-20 shrink-0 font-bold"
              :class="line.role === 'player' ? 'text-[#04bcff]' : line.role === 'system' ? 'text-[#ffd86b]' : 'text-[#d7effa]'"
            >
              {{ speakerLabel(line) }}
            </span>
            <span class="whitespace-pre-line break-words text-[#eaf3ff]/90">{{ line.content }}</span>
          </li>
        </ul>
      </main>
    </div>
  </div>
</template>
