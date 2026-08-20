<script setup lang="ts">
// docs/16 P5：黑幕眼睑式睁眼转场 —— 全屏黑幕中间一道缝，上下「眼皮」分开
// 露出画面，约 1s。pointer-events:none 不拦截点击；prefers-reduced-motion
// 直接完成（不播动画）。纯 CSS 过渡，无素材依赖。
import { onMounted, onUnmounted, ref } from 'vue'

const emit = defineEmits<{ (e: 'complete'): void }>()

const DURATION = 1000
const opening = ref(false)

const prefersReducedMotion =
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

let timer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  if (prefersReducedMotion) {
    emit('complete')
    return
  }
  // 下一帧再触发过渡，保证初始「闭眼」状态先渲染一帧
  requestAnimationFrame(() => {
    opening.value = true
  })
  timer = setTimeout(() => emit('complete'), DURATION + 120)
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <div class="pointer-events-none fixed inset-0 z-[60] overflow-hidden" data-testid="eye-open">
    <div class="eyelid eyelid-top" :class="{ open: opening }"></div>
    <div class="eyelid eyelid-bottom" :class="{ open: opening }"></div>
  </div>
</template>

<style scoped>
.eyelid {
  position: absolute;
  left: 0;
  width: 100%;
  height: 50%;
  background: #000;
  transition: transform 1s cubic-bezier(0.33, 0.05, 0.23, 1);
  will-change: transform;
}
.eyelid-top {
  top: 0;
}
.eyelid-bottom {
  bottom: 0;
}
.eyelid-top.open {
  transform: translateY(-100%);
}
.eyelid-bottom.open {
  transform: translateY(100%);
}
</style>
