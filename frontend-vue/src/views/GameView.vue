<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'

const router = useRouter()
const game = useGameStore()

const speakerName = computed(() => {
  const c = game.lastResponse?.character_id ?? ''
  return c === 'deepseek' ? 'DeepSeek' : c
})

onMounted(() => {
  if (!game.sessionId) void game.startNewSession()
})
</script>

<template>
  <div class="flex h-full flex-col bg-[#10131d] text-[#f4f8ff]">
    <header class="flex items-center justify-between border-b border-white/10 px-4 py-2">
      <span class="text-sm text-[#a9e8ff]">第一章 · 被困的房间</span>
      <button class="text-sm text-[#d7effa]/70 hover:text-[#dff7ff]" @click="router.push('/')">
        返回标题
      </button>
    </header>

    <!-- 角色舞台：Task 2 迁入 GameRolesStage / GameRoleAvatar 后替换 -->
    <main class="flex flex-1 items-center justify-center px-6">
      <p v-if="game.busy" class="text-[#a9e8ff]">DeepSeek 正在思考…</p>
      <p v-else-if="game.error" class="text-red-300">{{ game.error }}</p>
      <p v-else-if="game.lastResponse" class="max-w-2xl text-center leading-relaxed">
        <span class="font-bold text-[#a9e8ff]">{{ speakerName }}</span><br />
        <span class="mt-2 inline-block">{{ game.lastResponse.dialogue }}</span>
      </p>
      <p v-else class="text-[#d7effa]/60">等待开始…</p>
    </main>

    <!-- 玩家输入：Task 4 接入真实发送；当前仅占位 -->
    <footer class="px-4 py-3">
      <div class="flex gap-2">
        <input
          class="flex-1 rounded border border-[#87d6f4]/40 bg-[#071018] px-3 py-2 text-[#f6f9ff] outline-none placeholder:text-[#d7effa]/40"
          :disabled="!game.canInput"
          placeholder="输入…"
        />
        <button class="rounded bg-[#87d6f4] px-4 font-bold text-[#06121b] disabled:opacity-50">发送</button>
      </div>
    </footer>
  </div>
</template>
