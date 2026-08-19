<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useSettingsStore } from '../stores/settings'

const router = useRouter()
const settings = useSettingsStore()
</script>

<template>
  <div class="flex h-full flex-col bg-[#10131d] text-[#f4f8ff]">
    <header class="flex items-center justify-between border-b border-white/10 px-4 py-2">
      <span class="text-sm text-[#a9e8ff]">设置</span>
      <button class="text-sm text-[#d7effa]/70 hover:text-[#dff7ff]" @click="router.push('/')">返回标题</button>
    </header>
    <main class="mx-auto w-full max-w-xl flex-1 px-4 py-6">
      <label class="mb-4 block text-sm">
        <span class="text-[#d7effa]">文字速度</span>
        <input v-model.number="settings.textSpeed" type="range" min="0.5" max="2" step="0.1" class="mt-2 w-full" />
      </label>
      <label class="mb-4 block text-sm">
        <span class="text-[#d7effa]">BGM 音量</span>
        <input v-model.number="settings.bgmVolume" type="range" min="0" max="1" step="0.05" class="mt-2 w-full" />
      </label>
      <label class="mb-4 block text-sm">
        <span class="text-[#d7effa]">音效音量</span>
        <input v-model.number="settings.sfxVolume" type="range" min="0" max="1" step="0.05" class="mt-2 w-full" />
      </label>
    </main>
  </div>
</template>
