<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import LoadPanel from '../components/save/LoadPanel.vue'
import { useGameStore } from '../stores/game'
import { useSavesStore } from '../stores/saves'
import { saveTargetRoute } from '../api/saves'

// 读取存档页（docs/13 §12.4 / §20.3）：Load 创建新 Active Session，返回
// new_session_id + GameViewState，暂存 game.pendingLoad 后进入 GameView，
// 由 GameView 挂载时消费渲染。docs/15 §8：与 Title/Settings 共享页壳皮肤。
const router = useRouter()
const game = useGameStore()
const saves = useSavesStore()

const busy = ref(false)
const error = ref<string | null>(null)

async function onLoad(saveId: string) {
  if (busy.value) return
  busy.value = true
  error.value = null
  try {
    const result = await saves.load(saveId)
    game.pendingLoad = result
    localStorage.removeItem('gal_session_id')
    // 故事未完结 → /story；已完结 / 旧玩法 → /game（docs/17）
    await router.push(
      saveTargetRoute(result.story_cursor, result.story_finished, result.experience_id),
    )
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="gal-page text-[#f4f8ff]">
    <div class="gal-page-bg"></div>
    <div class="gal-page-scrim"></div>

    <main class="relative z-10 mx-auto flex h-full w-full max-w-2xl flex-col px-4 py-6">
      <header class="mb-4 flex items-center justify-between">
        <h1 class="text-xl font-bold tracking-[0.2em] text-[#dff7ff] drop-shadow-lg">读取存档</h1>
        <button class="gal-link-btn" @click="router.push('/')">返回标题</button>
      </header>

      <div class="gal-panel flex-1 overflow-hidden p-5">
        <LoadPanel embedded :busy="busy" @load="onLoad" @close="router.push('/')" />
      </div>
      <p v-if="error" class="mt-3 text-center text-sm text-red-300 drop-shadow">{{ error }}</p>
    </main>
  </div>
</template>
