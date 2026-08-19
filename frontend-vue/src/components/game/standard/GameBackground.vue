<template>
  <!-- 背景图 + 背景光照滤镜（docs/13 §11.1；docs/15 §6 第二轮补齐粒子层） -->
  <div
    v-if="backgroundSrc"
    class="absolute inset-0"
    :style="bgLightingFilter"
  >
    <ImageAcrossFade
      ref="imageFadeRef"
      class="game-background"
      :src="backgroundSrc"
      position="center center"
      object-fit="cover"
      :duration="uiStore.currentBackgroundTransition"
    />
  </div>

  <!-- 场景粒子层（docs/15 §6.2）：按后端权威 background_effect 渲染五种粒子
       之一；sceneEffectsEnabled=false 或 effect 为 null 时整层不渲染。
       isolation:isolate 建立独立层叠上下文，粒子 z-index 不会逃逸盖 UI。 -->
  <div
    v-if="sceneEffectsEnabled && currentEffect"
    class="pointer-events-none absolute inset-0"
    style="isolation: isolate"
  >
    <StarField
      v-if="currentEffect === 'StarField'"
      :enabled="true"
      :star-count="200"
      :scroll-speed="0.2"
    />
    <Rain v-else-if="currentEffect === 'Rain'" :enabled="true" :intensity="1" />
    <Sakura v-else-if="currentEffect === 'Sakura'" :enabled="true" :intensity="1" />
    <Snow v-else-if="currentEffect === 'Snow'" :enabled="true" :intensity="1" />
    <Fireworks v-else-if="currentEffect === 'Fireworks'" :enabled="true" :intensity="1" />
  </div>

  <!-- 背景光照叠加层（在背景上方、角色下方） -->
  <div
    v-if="bgOverlayStyle"
    class="pointer-events-none absolute inset-0"
    :style="bgOverlayStyle as any"
  ></div>
</template>

<script setup lang="ts">
// Adapted from LingChat (AGPL-3.0): src/components/game/standard/GameBackground.vue
// Modification: replaced convertFileSrc (HTTP 静态资源，走兼容层)；
// removed 粒子特效（StarField/Rain/Sakura/Snow/Fireworks）、背景音乐
// （AudioAcrossFade）、环境音（AmbientLoopPlayer）与音效播放 —— docs/13 §11.1
// 第一轮不迁移、无相关素材；仅保留背景图 + 光照滤镜。
import { computed } from 'vue'
import { useUIStore, useGameStore } from '../../../adapters/lingchat-compat'
import { useSettingsStore } from '../../../stores/settings'
import ImageAcrossFade from './ui/ImageAcrossFade.vue'
import { StarField, Rain, Sakura, Snow, Fireworks } from './particles'

const uiStore = useUIStore()
const gameStore = useGameStore()
const settingsStore = useSettingsStore()

const backgroundSrc = computed(() => uiStore.currentBackground || '')

// docs/15 §6.2：场景粒子氛围层（后端权威 effect + 设置总开关）
const currentEffect = computed(() => uiStore.currentBackgroundEffect || '')
const sceneEffectsEnabled = computed(() => settingsStore.sceneEffectsEnabled)

// 背景光照滤镜
const bgLightingFilter = computed(() => {
  const c = gameStore.currentScene?.lighting?.background
  if (!c) return undefined
  const parts: string[] = []
  if (c.brightness !== undefined && c.brightness !== 1.0) parts.push(`brightness(${c.brightness})`)
  if (c.contrast !== undefined && c.contrast !== 1.0) parts.push(`contrast(${c.contrast})`)
  if (c.saturation !== undefined && c.saturation !== 1.0) parts.push(`saturate(${c.saturation})`)
  if (c.glow_radius !== undefined && c.glow_radius > 0) parts.push(`drop-shadow(0 0 ${c.glow_radius}px ${c.glow_color})`)
  if (c.sepia !== undefined && c.sepia > 0) parts.push(`sepia(${c.sepia})`)
  return parts.length > 0 ? { filter: parts.join(' ') } : undefined
})

// 背景光照叠加层（仅当 target 为 background 或 both 时启用）
const bgOverlayStyle = computed(() => {
  const l = gameStore.currentScene?.lighting
  if (!l || !l.overlay_enabled) return undefined
  if (l.overlay_target !== 'background' && l.overlay_target !== 'both') return undefined
  const blend = l.blend_mode !== 'normal' ? l.blend_mode : 'overlay'
  return {
    background: `radial-gradient(circle at ${l.light_x}% ${l.light_y}%, ${l.overlay_color1} 0%, ${l.overlay_color2} ${l.overlay_radius}%)`,
    mixBlendMode: blend,
    opacity: l.overlay_opacity,
  }
})
</script>

<style scoped>
.game-background {
  position: absolute;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center center;
  background-attachment: fixed;
  background-repeat: no-repeat;
  /* T2review P1-12：负 z-index 会把背景压到 GameView 黑色根节点之后，
     视觉基线因此把纯黑固化为「正确」。改回正常流内堆叠（角色舞台 z-1 在其上）。 */
  z-index: 0;
}
</style>
