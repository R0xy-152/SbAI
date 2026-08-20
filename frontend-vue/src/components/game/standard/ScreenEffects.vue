<template>
  <!-- 屏幕故障特效层（SCREEN_GLITCH）：场景入场脉冲播放；
       SCREEN_SHAKE 由视图根节点绑定 .screen-shake（样式在本文件全局段）。
       纯表现、pointer-events-none，不挡任何交互（docs/17 演出接线）。 -->
  <div v-if="glitch" class="screen-glitch-overlay" data-testid="screen-glitch">
    <div class="glitch-scanlines"></div>
    <div class="glitch-flash"></div>
    <div class="glitch-tear glitch-tear-1"></div>
    <div class="glitch-tear glitch-tear-2"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ effects: string[] }>()

const glitch = computed(() => props.effects.includes('SCREEN_GLITCH'))
</script>

<style>
/* 全局段：.screen-shake 供 GameView / StoryView 根节点绑定 */
.screen-glitch-overlay {
  position: fixed;
  inset: 0;
  z-index: 30;
  pointer-events: none;
  overflow: hidden;
  mix-blend-mode: screen;
}

.glitch-scanlines {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(120, 255, 240, 0.12) 0 1px,
    transparent 1px 3px
  );
  animation: glitch-scanlines 0.9s steps(3) infinite;
}

.glitch-flash {
  position: absolute;
  inset: 0;
  animation: glitch-flash 0.9s steps(2) infinite;
}

/* 横向撕裂条（RGB 位移质感） */
.glitch-tear {
  position: absolute;
  left: 0;
  right: 0;
  height: 14%;
  background: linear-gradient(
    90deg,
    transparent 0 18%,
    rgba(90, 255, 240, 0.22) 18% 22%,
    transparent 22% 46%,
    rgba(255, 90, 200, 0.2) 46% 50%,
    transparent 50% 74%,
    rgba(120, 200, 255, 0.2) 74% 78%,
    transparent 78%
  );
  animation: glitch-tear 0.7s steps(4) infinite;
}

.glitch-tear-1 { top: 12%; }
.glitch-tear-2 { top: 58%; animation-delay: 0.24s; }

@keyframes glitch-scanlines {
  0%, 100% { opacity: 0.9; }
  25% { opacity: 0.2; }
  50% { opacity: 0.6; }
  75% { opacity: 0.1; }
}

@keyframes glitch-flash {
  0%, 100% { background: rgba(0, 255, 255, 0.05); }
  15% { background: rgba(0, 255, 255, 0.22); }
  30% { background: rgba(255, 0, 180, 0.12); }
  45% { background: rgba(0, 255, 255, 0.08); }
  60% { background: rgba(180, 255, 255, 0.25); }
  80% { background: rgba(255, 0, 180, 0.14); }
}

@keyframes glitch-tear {
  0%, 100% { transform: translateX(-1.2%); opacity: 0.9; }
  30% { transform: translateX(1.4%); opacity: 0.4; }
  55% { transform: translateX(-0.6%); opacity: 0.8; }
  80% { transform: translateX(1.8%); opacity: 0.3; }
}

/* SCREEN_SHAKE：视图根节点绑定类，持续期间小幅度抖动（脉冲播放） */
.screen-shake {
  animation: screen-shake 0.5s linear infinite;
}

@keyframes screen-shake {
  0%, 100% { transform: translate(0, 0); }
  10% { transform: translate(-6px, 2px); }
  20% { transform: translate(5px, -3px); }
  30% { transform: translate(-4px, -2px); }
  40% { transform: translate(4px, 3px); }
  50% { transform: translate(-3px, 1px); }
  60% { transform: translate(3px, -2px); }
  70% { transform: translate(-2px, 2px); }
  80% { transform: translate(2px, -1px); }
  90% { transform: translate(-1px, 1px); }
}

@media (prefers-reduced-motion: reduce) {
  .screen-glitch-overlay,
  .screen-shake {
    animation: none !important;
    display: none;
  }
}
</style>
