<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useUiStore } from '../stores/ui'

const router = useRouter()
const game = useGameStore()
const ui = useUiStore()

async function newGame() {
  await game.startNewSession()
  if (game.error) return
  router.push('/game')
}
</script>

<template>
  <div class="flex h-full flex-col items-center justify-center overflow-hidden bg-[#10131d] text-[#f4f8ff]">
    <h1 class="mb-10 text-center text-4xl font-bold tracking-widest text-[#dff7ff] drop-shadow-lg">
      完蛋，我被AI娘包围了
    </h1>
    <nav class="flex flex-col items-center gap-3">
      <button class="title-btn" :disabled="game.busy" @click="newGame">开始游戏</button>
      <button class="title-btn" disabled title="暂无可继续的存档（Task 5 接入）">继续游戏</button>
      <button class="title-btn" @click="router.push('/load')">读取存档</button>
      <button class="title-btn" @click="router.push('/settings')">设置</button>
    </nav>
    <p v-if="game.error" class="mt-5 max-w-sm text-center text-sm text-red-300">{{ game.error }}</p>
    <p v-else class="mt-5 text-xs text-[#a9e8ff]/70">
      {{ ui.backendOk === true ? '后端已连接' : ui.backendOk === false ? '后端未连接' : '连接后端中…' }}
    </p>
  </div>
</template>

<style scoped>
.title-btn {
  width: 13rem;
  padding: 0.7rem 1rem;
  border: 1px solid rgba(211, 234, 255, 0.55);
  border-radius: 0.5rem;
  background: rgba(7, 12, 24, 0.8);
  color: #d7effa;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s ease;
}
.title-btn:hover:not(:disabled) {
  background: rgba(30, 48, 78, 0.9);
}
.title-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
