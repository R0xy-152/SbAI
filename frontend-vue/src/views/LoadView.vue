<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useSavesStore } from '../stores/saves'

const router = useRouter()
const saves = useSavesStore()
</script>

<template>
  <div class="flex h-full flex-col bg-[#10131d] text-[#f4f8ff]">
    <header class="flex items-center justify-between border-b border-white/10 px-4 py-2">
      <span class="text-sm text-[#a9e8ff]">读取存档</span>
      <button class="text-sm text-[#d7effa]/70 hover:text-[#dff7ff]" @click="router.push('/')">返回标题</button>
    </header>
    <main class="mx-auto w-full max-w-2xl flex-1 overflow-auto px-4 py-6">
      <h2 class="mb-2 text-sm font-bold text-[#dff7ff]">自动存档</h2>
      <div class="mb-6 rounded border border-white/15 p-4 text-sm text-[#d7effa]/60">
        {{ saves.auto ? '自动存档存在' : '暂无自动存档' }}
      </div>
      <h2 class="mb-2 text-sm font-bold text-[#dff7ff]">手动存档</h2>
      <div class="grid gap-2">
        <div v-for="(slot, i) in saves.manual" :key="i" class="rounded border border-white/15 p-4 text-sm text-[#d7effa]/60">
          {{ slot ? slot.title : `存档位 ${i + 1}（空）` }}
        </div>
      </div>
      <p class="mt-6 text-xs text-[#a9e8ff]/70">存档系统在 Task 6/7 接入后可用。</p>
    </main>
  </div>
</template>
