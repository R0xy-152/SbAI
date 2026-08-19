<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useSavesStore } from '../../stores/saves'
import AutoSaveCard from './AutoSaveCard.vue'
import ManualSaveSlot from './ManualSaveSlot.vue'

// 游戏内「保存」面板（docs/13 §13.1）：6 个手动 Slot，每 slot 可即时
// 输入自定义标题后保存。自动存档由 Task 8 在 checkpoint 自动写入（此处
// 只读展示）。操作走 saves store → Save API，snapshot 由 Backend Capture
//（docs/13 §14.2）。LLM 中间态下保存禁用（docs/13 §22）由父级把 busy 传入。
const props = defineProps<{
  sessionId: string
  /** LLM thinking/streaming 中间态（docs/13 §22：保存 disabled）。 */
  busy: boolean
}>()

const emit = defineEmits<{ close: [] }>()

const saves = useSavesStore()
const titleInput = ref<Record<number, string>>({})
const savingSlot = ref<number | null>(null)
const message = ref<string | null>(null)
const messageKind = ref<'ok' | 'err'>('ok')

async function refreshList() {
  try {
    await saves.refresh()
  } catch (e) {
    message.value = e instanceof Error ? e.message : '读取存档列表失败'
    messageKind.value = 'err'
  }
}

watch(
  () => props.sessionId,
  () => {
    if (props.sessionId) void refreshList()
  },
  { immediate: true },
)

onMounted(() => {
  if (props.sessionId) void refreshList()
})

async function onSave(slot: number) {
  if (savingSlot.value !== null) return
  savingSlot.value = slot
  message.value = null
  try {
    const title = titleInput.value[slot]?.trim() || null
    await saves.saveManual(props.sessionId, slot, title)
    if (title) titleInput.value[slot] = ''
    message.value = `已保存到存档位 ${slot}`
    messageKind.value = 'ok'
  } catch (e) {
    message.value = e instanceof Error ? e.message : `保存失败（存档位 ${slot}）`
    messageKind.value = 'err'
  } finally {
    savingSlot.value = null
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-30 flex items-center justify-center bg-black/70"
    @click.self="emit('close')"
  >
    <div class="flex max-h-[85vh] w-[min(92vw,560px)] flex-col rounded-xl border border-white/15 bg-[#0b1424]/95 p-5 text-[#f4f8ff] shadow-2xl">
      <header class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-bold text-[#dff7ff]">保存</h2>
        <button class="text-sm text-[#d7effa]/70 hover:text-[#dff7ff]" @click="emit('close')">关闭</button>
      </header>

      <main class="flex flex-col gap-3 overflow-y-auto pr-1">
        <AutoSaveCard :save="saves.auto" mode="save" :busy="savingSlot !== null" />
        <div
          v-for="i in 6"
          :key="i"
          class="flex flex-col gap-1"
        >
          <div class="flex gap-1.5">
            <input
              v-model="titleInput[i]"
              class="min-w-0 flex-1 rounded border border-white/15 bg-black/40 px-2 py-1 text-xs text-[#d7effa] placeholder:text-[#d7effa]/35 focus:border-[#04bcff]/60 focus:outline-none"
              placeholder="存档标题（可选）"
              :disabled="savingSlot !== null || props.busy"
            />
            <button
              class="shrink-0 rounded border border-[#04bcff]/50 bg-[#0a2c4e]/80 px-2.5 py-1 text-xs text-[#9ff] transition-colors hover:bg-[#123c63] disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="savingSlot !== null || props.busy"
              @click="onSave(i)"
            >
              {{ savingSlot === i ? '保存中…' : '保存' }}
            </button>
          </div>
          <ManualSaveSlot :slot="i" :save="saves.manual[i - 1] ?? null" mode="view" :busy="savingSlot !== null || props.busy" />
        </div>
      </main>

      <footer class="mt-3 flex min-h-5 items-center justify-between text-xs">
        <p :class="messageKind === 'err' ? 'text-red-300' : 'text-[#a9e8ff]/80'">
          {{ message || (props.busy ? '当前对话尚未完成，请稍后保存（docs/13 §22）。' : ' ') }}
        </p>
        <button class="text-xs text-[#d7effa]/60 hover:text-[#dff7ff]" @click="emit('close')">返回</button>
      </footer>
    </div>
  </div>
</template>
