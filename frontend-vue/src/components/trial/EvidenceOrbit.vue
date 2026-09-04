<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { TrialEvidence } from '../../api/trial'
import { AdaptivePhysicsQuality } from './performance'
import {
  createOrbitBodies,
  DEFAULT_ORBIT_CONFIG,
  stepOrbitBodies,
  type OrbitBody,
} from './physics'

const props = withDefaults(
  defineProps<{
    evidence: TrialEvidence[]
    selectedIds: string[]
    seed?: number
  }>(),
  { seed: 31704 },
)

const emit = defineEmits<{
  (event: 'inspect', evidenceId: string): void
  (event: 'drop', payload: { evidenceId: string; clientX: number; clientY: number }): void
}>()

const root = ref<HTMLElement | null>(null)
const bodies = ref<OrbitBody[]>([])
const quality = new AdaptivePhysicsQuality()
const qualityLabel = computed(() =>
  quality.quality === 'high' ? '高精度' : quality.quality === 'balanced' ? '平衡' : '节能',
)

let frameId = 0
let lastFrame = 0
let accumulator = 0
let resizeObserver: ResizeObserver | null = null

interface DragState {
  pointerId: number
  evidenceId: string
  startX: number
  startY: number
  lastX: number
  lastY: number
  lastTime: number
  moved: boolean
}
let drag: DragState | null = null

const visibleEvidence = computed(() =>
  props.evidence.filter((item) => !props.selectedIds.includes(item.evidence_id)),
)

function bounds() {
  const rect = root.value?.getBoundingClientRect()
  return { width: Math.max(1, rect?.width ?? 1), height: Math.max(1, rect?.height ?? 1) }
}

function syncBodies() {
  const area = bounds()
  const visibleIds = visibleEvidence.value.map((item) => item.evidence_id)
  const existing = new Map(bodies.value.map((body) => [body.id, body]))
  const created = createOrbitBodies(visibleIds, area, props.seed)
  bodies.value = visibleIds.map(
    (id, index) => existing.get(id) ?? created[index],
  )
}

function bodyFor(id: string): OrbitBody | undefined {
  return bodies.value.find((body) => body.id === id)
}

function transformOf(id: string): string {
  const body = bodyFor(id)
  return body ? `translate3d(${body.x}px, ${body.y}px, 0) translate(-50%, -50%)` : ''
}

function tick(timestamp: number) {
  if (!lastFrame) lastFrame = timestamp
  const elapsed = Math.min(50, timestamp - lastFrame)
  lastFrame = timestamp
  quality.recordFrame(elapsed)
  accumulator += elapsed
  if (accumulator >= quality.targetFrameMs) {
    bodies.value = stepOrbitBodies(
      bodies.value,
      bounds(),
      accumulator / 1000,
      DEFAULT_ORBIT_CONFIG,
      quality.substeps,
    )
    accumulator = 0
  }
  frameId = requestAnimationFrame(tick)
}

function onPointerDown(event: PointerEvent, evidenceId: string) {
  const body = bodyFor(evidenceId)
  if (!body) return
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  body.dragged = true
  drag = {
    pointerId: event.pointerId,
    evidenceId,
    startX: event.clientX,
    startY: event.clientY,
    lastX: event.clientX,
    lastY: event.clientY,
    lastTime: event.timeStamp,
    moved: false,
  }
}

function onPointerMove(event: PointerEvent) {
  if (!drag || drag.pointerId !== event.pointerId) return
  const body = bodyFor(drag.evidenceId)
  const rect = root.value?.getBoundingClientRect()
  if (!body || !rect) return
  const dx = event.clientX - drag.lastX
  const dy = event.clientY - drag.lastY
  const dt = Math.max(8, event.timeStamp - drag.lastTime) / 1000
  body.x = Math.max(30, Math.min(rect.width - 30, body.x + dx))
  body.y = Math.max(30, Math.min(rect.height - 30, body.y + dy))
  body.vx = dx / dt
  body.vy = dy / dt
  body.dragged = true
  drag.moved ||= Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) > 6
  drag.lastX = event.clientX
  drag.lastY = event.clientY
  drag.lastTime = event.timeStamp
}

