<script setup lang="ts">
// docs/16 P7/P8：选项窗口（lingchat 式竖排选项）。取代 docs/14 D6 的气泡按钮条：
// 选项由后端权威下发（D3），本组件只渲染与回传；「继续对话」关闭项保证 D4
// 自由输入始终可用。chat_routing 粘性高亮由 activeRouteId 承担。
import type { GameOption } from '../../../api/game'

defineProps<{
  options: GameOption[]
  busy: boolean
  activeRouteId: string | null
}>()

const emit = defineEmits<{ (e: 'select', option: GameOption): void; (e: 'dismiss'): void }>()
</script>

<template>
  <div
    class="pointer-events-auto fixed inset-0 z-[40] flex items-center justify-center bg-black/45 backdrop-blur-[2px]"
    data-testid="option-window-backdrop"
  >
    <div class="gal-panel w-full max-w-md p-6" data-testid="option-window">
      <h2 class="mb-4 text-sm font-bold tracking-[0.2em] text-[#a9e8ff]/80">选择行动</h2>
      <div class="flex max-h-[60vh] flex-col gap-2 overflow-y-auto pr-1">
        <button
          v-for="opt in options"
          :key="opt.id"
          :disabled="busy"
          :title="opt.hint ?? undefined"
          :class="
            activeRouteId === opt.id
              ? 'border-[#7fd4ff] bg-[#123c63] text-white'
              : 'border-white/15 bg-black/40 text-[#d7effa] hover:bg-[#123c63]/80'
          "
          class="rounded-lg border px-4 py-3 text-left text-base transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          @click="emit('select', opt)"
        >
          {{ opt.label }}
        </button>
      </div>
      <button
        class="gal-link-btn mt-4 w-full"
        data-testid="option-window-dismiss"
        @click="emit('dismiss')"
      >
        继续对话
      </button>
    </div>
  </div>
</template>
