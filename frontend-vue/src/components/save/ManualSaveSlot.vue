<script setup lang="ts">
import type { GameSaveInfo } from '../../api/saves'
import { chapterPhaseLabel, formatTime, slotTitle } from '../../utils/save-format'

// 单个手动存档 slot（docs/13 Task 7：ManualSaveSlot x6）。
// T2review P2-4：卡片主体与「删除」按钮不得嵌套（原实现 button-in-button）；
// 改为外层容器 + 主体按钮 + 独立删除按钮。
const props = defineProps<{
  slot: number
  save: GameSaveInfo | null
  mode: 'save' | 'load' | 'view'
  busy?: boolean
}>()

const emit = defineEmits<{
  action: [slot: number]
  delete: [slot: number]
}>()
</script>

<template>
  <div class="relative">
    <button
      class="flex w-full flex-col gap-1 rounded-lg border px-4 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60"
      :class="
        save
          ? 'border-[#2a4a75] bg-[#0d1a30]/80 hover:bg-[#16304f]/80'
          : 'border-white/10 bg-black/30 hover:bg-white/5'
      "
      :disabled="busy"
      :title="save ? (mode === 'save' ? '覆盖此存档位' : mode === 'load' ? '读取此存档' : '') : ''"
      @click="emit('action', slot)"
    >
      <div class="flex items-baseline gap-2">
        <span class="text-sm font-bold text-[#04bcff]">存档位 {{ slot }}</span>
        <span v-if="save" class="min-w-0 flex-1 truncate text-sm text-[#dff7ff]">
          {{ slotTitle(save, slot) }}
        </span>
        <span v-else class="text-xs text-[#d7effa]/40">空存档位</span>
      </div>
      <div v-if="save" class="flex items-center gap-3 text-xs text-[#a9e8ff]/70">
        <span class="min-w-0 flex-1 truncate">{{ chapterPhaseLabel(save) }}</span>
        <span class="shrink-0 tabular-nums">{{ formatTime(save.updated_at) }}</span>
      </div>
      <div v-else class="text-xs text-[#d7effa]/30">暂无存档</div>
    </button>
    <button
      v-if="save && mode === 'load'"
      class="absolute right-2 top-2 rounded border border-red-300/30 bg-[#0b1424]/80 px-1.5 py-0.5 text-[10px] text-red-300/80 transition-colors hover:bg-red-500/20 disabled:opacity-40"
      :disabled="busy"
      title="删除此存档"
      @click.stop="emit('delete', slot)"
    >
      删除
    </button>
  </div>
</template>
