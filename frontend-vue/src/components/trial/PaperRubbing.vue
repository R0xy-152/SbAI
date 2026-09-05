<script setup lang="ts">
// 【复用旧废案】移植 frontend-deprecated/app.js 的「纸上拓印」小游戏
// （docs/14 §1 拓印小游戏 / docs/23 §2.2 被绑开场前期实验）。
// 玩家在纸面移动指针涂擦铅笔灰，压痕文字逐渐显影；刮够覆盖度后揭晓密码。
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps<{ answer: string }>()
const emit = defineEmits<{ (event: 'complete'): void }>()

const surface = ref<HTMLElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)
const revealed = ref(false)

const GRID_COLUMNS = 28
const GRID_ROWS = 15
const COMPLETE_COVERAGE = 0.38

let graphiteCanvas: HTMLCanvasElement | null = null
let context: CanvasRenderingContext2D | null = null
let graphiteContext: CanvasRenderingContext2D | null = null
const coveredCells = new Set<string>()
let width = 0
let height = 0
let pixelRatio = 1
let previousPoint: { x: number; y: number } | null = null

function drawPaperTexture(target: CanvasRenderingContext2D) {
  target.fillStyle = '#e7dfce'
  target.fillRect(0, 0, width, height)
  target.globalCompositeOperation = 'multiply'
  for (let index = 0; index < (width * height) / 170; index += 1) {
    const shade = 184 + ((index * 37) % 34)
    target.fillStyle = `rgba(${shade}, ${shade - 8}, ${shade - 20}, .12)`
    target.fillRect((index * 71) % width, (index * 43) % height, 1, 1)
  }
  target.globalCompositeOperation = 'source-over'
}

function drawImprint(target: CanvasRenderingContext2D, alpha = 1) {
  const centerX = width * 0.5
  const centerY = height * 0.5
  target.save()
  target.translate(centerX, centerY)
  target.rotate(-0.045)
  target.textAlign = 'center'
  target.textBaseline = 'middle'
  const words = (offsetX: number, offsetY: number, color: string) => {
    target.fillStyle = color
    target.font = '700 30px Georgia, serif'
    target.fillText(props.answer, offsetX, offsetY - 14)
    target.font = '600 15px ui-monospace, Consolas, monospace'
    target.fillText('—— 密码', offsetX, offsetY + 22)
  }
  words(2, 2, `rgba(67, 49, 36, ${0.23 * alpha})`)
  words(0, 0, `rgba(248, 240, 224, ${0.84 * alpha})`)
  target.restore()
}

function liftImprint() {
  if (!graphiteContext) return
  graphiteContext.save()
  graphiteContext.globalCompositeOperation = 'destination-out'
  drawImprint(graphiteContext, 0.93)
  graphiteContext.restore()
}

function renderPaper() {
  if (!context) return
  context.save()
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  drawPaperTexture(context)
  if (graphiteCanvas) context.drawImage(graphiteCanvas, 0, 0, width, height)
  drawImprint(context, Math.max(0.12, coveredCells.size / (GRID_COLUMNS * GRID_ROWS)))
  context.restore()
}

function resizePaper() {
  const el = surface.value
  if (!el) return
  const bounds = el.getBoundingClientRect()
  const nextWidth = Math.max(1, Math.round(bounds.width))
  const nextHeight = Math.max(1, Math.round(bounds.height))
  if (nextWidth === width && nextHeight === height) return
  width = nextWidth
  height = nextHeight
  pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
  if (canvas.value) {
    canvas.value.width = width * pixelRatio
    canvas.value.height = height * pixelRatio
  }
  graphiteCanvas = graphiteCanvas ?? document.createElement('canvas')
  graphiteCanvas.width = width * pixelRatio
  graphiteCanvas.height = height * pixelRatio
  graphiteContext = graphiteCanvas.getContext('2d')
  graphiteContext?.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  liftImprint()
  renderPaper()
}

function markCoverage(from: { x: number; y: number }, to: { x: number; y: number }) {
  const distance = Math.max(1, Math.hypot(to.x - from.x, to.y - from.y))
  for (let step = 0; step <= distance; step += 7) {
    const progress = step / distance
    const x = from.x + (to.x - from.x) * progress
    const y = from.y + (to.y - from.y) * progress
    const column = Math.min(GRID_COLUMNS - 1, Math.max(0, Math.floor((x / width) * GRID_COLUMNS)))
    const row = Math.min(GRID_ROWS - 1, Math.max(0, Math.floor((y / height) * GRID_ROWS)))
    coveredCells.add(`${column}:${row}`)
  }
}

