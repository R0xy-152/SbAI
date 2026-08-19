<script setup lang="ts">
// docs/14 §2.2（T2）：对话框上方气泡按钮条（D6）。选项列表由后端权威下发
// （GET /api/game/state options，D3 未解锁/已完成不下发），本组件只渲染与
// 回传，不解释 payload 含义（D7：执行仍走既有权威端点，由 GameView 负责）。
import type { GameOption } from '../../../api/game'

defineProps<{
  options: GameOption[]
  /** 执行中（调查/LLM 中间态）禁用所有气泡，防重复触发。 */
  busy: boolean
  /** 上一次选项执行的反馈文案（如调查完成提示）。 */
  feedback: string | null
  /** 粘性对话路由提示（「正在与 X 对话…」），null 表示公共对话。 */
  routeLabel: string | null
  /** 当前路由对应的选项 id（高亮该气泡）。 */
  activeRouteId: string | null
}>()

const emit = defineEmits<{ (e: 'select', option: GameOption): void }>()
</script>

<template>
  <div
    v-if="options.length || routeLabel || feedback"
    data-testid="options-panel"
    class="flex w-full flex-col items-center gap-1 pb-2"
  >
    <div class="flex max-w-full flex-wrap items-center justify-center gap-2 px-4">
      <button
        v-for="opt in options"
        :key="opt.id"
        :title="opt.hint ?? undefined"
        :disabled="busy"
        :class="
          activeRouteId === opt.id
            ? 'border-[#7fd4ff] bg-[#123c63] text-white'
            : 'border-[#7fd4ff]/40 bg-black/60 text-[#d7effa] hover:bg-[#123c63]/80'
        "
        class="rounded-full border px-3 py-1 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40"
        @click="emit('select', opt)"
      >
        {{ opt.label }}
      </button>
    </div>
    <!-- 路由提示与操作反馈可同时可见（feedback 不得被 routeLabel 遮蔽，
         docs/14 T4 E2E 复现：私审成功文案被路由行吞掉） -->
    <div v-if="routeLabel" class="px-4 text-xs text-[#a9e8ff]">
      {{ routeLabel }}
    </div>
    <div v-if="feedback" class="max-w-[560px] px-4 text-xs text-[#a9e8ff]/80">
      {{ feedback }}
    </div>
  </div>
</template>