function onPointerUp(event: PointerEvent) {
  if (!drag || drag.pointerId !== event.pointerId) return
  const body = bodyFor(drag.evidenceId)
  if (body) body.dragged = false
  if (drag.moved) {
    emit('drop', {
      evidenceId: drag.evidenceId,
      clientX: event.clientX,
      clientY: event.clientY,
    })
  } else {
    emit('inspect', drag.evidenceId)
  }
  drag = null
}

watch(() => [visibleEvidence.value.map((item) => item.evidence_id).join(','), props.seed], syncBodies)

onMounted(() => {
  syncBodies()
  if (root.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(syncBodies)
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
  <section ref="root" class="evidence-orbit" data-testid="evidence-orbit">
    <div class="orbit-grid" aria-hidden="true"></div>
    <div class="orbit-status">
      <span>文字天体场</span>
      <small>等质量 · {{ qualityLabel }}</small>
    </div>
    <button
      v-for="item in visibleEvidence"
      :key="item.evidence_id"
      class="evidence-body"
      :style="{ transform: transformOf(item.evidence_id) }"
      type="button"
      :aria-label="`${item.title}：点击查看，拖动选择`"
      @pointerdown="onPointerDown($event, item.evidence_id)"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
    >
      <span>{{ item.title }}</span>
    </button>
    <p v-if="visibleEvidence.length === 0" class="orbit-empty">证据均已移入推理槽</p>
  </section>
</template>

<style scoped>
.evidence-orbit {
  position: relative;
  min-width: 0;
  min-height: 24rem;
  overflow: hidden;
  border: 1px solid rgba(116, 222, 255, 0.3);
  border-radius: 1rem;
  background:
    radial-gradient(circle at 51% 48%, rgba(45, 112, 142, 0.17), transparent 38%),
    rgba(1, 7, 13, 0.78);
  box-shadow: inset 0 0 80px rgba(0, 0, 0, 0.52);
  touch-action: none;
}

.orbit-grid {
  position: absolute;
  inset: 0;
  opacity: 0.18;
  background-image:
    linear-gradient(rgba(104, 210, 244, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(104, 210, 244, 0.12) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(circle, black, transparent 79%);
}

.orbit-status {
  position: absolute;
  top: 0.8rem;
  left: 1rem;
  z-index: 2;
  display: flex;
  gap: 0.75rem;
  align-items: baseline;
  color: #87ddf7;
  letter-spacing: 0.12em;
  pointer-events: none;
}
.orbit-status small { color: #6e9da9; font-size: 0.67rem; }

.evidence-body {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 3;
  width: 7.2rem;
  height: 3rem;
  border: 1px solid rgba(145, 233, 255, 0.58);
  border-radius: 999px;
  color: #e5faff;
  background:
    linear-gradient(115deg, rgba(8, 25, 37, 0.94), rgba(11, 47, 61, 0.86));
  box-shadow:
    0 0 0 1px rgba(57, 144, 171, 0.16),
    0 0 22px rgba(64, 196, 235, 0.18);
  font-size: 1rem;
  font-weight: 750;
  letter-spacing: 0.12em;
  cursor: grab;
  user-select: none;
  will-change: transform;
}
.evidence-body::after {
  content: '';
  position: absolute;
  inset: -0.35rem;
  border: 1px solid rgba(124, 222, 250, 0.12);
  border-radius: inherit;
}
.evidence-body:hover,
.evidence-body:focus-visible {
  border-color: #b5f2ff;
  box-shadow: 0 0 26px rgba(89, 218, 255, 0.54);
  outline: none;
}
.evidence-body:active { cursor: grabbing; }

.orbit-empty {
  position: absolute;
  inset: 50% auto auto 50%;
  margin: 0;
  color: #6f9eaa;
  transform: translate(-50%, -50%);
}

@media (prefers-reduced-motion: reduce) {
  .evidence-body { box-shadow: 0 0 8px rgba(64, 196, 235, 0.16); }
}
</style>
