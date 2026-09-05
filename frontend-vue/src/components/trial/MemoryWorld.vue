<script setup lang="ts">
// 「她的世界」记忆横版（docs/27 §8）：手写 Canvas 2D + rAF，无引擎/物理库。
// 地形 = 本局真实对话文字（terrain_text 由 Backend 下发），踩在脚下的是说过的话。
// 运行/相机是表现层；门与结局仍由 Backend 权威提交——本组件只负责走到门口
// 时 emit('arrive')，由 TrialView 发 ADVANCE/CHOOSE 推进。
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ terrainText: string[]; active: boolean }>()
const emit = defineEmits<{ (event: 'arrive'): void }>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const reduced = ref(false)
let raf = 0
let ctx: CanvasRenderingContext2D | null = null

// 玩家与相机（表现层，不写档）
const player = { x: 40, y: 0, vx: 0, vy: 0, w: 18, h: 26, onGround: false }
const keys = new Set<string>()
let gateX = 0
let arrived = false
let last = 0
const GRAVITY = 2200
const SPEED = 300
const JUMP = 820

const GROUND_Y = 0.78 // 地面在画布高度的比例

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.max(1, Math.round(rect.width * dpr))
  canvas.height = Math.max(1, Math.round(rect.height * dpr))
  ctx = canvas.getContext('2d')
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  gateX = rect.width - 90
  if (player.y === 0) player.y = rect.height * GROUND_Y - player.h
}

function step(dt: number) {
  const canvas = canvasRef.value
  if (!canvas) return
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  const floor = h * GROUND_Y

  const left = keys.has('ArrowLeft') || keys.has('a') || keys.has('A')
  const right = keys.has('ArrowRight') || keys.has('d') || keys.has('D')
  const jump = keys.has('ArrowUp') || keys.has('w') || keys.has('W') || keys.has(' ')

  player.vx = (right ? SPEED : 0) - (left ? SPEED : 0)
  if (jump && player.onGround) player.vy = -JUMP
  player.vy += GRAVITY * dt
  player.x += player.vx * dt
  player.y += player.vy * dt

  if (player.y + player.h >= floor) {
    player.y = floor - player.h
    player.vy = 0
    player.onGround = true
  } else {
    player.onGround = false
  }
  player.x = Math.max(8, Math.min(w - player.w - 8, player.x))

  if (!arrived && player.x + player.w >= gateX) {
    arrived = true
    emit('arrive')
  }
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !ctx) return
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  const floor = h * GROUND_Y

  // 冷色渐变底：起点（左）暖 → 出口（右）冷（docs/27 §8.4 的空间化）
  const grad = ctx.createLinearGradient(0, 0, w, 0)
  grad.addColorStop(0, '#2a1a10')
  grad.addColorStop(0.5, '#0a1220')
  grad.addColorStop(1, '#06121f')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, w, h)

  // 地面
  ctx.strokeStyle = 'rgba(131, 224, 251, 0.35)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(0, floor)
  ctx.lineTo(w, floor)
  ctx.stroke()

  // 地形文字：刻在地面上的「说过的话」
  ctx.font = '700 16px ui-sans-serif, system-ui'
  ctx.textBaseline = 'bottom'
  const n = props.terrainText.length
  props.terrainText.forEach((text, index) => {
    const x = 90 + (index * (w - 200)) / Math.max(1, n - 1)
    const y = floor - 4
    ctx!.fillStyle = 'rgba(180, 226, 240, 0.82)'
    ctx!.fillText(text, x, y)
  })

  // 门（关卡门标记，右侧竖线）
  ctx.strokeStyle = 'rgba(255, 120, 140, 0.9)'
  ctx.lineWidth = 3
  ctx.setLineDash([8, 6])
  ctx.beginPath()
  ctx.moveTo(gateX, floor - 64)
  ctx.lineTo(gateX, floor)
  ctx.stroke()
  ctx.setLineDash([])
  ctx.fillStyle = 'rgba(255, 150, 165, 0.9)'
  ctx.font = '700 13px ui-sans-serif, system-ui'
  ctx.textBaseline = 'bottom'
  ctx.fillText('门', gateX + 10, floor - 4)

  // 玩家
  ctx.fillStyle = '#a4ecff'
  ctx.shadowColor = 'rgba(70, 199, 237, 0.8)'
  ctx.shadowBlur = 14
  ctx.fillRect(player.x, player.y, player.w, player.h)
  ctx.shadowBlur = 0
}

function loop(t: number) {
  if (!reduced.value || !props.active) {
    if (last === 0) last = t
    const dt = Math.min((t - last) / 1000, 0.05)
    last = t
    if (props.active && !reduced.value) step(dt)
    draw()
  }
  raf = requestAnimationFrame(loop)
}

function onKeyDown(event: KeyboardEvent) {
  keys.add(event.key)
}
function onKeyUp(event: KeyboardEvent) {
  keys.delete(event.key)
}

watch(
  () => props.active,
  (active) => {
    if (active) resize()
  },
)

onMounted(() => {
  reduced.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  resize()
  raf = requestAnimationFrame(loop)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
})
</script>

<template>
  <div class="memory-world">
    <canvas ref="canvasRef" aria-label="她的世界：文字地形横版"></canvas>
    <p class="mw-hint">← → 行走 · ↑ / 空格 跳跃 · 向右走到门前</p>
    <!-- 低动态/静态回退（docs/27 §8.7）：不跑物理，直接给「到达门」按钮 -->
    <button
      v-if="reduced"
      class="mw-skip"
      type="button"
      @click="emit('arrive')"
    >
      到达门
    </button>
  </div>
</template>

<style scoped>
.memory-world { position: absolute; inset: 0; z-index: 6; }
canvas { display: block; width: 100%; height: 100%; }
.mw-hint {
  position: absolute;
  top: 4.6rem;
  left: 50%;
  transform: translateX(-50%);
  margin: 0;
  color: #6b9aa8;
  font: 0.68rem/1.4 monospace;
  letter-spacing: 0.08em;
  pointer-events: none;
}
.mw-skip {
  position: absolute;
  right: 1.4rem;
  bottom: 1.4rem;
  z-index: 10;
  border: 1px solid rgba(142, 229, 255, 0.52);
  border-radius: 999px;
  padding: 0.7rem 1.4rem;
  color: #e7faff;
  background: rgba(5, 25, 36, 0.86);
  font-weight: 750;
  cursor: pointer;
}
</style>
