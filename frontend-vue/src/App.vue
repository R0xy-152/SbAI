<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useUiStore } from './stores/ui'
import { checkBackendHealth } from './api/game'
import CursorEffects from './components/effects/CursorEffects.vue'
import { useZoom } from './composables/useZoom'

// docs/15 §5.1：全局光标特效（teleport 到 body，避开 #app zoom 坐标偏移）。
// docs/15 §5.2：Ctrl+滚轮 UI 缩放。
const ui = useUiStore()

useZoom()

onMounted(() => {
  void checkBackendHealth()
    .then((ok) => (ui.backendOk = ok))
    .catch(() => (ui.backendOk = false))
})
</script>

<template>
  <!-- docs/15 §8：路由级淡入过渡，Title/Save/Load/Settings 不再生硬跳变 -->
  <RouterView v-slot="{ Component }">
    <Transition name="route-fade" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>

  <Teleport to="body">
    <CursorEffects />
  </Teleport>
</template>

<style>
.route-fade-enter-active,
.route-fade-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.22s ease;
}

.route-fade-enter-from {
  opacity: 0;
  transform: scale(1.01);
}

.route-fade-leave-to {
  opacity: 0;
  transform: scale(0.99);
}
</style>
