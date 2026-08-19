<script setup lang="ts">
import type { GameSaveInfo } from '../../api/saves'
import { chapterPhaseLabel, formatTime, slotTitle } from '../../utils/save-format'

// 自动存档卡（docs/13 Task 7：AutoSaveCard）。T2review P2-4 / P1-6：AUTO 槽
// 由后端 checkpoint 独占写入，save 模式下不是可点击控件（此前是死按钮）；
// 仅在 load 模式渲染为可点击按钮。
const props = defineProps<{
  save: GameSaveInfo | null
  mode: 'save' | 'load'
  busy?: boolean
}>()

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <button
    v-if="mode === 'load'"
    class="group flex w-full flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60"
    :class="
      save
        ? 'border-[#2a4a75] bg-[#0d1a30]/80 hover:bg-[#16304f]/80'
        : 'border-white/10 bg-black/30 hover:bg-white/5'
    "
    :disabled="busy || !save"
    :title="save ? '读取自动存档' : ''"
    @click="emit('action')"
  >
    <div class="flex items-baseline gap-2">
      <span class="text-sm font-bold text-[#ffd86b]">自动存档</span>
      <span v-if="save" class="min-w-0 flex-1 truncate text-sm text-[#dff7ff]">
        {{ slotTitle(save) }}
      </span>
      <span v-else class="text-xs text-[#d7effa]/30">暂无自动存档</span>
    </div>
    <div v-if="save" class="flex items-center gap-3 text-xs text-[#a9e8ff]/70">
      <span class="min-w-0 flex-1 truncate">{{ chapterPhaseLabel(save) }}</span>
      <span class="shrink-0 tabular-nums">{{ formatTime(save.updated_at) }}</span>
    </div>
    <div v-else class="text-xs text-[#d7effa]/30">暂无自动存档</div>
  </button>

  <div
    v-else
    class="flex w-full flex-col gap-1 rounded-lg border px-4 py-3 text-left"
    :class="save ? 'border-[#2a4a75] bg-[#0d1a30]/80' : 'border-white/10 bg-black/30'"
    title="自动存档由后端 checkpoint 写入，不可手动覆盖"
  >
    <div class="flex items-baseline gap-2">
      <span class="text-sm font-bold text-[#ffd86b]">自动存档</span>
      <span v-if="save" class="min-w-0 flex-1 truncate text-sm text-[#dff7ff]">
        {{ slotTitle(save) }}
      </span>
      <span v-else class="text-xs text-[#d7effa]/30">暂无自动存档</span>
    </div>
    <div v-if="save" class="flex items-center gap-3 text-xs text-[#a9e8ff]/70">
      <span class="min-w-0 flex-1 truncate">{{ chapterPhaseLabel(save) }}</span>
      <span class="shrink-0 tabular-nums">{{ formatTime(save.updated_at) }}</span>
    </div>
    <div v-else class="text-xs text-[#d7effa]/30">暂无自动存档</div>
  </div>
</template>
