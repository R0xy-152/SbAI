<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '../stores/settings'

// 设置页（docs/13 §12.5 + docs/15 §5.3）：文字/音频 + 显示特效开关。
// 全部持久化到 localStorage（gal_settings）；显示特效默认开，关闭后
// 首页星星/流星、光标特效、场景粒子、加载演出即时停用（docs/15 §5）。
const router = useRouter()
const settings = useSettingsStore()

const effectToggles = computed(() => [
  { key: 'stars', label: '首页星星粒子', hint: '主菜单背景星空', model: settings.mainMenuStarsEnabled },
  { key: 'meteors', label: '首页流星', hint: '主菜单划过的流星', model: settings.mainMenuMeteorsEnabled },
  { key: 'trail', label: '光标拖尾', hint: '鼠标移动光点轨迹', model: settings.globalMouseTrailEnabled },
  { key: 'click', label: '点击涟漪', hint: '点击时的扩散光圈', model: settings.clickAnimationEnabled },
  { key: 'scene', label: '场景粒子特效', hint: '游戏内雨/雪/星空等氛围粒子', model: settings.sceneEffectsEnabled },
  { key: 'loading', label: '首次加载演出', hint: '新游戏开场进度动画', model: settings.loadingTransitionEnabled },
  { key: 'eyeOpen', label: '睁眼转场', hint: '进入游戏画面时的黑幕睁眼动画', model: settings.eyeOpenTransitionEnabled },
])
</script>

<template>
  <div class="gal-page text-[#f4f8ff]">
    <div class="gal-page-bg"></div>
    <div class="gal-page-scrim"></div>

    <main class="relative z-10 mx-auto flex h-full w-full max-w-xl flex-col px-4 py-6">
      <header class="mb-4 flex items-center justify-between">
        <h1 class="text-xl font-bold tracking-[0.2em] text-[#dff7ff] drop-shadow-lg">设置</h1>
        <button class="gal-link-btn" @click="router.push('/')">返回标题</button>
      </header>

      <div class="gal-panel flex-1 gap-6 overflow-y-auto p-6">
        <!-- 文字与音频 -->
        <section>
          <h2 class="mb-3 text-sm font-bold tracking-wider text-[#a9e8ff]/80">文字与音频</h2>
          <label class="mb-5 block">
            <span class="mb-2 flex items-center justify-between text-sm text-[#d7effa]">
              <span>文字速度</span>
              <span class="tabular-nums text-xs text-[#a9e8ff]/70">{{ settings.textSpeed.toFixed(1) }}×</span>
            </span>
            <input
              v-model.number="settings.textSpeed"
              class="gal-range"
              type="range"
              min="0.5"
              max="2"
              step="0.1"
            />
          </label>
          <label class="mb-5 block">
            <span class="mb-2 flex items-center justify-between text-sm text-[#d7effa]">
              <span>BGM 音量</span>
              <span class="tabular-nums text-xs text-[#a9e8ff]/70">{{ Math.round(settings.bgmVolume * 100) }}%</span>
            </span>
            <input
              v-model.number="settings.bgmVolume"
              class="gal-range"
              type="range"
              min="0"
              max="1"
              step="0.05"
            />
          </label>
          <label class="block">
            <span class="mb-2 flex items-center justify-between text-sm text-[#d7effa]">
              <span>音效音量</span>
              <span class="tabular-nums text-xs text-[#a9e8ff]/70">{{ Math.round(settings.sfxVolume * 100) }}%</span>
            </span>
            <input
              v-model.number="settings.sfxVolume"
              class="gal-range"
              type="range"
              min="0"
              max="1"
              step="0.05"
            />
          </label>
        </section>

        <!-- 显示特效（docs/15 §5.3） -->
        <section class="border-t border-white/10 pt-5">
          <h2 class="mb-3 text-sm font-bold tracking-wider text-[#a9e8ff]/80">显示特效</h2>
          <label
            v-for="item in effectToggles"
            :key="item.key"
            class="flex items-center justify-between gap-3 py-2"
          >
            <span class="flex flex-col">
              <span class="text-sm text-[#d7effa]">{{ item.label }}</span>
              <span class="text-xs text-[#a9e8ff]/55">{{ item.hint }}</span>
            </span>
            <input v-model="item.model" class="gal-toggle" type="checkbox" />
          </label>
        </section>

        <p class="mt-auto border-t border-white/10 pt-4 text-xs text-[#a9e8ff]/50">
          提示：游戏内可用 Ctrl + 滚轮 缩放界面（Ctrl + 0 复位）。
        </p>
      </div>
    </main>
  </div>
</template>
