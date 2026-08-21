<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useUiStore } from './stores/ui'
import { checkBackendHealth } from './api/game'
import CursorEffects from './components/effects/CursorEffects.vue'
import { useZoom } from './composables/useZoom'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

// docs/15 §5.1：全局光标特效（teleport 到 body，避开 #app zoom 坐标偏移）。
// docs/15 §5.2：Ctrl+滚轮 UI 缩放。
const ui = useUiStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

useZoom()

onMounted(() => {
  void checkBackendHealth()
    .then((ok) => (ui.backendOk = ok))
    .catch(() => (ui.backendOk = false))
})

async function logout() {
  await auth.logout()
  await router.replace('/login')
}
</script>

<template>
  <!-- docs/15 §8：路由级淡入过渡，Title/Save/Load/Settings 不再生硬跳变 -->
  <RouterView v-slot="{ Component }">
    <Transition name="route-fade" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>

  <aside v-if="auth.user && route.name !== 'login'" class="account-status">
    <span>{{ auth.user.display_name }}</span>
    <strong>AI 剩余 {{ auth.user.quota_remaining }} 次</strong>
    <button type="button" @click="logout">退出</button>
  </aside>

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

.account-status {
  position: fixed;
  top: 12px;
  right: 16px;
  z-index: 10000;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border: 1px solid rgba(116, 218, 255, 0.3);
  border-radius: 999px;
  color: #dff8ff;
  background: rgba(2, 12, 22, 0.78);
  backdrop-filter: blur(10px);
  font-size: 12px;
}

.account-status strong { color: #78ddff; }
.account-status button { color: #b9cbd3; background: none; border: 0; cursor: pointer; }
.account-status button:hover { color: white; }
</style>
