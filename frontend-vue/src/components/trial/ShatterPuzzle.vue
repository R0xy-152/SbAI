<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { TrialScene, TrialShardPose } from '../../api/trial'
import { AdaptivePhysicsQuality } from './performance'
import {
  allShardsSolved,
  createShardBodies,
  stepShardBodies,
  type ShardBody,
} from './shard-physics'
import TrialSceneSnapshot from './TrialSceneSnapshot.vue'
import { getFrozenFrame } from './mediaFrame'

const props = defineProps<{
  scene: TrialScene
  shardIds: string[]
}>()

const emit = defineEmits<{
  (event: 'complete', poses: TrialShardPose[]): void
}>()

const root = ref<HTMLElement | null>(null)
const bodies = ref<ShardBody[]>([])
const quality = new AdaptivePhysicsQuality()
const completed = ref(false)
const nearby = ref(new Set<string>())
// 碎裂源：视频场景用「异常时冻结的当前帧」（避免四片各自挂不同步视频）；静态场景为 null
const frozenFrame = ref<string | null>(null)

const masks = [
  'polygon(0 0,52% 0,48% 18%,53% 34%,50% 50%,31% 53%,18% 48%,0 52%)',
  'polygon(52% 0,100% 0,100% 48%,83% 52%,70% 47%,50% 50%,53% 34%,48% 18%)',
  'polygon(100% 48%,100% 100%,49% 100%,52% 83%,47% 68%,50% 50%,70% 47%,83% 52%)',
  'polygon(49% 100%,0 100%,0 52%,18% 48%,31% 53%,50% 50%,47% 68%,52% 83%)',
]
const origins = ['25% 25%', '75% 25%', '75% 75%', '25% 75%']

let frameId = 0
let lastFrame = 0
let frameAccumulator = 0
let resizeObserver: ResizeObserver | null = null

interface DragState {
  pointerId: number
  shardId: string
  lastX: number
  lastY: number
  lastTime: number
}
let drag: DragState | null = null

function initialize() {
  const rect = root.value?.getBoundingClientRect()
  if (!rect || rect.width <= 0 || rect.height <= 0) return
  if (bodies.value.length === 0) {
    bodies.value = createShardBodies(props.shardIds, rect.width, rect.height)
  }
}

function transformOf(body: ShardBody): string {
  return `translate3d(${body.x}px, ${body.y}px, 0) rotate(${body.rotation}deg)`
}

function tick(timestamp: number) {
  if (!lastFrame) lastFrame = timestamp
  const elapsed = Math.min(50, timestamp - lastFrame)
  lastFrame = timestamp
  quality.recordFrame(elapsed)
  frameAccumulator += elapsed
  if (frameAccumulator >= quality.targetFrameMs) {
    bodies.value = stepShardBodies(bodies.value, frameAccumulator / 1000, quality.quality)
    frameAccumulator = 0
    nearby.value = new Set(
      bodies.value
        .filter((body) => !body.snapped && Math.hypot(body.x, body.y) < body.snapRadius)
        .map((body) => body.id),
    )
    if (!completed.value && allShardsSolved(bodies.value)) {
      completed.value = true
      const rect = root.value?.getBoundingClientRect()
      const width = rect?.width || 1
      const height = rect?.height || 1
      emit(
        'complete',
        bodies.value.map((body) => ({
          shard_id: body.id,
          x: body.x / width,
          y: body.y / height,
          rotation: body.rotation,
        })),
      )
    }
  }
  frameId = requestAnimationFrame(tick)
}

function bodyById(id: string): ShardBody | undefined {
  return bodies.value.find((body) => body.id === id)
}

function onPointerDown(event: PointerEvent, shardId: string) {
  if (completed.value) return
  const body = bodyById(shardId)
  if (!body) return
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  body.dragging = true
  body.snapped = false
  body.vx = 0
  body.vy = 0
  drag = {
    pointerId: event.pointerId,
    shardId,
    lastX: event.clientX,
    lastY: event.clientY,
    lastTime: event.timeStamp,
  }
}

function onPointerMove(event: PointerEvent) {
  if (!drag || drag.pointerId !== event.pointerId) return
  const body = bodyById(drag.shardId)
  if (!body) return
  const dx = event.clientX - drag.lastX
  const dy = event.clientY - drag.lastY
  const dt = Math.max(8, event.timeStamp - drag.lastTime) / 1000
  body.x += dx
  body.y += dy
  body.vx = dx / dt
  body.vy = dy / dt
  body.angularVelocity += (dx - dy) * 0.018
  drag.lastX = event.clientX
  drag.lastY = event.clientY
  drag.lastTime = event.timeStamp
}

function onPointerUp(event: PointerEvent) {
  if (!drag || drag.pointerId !== event.pointerId) return
  const body = bodyById(drag.shardId)
  if (body) {
    body.dragging = false
    if (Math.hypot(body.x, body.y) < body.snapRadius * 0.9) {
      body.vx *= 0.18
      body.vy *= 0.18
      body.angularVelocity *= 0.3
    }
  }
  drag = null
}

