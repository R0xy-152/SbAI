<script setup lang="ts">
// 快速上线固定剧本 · 选项窗口（临时组件）。
// 实现借鉴 LingChat GameChoices（components/game/standard/extra/GameChoices.vue，
// AGPL 参考源码）：全屏悬浮胶囊按钮组（无面板卡片）、交错入场动画
//（100ms 逐个上浮 + 回弹缓动）、选择后缩放渐隐离场、悬停微光扫射 + 漂浮粒子。
// 差异：本组件只渲染「必须选择」的剧本 A/B/C 选项（无禁用态），选择后回传
// /api/story/choose；配色沿用本项目皮肤 token（#04bcff / slate 玻璃）。
import { ref } from 'vue'
import type { StoryOptionView } from '../../../api/story'

const props = defineProps<{
  options: StoryOptionView[]
  busy: boolean
}>()

const emit = defineEmits<{ (e: 'select', id: string): void }>()

// 选择后先播离场动画再回传（与 LingChat「清空 choices 触发交错渐隐」同语义：
// 点选项 → 全组缩放渐隐 → 提交），避免窗口瞬间消失。
const picked = ref(false)
function select(option: StoryOptionView) {
  if (props.busy || picked.value) return
  picked.value = true
  setTimeout(() => emit('select', option.id), 300)
}

// LingChat GameChoices 同款 JS 动画钩子（:css="false" 的 transition-group）
function choiceBeforeEnter(el: Element) {
  const element = el as HTMLElement
  element.style.opacity = '0'
  element.style.transform = 'translateY(30px)'
  element.style.transition = 'all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)'
}

function choiceEnter(el: Element, done: () => void) {
  const element = el as HTMLElement
  const index = parseInt(element.dataset.index || '0', 10)
  requestAnimationFrame(() => {
    setTimeout(() => {
      element.style.opacity = '1'
      element.style.transform = 'translateY(0)'
      setTimeout(done, 500)
    }, index * 100)
  })
}

function choiceLeave(el: Element, done: () => void) {
  const element = el as HTMLElement
  element.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
  element.style.opacity = '0'
  element.style.transform = 'scale(0.95)'
  setTimeout(done, 300)
}
</script>

<template>
  <div
    class="pointer-events-none fixed inset-0 z-[40] mt-[-15vh] flex flex-col items-center justify-center"
    data-testid="story-choice-window"
  >
    <transition-group
      appear
      :css="false"
      tag="div"
      class="pointer-events-auto flex w-full max-w-2xl flex-col gap-10 px-4"
      @before-enter="choiceBeforeEnter"
      @enter="choiceEnter"
      @leave="choiceLeave"
    >
      <button
        v-for="(opt, index) in options"
        :key="opt.id"
        :data-index="index"
        :disabled="busy || picked"
        class="group relative w-full rounded-full border border-white/10 bg-slate-900/40 px-8 py-4 text-sm shadow-[0_4px_12px_rgba(0,0,0,0.3)] backdrop-blur-xl backdrop-saturate-150 transition-all duration-200 hover:-translate-y-1 hover:border-[#04bcff] hover:shadow-[0_0_15px_rgba(0,0,0,0.5)] hover:ring-2 hover:ring-[#04bcff]/20 disabled:cursor-not-allowed disabled:opacity-60"
        :class="picked ? 'scale-95 opacity-0' : ''"
        @click="select(opt)"
      >
        <!-- 静态粒子（小圆点，悬停变亮） -->
        <div class="absolute inset-0 opacity-30 transition-opacity duration-700 group-hover:opacity-50">
          <div class="absolute top-2 left-4 h-1 w-1 rounded-full bg-white/60"></div>
          <div class="absolute top-6 left-8 h-0.5 w-0.5 rounded-full bg-blue-300/50"></div>
          <div class="absolute top-4 left-16 h-1.5 w-1.5 rounded-full bg-[#04bcff]/40 blur-[1px]"></div>
          <div class="absolute top-3 right-6 h-1 w-1 rounded-full bg-white/40"></div>
          <div class="absolute top-8 right-12 h-0.5 w-0.5 rounded-full bg-purple-300/50"></div>
          <div class="absolute top-5 right-20 h-1 w-1 rounded-full bg-[#04bcff]/30 blur-[1px]"></div>
          <div class="absolute top-1/2 left-10 h-0.5 w-0.5 rounded-full bg-cyan-300/40"></div>
          <div class="absolute top-1/2 right-12 h-1 w-1 rounded-full bg-white/30"></div>
          <div class="absolute bottom-4 left-8 h-1 w-1 rounded-full bg-[#04bcff]/30"></div>
          <div class="absolute bottom-8 right-10 h-0.5 w-0.5 rounded-full bg-blue-300/40"></div>
          <div class="absolute bottom-3 right-16 h-1.5 w-1.5 rounded-full bg-white/20 blur-[1px]"></div>
        </div>

        <!-- 动态漂浮粒子（悬停时出现） -->
        <div class="absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-40">
          <div class="animate-float absolute top-2 left-4 h-1 w-1 rounded-full bg-white/60"></div>
          <div class="animate-float-slow absolute bottom-6 right-8 h-0.5 w-0.5 rounded-full bg-[#04bcff]/60"></div>
          <div class="animate-float-reverse absolute top-8 right-12 h-1 w-1 rounded-full bg-purple-400/50"></div>
          <div class="animate-float-slow absolute bottom-10 left-12 h-1.5 w-1.5 rounded-full bg-cyan-300/40 blur-[1px]"></div>
          <div class="animate-float absolute top-1/3 right-20 h-1 w-1 rounded-full bg-white/40"></div>
        </div>

        <!-- 悬停微光扫射 -->
        <div class="absolute inset-0 overflow-hidden rounded-full opacity-0 transition-opacity duration-700 group-hover:opacity-100">
          <div class="animate-shine absolute top-0 -inset-full z-5 block h-full w-1/2 -skew-x-12 bg-linear-to-r from-transparent via-white/10 to-transparent"></div>
        </div>

        <span
          class="block text-center text-lg font-medium tracking-widest text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)] group-hover:text-white"
        >
          {{ opt.label }}
        </span>
      </button>
    </transition-group>
  </div>
</template>

<style scoped>
/* LingChat GameChoices 同款动画（AGPL 参考源码移植） */
@keyframes float {
  0%,
  100% {
    transform: translateY(0) translateX(0);
  }
  25% {
    transform: translateY(-4px) translateX(2px);
  }
  50% {
    transform: translateY(0) translateX(4px);
  }
  75% {
    transform: translateY(4px) translateX(0);
  }
}

@keyframes float-slow {
  0%,
  100% {
    transform: translateY(0) translateX(0);
  }
  33% {
    transform: translateY(-3px) translateX(-2px);
  }
  66% {
    transform: translateY(2px) translateX(3px);
  }
}

@keyframes float-reverse {
  0%,
  100% {
    transform: translateY(0) translateX(0);
  }
  33% {
    transform: translateY(3px) translateX(-3px);
  }
  66% {
    transform: translateY(-2px) translateX(2px);
  }
}

@keyframes shine {
  100% {
    left: 200%;
  }
}

.animate-float {
  animation: float 6s ease-in-out infinite;
}
.animate-float-slow {
  animation: float-slow 8s ease-in-out infinite;
}
.animate-float-reverse {
  animation: float-reverse 7s ease-in-out infinite;
}
.animate-shine {
  animation: shine 3s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .animate-float,
  .animate-float-slow,
  .animate-float-reverse,
  .animate-shine {
    animation: none;
  }
}
</style>
