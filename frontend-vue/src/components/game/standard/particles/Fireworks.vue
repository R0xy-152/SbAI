<!--
  Fireworks（docs/15 §3）：自研简化实现 —— 仅概念参考 LingChat
  particles/Fireworks.vue 的「火箭升空 → 爆炸粒子 + 拖尾」演出，不复制其源码
  （LingChat 版依赖指针交互/音频/复杂配置，本作只需氛围层）。
  契约同其余粒子：enabled prop、resize 重算、visibilitychange 暂停、卸载清理。
-->
<template>
  <canvas ref="canvasRef" class="fireworks-canvas"></canvas>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

interface Props {
  enabled?: boolean
  intensity?: number
}

const props = withDefaults(defineProps<Props>(), {
  enabled: true,
  intensity: 1,
})

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number
  maxLife: number
  color: string
  size: number
}

const canvasRef = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let rafId: number | null = null
let launchTimer: ReturnType<typeof setInterval> | null = null
let particles: Particle[] = []
let w = 0
let h = 0
let lastFrame = 0

const COLORS = ['#ff0043', '#14fc56', '#1e7fff', '#e60aff', '#ffbf36', '#ffffff']

const GRAVITY = 0.045
const TARGET_FPS = 60
const FRAME_INTERVAL = 1000 / TARGET_FPS

function randomRange(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function spawnBurst(x: number, y: number): void {
  const count = Math.floor(46 * (props.intensity ?? 1))
  const color = COLORS[Math.floor(Math.random() * COLORS.length)] ?? '#ffffff'
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count + Math.random() * 0.25
    const speed = randomRange(1.4, 4.4) * (props.intensity ?? 1)
    particles.push({
      x,
      y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 0,
      maxLife: randomRange(46, 86),
      color,
      size: randomRange(1.2, 2.4),
    })
  }
}

function launchRocket(): void {
  if (!ctx || w === 0 || h === 0) return
  // 火箭 = 一个快速上升的发光点 + 拖尾粒子
  const sx = randomRange(w * 0.12, w * 0.88)
  const sy = h
  const tx = randomRange(w * 0.18, w * 0.82)
  const ty = randomRange(h * 0.15, h * 0.42)
  const frames = 44
  let step = 0
  const rocketColor = COLORS[Math.floor(Math.random() * COLORS.length)] ?? '#ffffff'

  const tick = (): void => {
    step++
    if (!ctx || step > frames) return
    const t = step / frames
    const x = sx + (tx - sx) * t
    const y = sy + (ty - sy) * t - Math.sin(t * Math.PI) * h * 0.12
    // 拖尾
    ctx.globalCompositeOperation = 'lighter'
    ctx.beginPath()
    ctx.arc(x, y, 2.2, 0, Math.PI * 2)
    ctx.fillStyle = rocketColor
    ctx.fill()
    if (step === frames) {
      spawnBurst(tx, ty)
    } else {
      requestAnimationFrame(tick)
    }
  }
  requestAnimationFrame(tick)
}

function resize(): void {
  if (!canvasRef.value) return
  const dpr = window.devicePixelRatio || 1
  w = window.innerWidth
  h = window.innerHeight
  canvasRef.value.width = w * dpr
  canvasRef.value.height = h * dpr
  canvasRef.value.style.width = w + 'px'
  canvasRef.value.style.height = h + 'px'
  ctx = canvasRef.value.getContext('2d')
  ctx?.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function render(now: number): void {
  if (!ctx) {
    rafId = requestAnimationFrame(render)
    return
  }
  if (now - lastFrame < FRAME_INTERVAL) {
    rafId = requestAnimationFrame(render)
    return
  }
  lastFrame = now

  ctx.clearRect(0, 0, w, h)
  ctx.globalCompositeOperation = 'lighter'
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]
    if (!p) continue
    p.life++
    p.vy += GRAVITY
    p.vx *= 0.985
    p.vy *= 0.985
    p.x += p.vx
    p.y += p.vy
    const alpha = Math.max(0, 1 - p.life / p.maxLife)
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
    ctx.fillStyle = p.color
    ctx.globalAlpha = alpha
    ctx.fill()
    if (p.life >= p.maxLife) particles.splice(i, 1)
  }
  ctx.globalAlpha = 1
  ctx.globalCompositeOperation = 'source-over'
  rafId = requestAnimationFrame(render)
}

function start(): void {
  stop()
  resize()
  lastFrame = 0
  rafId = requestAnimationFrame(render)
  launchTimer = setInterval(launchRocket, 1900)
}

function stop(): void {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  if (launchTimer) {
    clearInterval(launchTimer)
    launchTimer = null
  }
  particles = []
  ctx?.clearRect(0, 0, w, h)
}

function handleVisibility(): void {
  if (document.hidden) stop()
  else if (props.enabled) start()
}

watch(
  () => props.enabled,
  (enabled) => {
    if (enabled) start()
    else stop()
  },
)

onMounted(() => {
  if (props.enabled) {
    try {
      start()
    } catch {
      // 无 2d context（测试环境）时静默降级
    }
  }
  document.addEventListener('visibilitychange', handleVisibility)
  window.addEventListener('resize', () => {
    if (props.enabled) start()
  })
})

onUnmounted(() => {
  stop()
  document.removeEventListener('visibilitychange', handleVisibility)
})
</script>

<style scoped>
.fireworks-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>
