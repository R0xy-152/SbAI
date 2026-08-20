<script setup lang="ts">
// docs/16 P7：线索窗口 —— 调查成功后展示获得证据的标题 + 描述（docs/10 证据
// registry 的 title/summary）。纯展示，关闭后继续剧情。
defineProps<{ title: string; summary: string }>()
const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div
    class="pointer-events-auto fixed inset-0 z-[40] flex items-center justify-center bg-black/50 backdrop-blur-[2px]"
    data-testid="clue-window-backdrop"
  >
    <div class="gal-panel w-full max-w-lg p-6" data-testid="clue-window">
      <h2 class="mb-2 text-xs tracking-[0.25em] text-[#a9e8ff]/70">线索</h2>
      <h3 class="mb-3 text-xl font-bold text-[#dff7ff]">{{ title }}</h3>
      <p class="mb-6 whitespace-pre-line text-sm leading-relaxed text-[#d7effa]">{{ summary }}</p>
      <button class="gal-link-btn w-full" data-testid="clue-window-close" @click="emit('close')">
        关闭
      </button>
    </div>
  </div>
</template>