function depositGraphite(from: { x: number; y: number }, to: { x: number; y: number }) {
  if (!graphiteContext) return
  const dx = to.x - from.x
  const dy = to.y - from.y
  const length = Math.max(1, Math.hypot(dx, dy))
  const normalX = -dy / length
  const normalY = dx / length
  graphiteContext.save()
  graphiteContext.lineCap = 'round'
  for (let line = -2; line <= 2; line += 1) {
    const offset = line * 1.8 + (Math.random() - 0.5) * 1.2
    graphiteContext.globalAlpha = 0.12 + Math.random() * 0.08
    graphiteContext.strokeStyle = '#373239'
    graphiteContext.lineWidth = 1.65 + Math.random() * 0.9
    graphiteContext.beginPath()
    graphiteContext.moveTo(from.x + normalX * offset, from.y + normalY * offset)
    graphiteContext.lineTo(to.x + normalX * offset, to.y + normalY * offset)
    graphiteContext.stroke()
  }
  for (let particle = 0; particle < Math.ceil(length / 5); particle += 1) {
    const progress = Math.random()
    const spread = (Math.random() - 0.5) * 11
    graphiteContext.globalAlpha = 0.08 + Math.random() * 0.13
    graphiteContext.fillStyle = '#2d2930'
    graphiteContext.beginPath()
    graphiteContext.arc(
      from.x + dx * progress + normalX * spread,
      from.y + dy * progress + normalY * spread,
      0.35 + Math.random() * 1.1,
      0,
      Math.PI * 2,
    )
    graphiteContext.fill()
  }
  graphiteContext.restore()
  liftImprint()
}

function completeRubbing() {
  if (revealed.value) return
  revealed.value = true
  if (graphiteContext) {
    graphiteContext.save()
    graphiteContext.fillStyle = 'rgba(53, 48, 56, .12)'
    graphiteContext.fillRect(0, 0, width, height)
    graphiteContext.restore()
  }
  liftImprint()
  renderPaper()
}

function onPointerMove(event: PointerEvent) {
  if (revealed.value) return
  resizePaper()
  const el = surface.value
  if (!el) return
  const bounds = el.getBoundingClientRect()
  const point = { x: event.clientX - bounds.left, y: event.clientY - bounds.top }
  if (previousPoint) {
    depositGraphite(previousPoint, point)
    markCoverage(previousPoint, point)
    renderPaper()
    if (coveredCells.size >= GRID_COLUMNS * GRID_ROWS * COMPLETE_COVERAGE) completeRubbing()
  }
  previousPoint = point
}

function onPointerLeave() {
  previousPoint = null
}

onMounted(() => {
  context = canvas.value?.getContext('2d') ?? null
  resizePaper()
})

onBeforeUnmount(() => {
  previousPoint = null
})
</script>

<template>
  <div class="paper-rubbing" role="dialog" aria-modal="true" aria-label="纸上拓印">
    <div class="paper-rubbing__panel">
      <div class="paper-rubbing__hint">
        <strong>拓印纸面</strong>
        <span>在纸上移动指针，用铅笔灰刮出压痕里的密码</span>
      </div>
      <div
        ref="surface"
        class="paper-rubbing__surface"
        :class="{ 'is-revealed': revealed }"
        @pointermove="onPointerMove"
        @pointerleave="onPointerLeave"
      >
        <canvas ref="canvas" class="paper-rubbing__canvas" aria-label="可涂擦的纸面拓印"></canvas>
        <div v-if="revealed" class="paper-rubbing__revealed">
          <span>密码</span>
          <strong>{{ answer }}</strong>
          <button type="button" @click="emit('complete')">继续</button>
        </div>
      </div>
      <small class="paper-rubbing__progress">
        {{ revealed ? '压痕已显影' : '继续涂擦直到文字完全显影' }}
      </small>
    </div>
  </div>
</template>

<style scoped>
.paper-rubbing {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(2, 8, 13, 0.72);
  backdrop-filter: blur(8px) saturate(0.6);
}
.paper-rubbing__panel {
  display: grid;
  gap: 0.8rem;
  width: min(42rem, calc(100% - 2rem));
}
.paper-rubbing__hint {
  display: grid;
  gap: 0.2rem;
  color: #e8fbff;
  text-align: center;
}
.paper-rubbing__hint strong {
  color: #9cecff;
  letter-spacing: 0.28em;
}
.paper-rubbing__hint span {
  font-size: 0.78rem;
  color: #c8e8f2;
}
.paper-rubbing__surface {
  position: relative;
  min-height: clamp(16rem, 46vh, 22rem);
  overflow: hidden;
  border-radius: 6px;
  background: #e7dfce;
  cursor: crosshair;
  touch-action: none;
  box-shadow:
    inset 0 0 24px rgba(71, 51, 34, 0.22),
    0 0 40px rgba(0, 0, 0, 0.5);
}
.paper-rubbing__canvas {
  display: block;
  width: 100%;
  height: 100%;
  min-height: inherit;
  touch-action: none;
}
.paper-rubbing__revealed {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 0.4rem;
  color: #3a2f28;
  background: rgba(231, 223, 206, 0.62);
  backdrop-filter: blur(1px);
}
.paper-rubbing__revealed span {
  font-size: 0.78rem;
  letter-spacing: 0.3em;
  color: #6b5d50;
}
.paper-rubbing__revealed strong {
  font-size: clamp(2.4rem, 8vw, 4rem);
  letter-spacing: 0.14em;
}
.paper-rubbing__revealed button {
  margin-top: 0.9rem;
  border: 1px solid rgba(20, 80, 100, 0.55);
  border-radius: 999px;
  padding: 0.6rem 2.2rem;
  color: #e7fbff;
  background: rgba(5, 35, 46, 0.92);
  font-weight: 750;
  letter-spacing: 0.2em;
  cursor: pointer;
}
.paper-rubbing__progress {
  color: #7fb4c3;
  font-size: 0.72rem;
  text-align: center;
}
@media (prefers-reduced-motion: reduce) {
  .paper-rubbing__surface { cursor: default; }
}
</style>
