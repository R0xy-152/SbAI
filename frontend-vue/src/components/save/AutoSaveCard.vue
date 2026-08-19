<script setup lang="ts">
import type { GameSaveInfo } from '../../api/saves'
import { chapterPhaseLabel, formatTime, slotTitle } from '../../utils/save-format'

// 自动存档卡（docs/13 Task 7：AutoSaveCard）。单卡展示唯一 AUTO slot，
// 动作（保存/读取）由父级（SavePanel/LoadPanel）传入。删除仅对手动 slot
// 定义（docs/13 §20 只有 DELETE /api/saves/manual/{slot}），此处不提供。
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
    class="group flex w-full flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60"
    :class="
      save
        ? 'border-[#2a4a75] bg-[#0d1a30]/80 hover:bg-[#16304f]/80'
        : 'border-white/10 bg-black/30 hover:bg-white/5'
    "
    :disabled="busy || !save"
    :title="save ? (mode === 'save' ? '覆盖自动存档' : '读取自动存档') : ''"
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
</template>
