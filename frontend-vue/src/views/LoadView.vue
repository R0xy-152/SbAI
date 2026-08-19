<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import LoadPanel from '../components/save/LoadPanel.vue'
import { useGameStore } from '../stores/game'
import { useSavesStore } from '../stores/saves'

// 读取存档页（docs/13 §12.4 / §20.3）：Load 创建新 Active Session，返回
// new_session_id + GameViewState，暂存 game.pendingLoad 后进入 GameView，
// 由 GameView 挂载时消费渲染。
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
    await router.push('/game')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="flex h-full flex-col bg-[#10131d] text-[#f4f8ff]">
    <header class="flex items-center justify-between border-b border-white/10 px-4 py-2">
      <span class="text-sm text-[#a9e8ff]">读取存档</span>
      <button class="text-sm text-[#d7effa]/70 hover:text-[#dff7ff]" @click="router.push('/')">返回标题</button>
    </header>
    <main class="mx-auto w-full max-w-2xl flex-1 overflow-auto px-4 py-6">
      <LoadPanel
        embedded
        :busy="busy"
        @load="onLoad"
        @close="router.push('/')"
      />
      <p v-if="error" class="mt-3 text-center text-sm text-red-300">{{ error }}</p>
    </main>
  </div>
</template>
