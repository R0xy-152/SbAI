<template>
  <Transition name="scene-card" @after-leave="emit('complete')">
    <div
      v-if="visible"
      class="pointer-events-none fixed inset-0 z-40 flex items-center justify-center"
      data-testid="scene-title-card"
    >
      <div class="scene-card-inner">
        <p class="scene-card-title">{{ title }}</p>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
// 场景标题卡（docs/17 演出接线）：场景切换时淡入 → 停留 → 淡出。
// 标题文本来自后端场景数据（剧本已有 scene title），前端不自行写作。
import { onMounted, onUnmounted, ref } from 'vue'

const props = defineProps<{ title: string }>()
const emit = defineEmits<{ (e: 'complete'): void }>()

const visible = ref(false)
let hideTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  requestAnimationFrame(() => {
    visible.value = true
  })
  hideTimer = setTimeout(() => {
    visible.value = false
  }, 1800)
})

onUnmounted(() => {
  if (hideTimer) clearTimeout(hideTimer)
})
</script>

<style scoped>
.scene-card-inner {
  padding: 0.6rem 2.2rem;
  border: 1px solid rgba(169, 232, 255, 0.25);
  border-radius: 2px;
  background: rgba(4, 8, 16, 0.55);
  backdrop-filter: blur(6px);
  box-shadow: 0 0 24px rgba(0, 180, 255, 0.12);
}

.scene-card-title {
  margin: 0;
  font-size: 1.35rem;
  letter-spacing: 0.35em;
  color: #e8f8ff;
  text-shadow: 0 0 12px rgba(140, 220, 255, 0.55);
}

.scene-card-enter-active {
  transition: opacity 0.45s ease, transform 0.45s ease;
}

.scene-card-leave-active {
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.scene-card-enter-from,
.scene-card-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