function onShardKeydown(event: KeyboardEvent, shardId: string) {
  const body = bodyById(shardId)
  if (!body || completed.value) return
  const step = event.shiftKey ? 4 : 14
  if (event.key === 'ArrowLeft') body.x -= step
  else if (event.key === 'ArrowRight') body.x += step
  else if (event.key === 'ArrowUp') body.y -= step
  else if (event.key === 'ArrowDown') body.y += step
  else if (event.key === 'Enter' && Math.hypot(body.x, body.y) < body.snapRadius) {
    body.x = 0
    body.y = 0
    body.rotation = 0
    body.vx = 0
    body.vy = 0
    body.angularVelocity = 0
    body.snapped = true
  } else return
  event.preventDefault()
}

onMounted(() => {
  if (props.scene.video) frozenFrame.value = getFrozenFrame()
  initialize()
  if (root.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(initialize)
    resizeObserver.observe(root.value)
  }
  frameId = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frameId)
  resizeObserver?.disconnect()
})
</script>

<template>
  <div ref="root" class="shatter-puzzle" data-testid="shatter-puzzle">
    <div class="shatter-target" aria-hidden="true">
      <TrialSceneSnapshot :scene="scene" :frozen="frozenFrame" />
    </div>
    <div
      v-for="(body, index) in bodies"
      :key="body.id"
      class="shatter-piece"
      :class="{
        'shatter-piece--near': nearby.has(body.id),
        'shatter-piece--snapped': body.snapped,
      }"
      :style="{
        clipPath: masks[index],
        transformOrigin: origins[index],
        transform: transformOf(body),
      }"
      role="button"
      tabindex="0"
      :aria-label="`玻璃碎片 ${index + 1}${body.snapped ? '，已归位' : ''}`"
      @pointerdown="onPointerDown($event, body.id)"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @keydown="onShardKeydown($event, body.id)"
    >
      <TrialSceneSnapshot :scene="scene" :frozen="frozenFrame" />
      <div class="glass-sheen" aria-hidden="true"></div>
    </div>
    <div class="shatter-instruction" aria-live="polite">
      <strong>重组画面</strong>
      <span>拖动四块碎片靠近原位，进入光圈后会按真实惯性与弹簧力归位</span>
    </div>
  </div>
</template>

<style scoped>
.shatter-puzzle {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at center, rgba(25, 58, 74, 0.2), transparent 44%),
    #02050a;
  isolation: isolate;
}

.shatter-target {
  position: absolute;
  inset: 0;
  opacity: 0.085;
  filter: grayscale(0.4) brightness(1.4);
}

.shatter-target::after {
  content: '';
  position: absolute;
  inset: 8%;
  border: 1px solid rgba(133, 226, 255, 0.32);
  box-shadow: 0 0 46px rgba(96, 214, 255, 0.16);
}

.shatter-piece {
  position: absolute;
  inset: 0;
  cursor: grab;
  touch-action: none;
  user-select: none;
  will-change: transform;
  filter:
    drop-shadow(0 0 1px rgba(235, 252, 255, 1))
    drop-shadow(0 12px 13px rgba(0, 0, 0, 0.72))
    drop-shadow(0 0 14px rgba(124, 225, 255, 0.2));
  transition: filter 140ms ease;
}

.shatter-piece:active { cursor: grabbing; }
.shatter-piece:focus-visible { outline: 3px solid #92e7ff; outline-offset: -5px; }
.shatter-piece--near {
  filter:
    drop-shadow(0 0 2px rgba(255, 255, 255, 1))
    drop-shadow(0 0 21px rgba(94, 223, 255, 0.95));
}
.shatter-piece--snapped { cursor: default; }

.glass-sheen {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.22;
  background:
    linear-gradient(115deg, transparent 16%, rgba(255, 255, 255, 0.28) 20%, transparent 24%),
    linear-gradient(290deg, transparent 65%, rgba(150, 235, 255, 0.2) 69%, transparent 74%);
  mix-blend-mode: screen;
}

.shatter-instruction {
  position: absolute;
  top: clamp(1rem, 4vh, 2.5rem);
  left: 50%;
  z-index: 10;
  display: grid;
  gap: 0.3rem;
  width: min(34rem, calc(100% - 2rem));
  padding: 0.8rem 1.1rem;
  transform: translateX(-50%);
  border: 1px solid rgba(136, 228, 255, 0.38);
  border-radius: 999px;
  color: #e8fbff;
  background: rgba(2, 11, 18, 0.78);
  box-shadow: 0 0 28px rgba(56, 185, 231, 0.14);
  text-align: center;
  pointer-events: none;
  backdrop-filter: blur(10px);
}
.shatter-instruction strong { color: #9cecff; letter-spacing: 0.28em; }
.shatter-instruction span { font-size: 0.78rem; color: #c8e8f2; }
.shatter-instruction small { color: #7fb4c3; font-size: 0.68rem; }

@media (prefers-reduced-motion: reduce) {
  .shatter-piece { transition: none; }
  .glass-sheen { display: none; }
}
</style>
