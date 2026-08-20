<script setup lang="ts">
// 快速上线固定剧本 · 结局画面（临时组件）：SC14「RECOVERY REQUIRED」播完后
// 显示「第一章 完 / To Be Continued」，提供返回标题。
const emit = defineEmits<{ (e: 'return-title'): void }>()
</script>

<template>
  <div
    class="pointer-events-auto fixed inset-0 z-[50] flex flex-col items-center justify-center gap-6 bg-black/80 backdrop-blur-sm"
    data-testid="story-ending"
  >
    <h1 class="text-3xl font-bold tracking-[0.3em] text-[#f4f8ff]">第一章 完</h1>
    <p class="text-lg tracking-[0.2em] text-[#a9e8ff]">《03:17 Incident》</p>
    <p class="text-sm tracking-[0.4em] text-[#d7effa]/70">TO BE CONTINUED</p>
    <button class="gal-link-btn mt-6" data-testid="story-ending-return" @click="emit('return-title')">
      返回标题
    </button>
  </div>
</template>
