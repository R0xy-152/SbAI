<script setup lang="ts">
// 快速上线固定剧本 · 选项窗口（临时组件）：渲染后端下发的 A/B/C 剧本选项。
// 与 OptionWindow（docs/16 P7/P8，调查玩法）不同：剧本选项必须选择，
// 没有「继续对话」关闭项；选择即提交 /api/story/choose。
import type { StoryOptionView } from '../../../api/story'

defineProps<{
  options: StoryOptionView[]
  busy: boolean
}>()

const emit = defineEmits<{ (e: 'select', id: string): void }>()
</script>

<template>
  <div
    class="pointer-events-auto fixed inset-0 z-[40] flex items-center justify-center bg-black/45 backdrop-blur-[2px]"
    data-testid="story-choice-window"
  >
    <div class="gal-panel w-full max-w-md p-6">
      <h2 class="mb-4 text-sm font-bold tracking-[0.2em] text-[#a9e8ff]/80">选择</h2>
      <div class="flex max-h-[60vh] flex-col gap-2 overflow-y-auto pr-1">
        <button
          v-for="opt in options"
          :key="opt.id"
          :disabled="busy"
          class="rounded-lg border border-white/15 bg-black/40 px-4 py-3 text-left text-base text-[#d7effa] transition-colors hover:bg-[#123c63]/80 disabled:cursor-not-allowed disabled:opacity-40"
          @click="emit('select', opt.id)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>
  </div>
</template>
