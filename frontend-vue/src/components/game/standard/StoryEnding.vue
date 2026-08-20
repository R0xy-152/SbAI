<script setup lang="ts">
// 快速上线固定剧本 · 结局画面（临时组件）：SC14「RECOVERY REQUIRED」播完后
// 显示「第一章 完 / To Be Continued」；返回标题，或进入结局后自由聊天
//（/game 复用同一会话，AI 回复由 DeepSeek 提供，docs/17）。
const emit = defineEmits<{
  (e: 'return-title'): void
  (e: 'continue-chat'): void
}>()
</script>

<template>
  <div
    class="pointer-events-auto fixed inset-0 z-[50] flex flex-col items-center justify-center gap-6 bg-black/80 backdrop-blur-sm"
    data-testid="story-ending"
  >
    <h1 class="text-3xl font-bold tracking-[0.3em] text-[#f4f8ff]">第一章 完</h1>
    <p class="text-lg tracking-[0.2em] text-[#a9e8ff]">《03:17 Incident》</p>
    <p class="text-sm tracking-[0.4em] text-[#d7effa]/70">TO BE CONTINUED</p>
    <div class="mt-6 flex items-center gap-6">
      <button class="gal-link-btn" data-testid="story-ending-chat" @click="emit('continue-chat')">
        继续聊天
      </button>
      <button class="gal-link-btn" data-testid="story-ending-return" @click="emit('return-title')">
        返回标题
      </button>
    </div>
  </div>
</template>
