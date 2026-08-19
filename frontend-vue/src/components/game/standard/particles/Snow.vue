<!--
  Adapted from LingChat (AGPL-3.0): src/components/game/standard/particles/Snow.vue
  （含 config/snow.ts）
  Modification（docs/15 §3）：配置内联合并；其余原样适配。
-->
<template>
  <div class="snow-container" ref="containerRef">
    <div
      class="snowflake"
      v-for="(snowflake, index) in snowflakes"
      :key="index"
      :style="{
        fontSize: `${snowflake.size}px`,
        left: `${snowflake.left}px`,
        top: `${snowflake.top}px`,
        opacity: snowflake.opacity,
        animation: `fall-${snowflake.id} ${snowflake.duration}s linear ${snowflake.delay}s infinite`,
      }"
    >
      {{ snowflake.content }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  useFallingParticle,
  createDefaultParticle,
  createDefaultKeyframes,
  type FallingParticle,
  type FallingParticleConfig,
  type KeyframeConfig,
} from './useFallingParticle'

// LingChat config/snow.ts（内联，docs/15 §3）
const snowConfig: FallingParticleConfig = {
  minSize: 12,
  maxSize: 28,
  minDuration: 20,
  maxDuration: 35,
  maxDelay: 10,
  minOpacity: 0.3,
  maxOpacity: 1.0,
  horizontalRange: 50,
  initialTopOffset: -30,
  randomStartY: true,
}

const snowSettings = {
  baseCount: 50,
  chars: ['❄', '❅', '❆', '•', '·'] as const,
}

const snowKeyframes: KeyframeConfig = {
  rotation: {
    startRotation: 0,
    rotationRanges: [
      { min: 0, max: 90 },
      { min: 0, max: 180 },
      { min: 0, max: 270 },
      { min: 0, max: 360 },
    ],
  },
  opacity: {
    keyframes: [1, 0.95, 0.9, 0.8, 0.4],
  },
}

interface Props {
  enabled?: boolean
  intensity?: number
}

const containerRef = ref<HTMLElement | null>(null)

const props = withDefaults(defineProps<Props>(), {
  enabled: true,
  intensity: 1,
})

const createSnowflake = (id: string): FallingParticle => {
  const content = snowSettings.chars[Math.floor(Math.random() * snowSettings.chars.length)] || '❄'
  return createDefaultParticle(id, snowConfig, { content })
}

const generateSnowflakeKeyframes = (snowflake: FallingParticle, maxHeight: number): string => {
  return createDefaultKeyframes(snowflake, maxHeight, snowKeyframes)
}

const { particles: snowflakes } = useFallingParticle<FallingParticle>(
  props,
  {
    baseCount: snowSettings.baseCount,
    createParticle: createSnowflake,
    generateKeyframes: generateSnowflakeKeyframes,
  },
  containerRef,
)
</script>

<style scoped>
.snow-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.snowflake {
  position: absolute;
  color: white;
  text-align: center;
  user-select: none;
  pointer-events: none;
  text-shadow: 0 0 5px rgba(255, 255, 255, 0.5);
  opacity: 0.7;
  transform-origin: center;
}
</style>
