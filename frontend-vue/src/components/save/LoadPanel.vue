<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useSavesStore } from '../../stores/saves'
import AutoSaveCard from './AutoSaveCard.vue'
import ManualSaveSlot from './ManualSaveSlot.vue'

// 读取面板（docs/13 §12.4 / §13.2）：读 Auto + 6 Manual。由 LoadView（标题
// 进入，embedded 内嵌渲染）与游戏内系统菜单（overlay 弹出）共用：点击 slot
// 触发 load(saveId) 回调，由父级决定「加载后如何进入 GameView」。删除仅
// 手动 slot（docs/13 §20）。docs/15 §8：统一皮肤（embedded 模式自身不带
// 面板边框，由 LoadView 的 gal-panel 承载）。
const props = defineProps<{
  /** true = 内嵌于 LoadView 页面流（非 overlay）。 */
  embedded?: boolean
  busy?: boolean
}>()

const emit = defineEmits<{
  load: [saveId: string]
  close: []
}>()

const saves = useSavesStore()
const deletingSlot = ref<number | null>(null)
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

onMounted(() => {
  void refreshList()
})

function onLoad(saveId: string) {
  emit('load', saveId)
}

async function onDelete(slot: number) {
  if (deletingSlot.value !== null) return
  deletingSlot.value = slot
  message.value = null
  try {
    await saves.deleteManual(slot)
    message.value = `已删除存档位 ${slot}`
    messageKind.value = 'ok'
  } catch (e) {
    message.value = e instanceof Error ? e.message : '删除存档失败'
    messageKind.value = 'err'
  } finally {
    deletingSlot.value = null
  }
}
</script>

<template>
  <div
    :class="embedded ? '' : 'gal-modal-mask'"
    @click.self="!embedded && emit('close')"
  >
    <div
      :class="embedded ? 'flex flex-col' : 'gal-panel max-h-[85vh] w-[min(92vw,560px)] p-5'"
      class="text-[#f4f8ff]"
    >
      <header v-if="!embedded" class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-bold tracking-[0.15em] text-[#dff7ff] drop-shadow">读取存档</h2>
        <button class="gal-link-btn" @click="emit('close')">关闭</button>
      </header>

      <main class="flex flex-col gap-3 overflow-y-auto pr-1">
        <AutoSaveCard
          :save="saves.auto"
          mode="load"
          :busy="deletingSlot !== null || props.busy"
          @action="saves.auto && onLoad(saves.auto.id)"
        />
        <ManualSaveSlot
          v-for="i in 6"
          :key="i"
          :slot="i"
          :save="saves.manual[i - 1] ?? null"
          mode="load"
          :busy="deletingSlot !== null || props.busy"
          @action="(s: number) => { const save = saves.manual[s - 1]; if (save) onLoad(save.id) }"
          @delete="onDelete"
        />
      </main>

      <footer class="mt-3 flex min-h-5 items-center justify-between text-xs">
        <p :class="messageKind === 'err' ? 'text-red-300' : 'text-[#a9e8ff]/80'">
          {{ message || (saves.loading ? '读取存档列表…' : ' ') }}
        </p>
        <button
          v-if="!embedded"
          class="gal-link-btn"
          @click="emit('close')"
        >
          返回
        </button>
      </footer>
    </div>
  </div>
</template>
