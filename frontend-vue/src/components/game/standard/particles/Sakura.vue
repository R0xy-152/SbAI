<!--
  Adapted from LingChat (AGPL-3.0): src/components/game/standard/particles/Sakura.vue
  （含 config/sakura.ts）
  Modification（docs/15 §3）：配置内联合并；其余原样适配。
-->
<template>
  <div class="petal-container" ref="containerRef">
    <div
      class="petal"
      v-for="(petal, index) in petals"
      :key="index"
      :style="{
        width: `${petal.size}px`,
        height: `${petal.size}px`,
        left: `${petal.left}px`,
        top: `${petal.top}px`,
        opacity: petal.opacity,
        background: `linear-gradient(135deg, hsl(${petal.hue}, 100%, 85%), hsl(${petal.hue}, 100%, 75%))`,
        animation: `fall-${petal.id} ${petal.duration}s linear ${petal.delay}s infinite`,
      }"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  useFallingParticle,
  createDefaultParticle,
  createDefaultKeyframes,
  randomInRange,
  type FallingParticle,
  type FallingParticleConfig,
  type KeyframeConfig,
} from './useFallingParticle'

// LingChat config/sakura.ts（内联，docs/15 §3）
const sakuraConfig: FallingParticleConfig = {
  minSize: 10,
  maxSize: 20,
  minDuration: 15,
  maxDuration: 25,
  maxDelay: 10,
  minOpacity: 0.4,
  maxOpacity: 0.9,
  horizontalRange: 50,
  initialTopOffset: -30,
  randomStartY: true,
}

const sakuraSettings = {
  baseCount: 25,
  hueMin: 320,
  hueMax: 330,
}

const sakuraKeyframes: KeyframeConfig = {
  rotation: {
    startRotation: 0,
    rotationRanges: [
      { min: 90, max: 180 },
      { min: 180, max: 270 },
      { min: 270, max: 360 },
      { min: 360, max: 540 },
    ],
  },
  opacity: {
    keyframes: [1, 0.9, 0.7, 0.5, 0],
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

const createPetal = (id: string): FallingParticle => {
  const hue = randomInRange(sakuraSettings.hueMin, sakuraSettings.hueMax)
  return createDefaultParticle(id, sakuraConfig, { hue })
}

const generatePetalKeyframes = (petal: FallingParticle, maxHeight: number): string => {
  return createDefaultKeyframes(petal, maxHeight, sakuraKeyframes)
}

const { particles: petals } = useFallingParticle<FallingParticle>(
  props,
  {
    baseCount: sakuraSettings.baseCount,
    createParticle: createPetal,
    generateKeyframes: generatePetalKeyframes,
  },
  containerRef,
)
</script>

<style scoped>
.petal-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.petal {
  position: absolute;
  border-radius: 50% 0 50% 50%;
  opacity: 0.7;
  filter: drop-shadow(0 0 5px rgba(255, 182, 193, 0.5));
  transform-origin: center;
}
</style>
