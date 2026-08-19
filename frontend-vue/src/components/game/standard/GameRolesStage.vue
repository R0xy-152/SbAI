<template>
  <div class="absolute w-full h-full overflow-hidden">
    <!-- 1. 遍历渲染所有在场角色 -->
    <RoleAvatar
      v-for="role in gameStore.presentRolesList"
      :key="role.roleId"
      :role="role"
    />

    <!-- 2. 场景光照叠加层 -->
    <div
      v-if="lightOverlayStyle"
      class="absolute inset-0 pointer-events-none z-10"
      :style="lightOverlayStyle"
    ></div>
  </div>
</template>

<script setup lang="ts">
// Adapted from LingChat (AGPL-3.0): src/components/game/standard/GameRolesStage.vue
// Modification: replaced useGameStore/useUIStore with 本项目 Mock 兼容层；
// removed 主语音播放器（getVoiceAudio / audio events，docs/13 §11.3 音频可移除）。
import { computed } from 'vue'
import { useGameStore } from '../../../adapters/lingchat-compat'
import RoleAvatar from './GameRoleAvatar.vue'

const gameStore = useGameStore()

const lightOverlayStyle = computed(() => {
  const l = gameStore.currentScene?.lighting
  if (!l || !l.overlay_enabled) return undefined
  if (l.overlay_target !== 'character' && l.overlay_target !== 'both') return undefined
  const blend = l.blend_mode !== 'normal' ? l.blend_mode : 'overlay'
  return `background: radial-gradient(circle at ${l.light_x}% ${l.light_y}%, ${l.overlay_color1} 0%, ${l.overlay_color2} ${l.overlay_radius}%); mix-blend-mode: ${blend}; opacity: ${l.overlay_opacity}`
})
</script>
