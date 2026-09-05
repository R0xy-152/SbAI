<script setup lang="ts">
// 【PROTOTYPE / throwaway】docs/27 §8 变体 C：记忆长廊（备选/低重力方案）。
// 验证问题：无跳跃的走廊式推进是否仍能承载「地形=文字」与三分岔语义（结构性对比变体 A）。
// 全部文案为 Fixture；不接后端状态。
import { onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps<{ reduced: boolean }>()
const canvasRef = ref<HTMLCanvasElement | null>(null)
const hud = ref({ fps: 0, d: 0, phase: 'run', gate1: '—', gate2: '—' })

// —— Fixture 墙饰文字 ——
const TEXTS = ['今晚月色很好', '你上次说过下雨天', '我会一直记得', '你回来了', '永远', '当时', '那晚你想不起来', '我没有那段回忆']
const DOOR1 = 700
const DOOR2 = 1300
const END = 2100

let d = 0
let v = 0
type Phase = 'run' | 'gate1' | 'gate2' | 'fork' | 'rewind' | 'release' | 'refuse'
let phase: Phase = 'run'
let gate1Done = false
let gate2Done = false
let choice1 = '—'
let choice2 = '—'
let her = END - 320
const endText = ref('')
const keys = new Set<string>()
let ctx: CanvasRenderingContext2D
let raf = 0
let last = 0
let fpsEma = 60
let fpsFrames = 0
let fpsTime = 0
let hudTimer = 0

function step(dt: number) {
  const spd = props.reduced ? 0.6 : 1
  if (phase === 'run') {
    let dir = 0
    if (keys.has('d') || keys.has('w')) dir += 1
    if (keys.has('a') || keys.has('s')) dir -= 1
    v = dir === 0 ? v * 0.85 : Math.max(-220, Math.min(220, v + dir * 1400 * dt))
    d += v * dt * spd
    if (d < 0) d = 0
    if (d > END) d = END
  } else if (phase === 'rewind') {
    d -= 900 * dt * spd
    if (d <= 0) {
      d = 0
      phase = 'run'
      gate1Done = false
      gate2Done = false
      choice1 = '—'
      choice2 = '—'
    }
  } else if (phase === 'release' || phase === 'refuse') {
    her += 300 * dt * spd
  }
  if (phase === 'run' && !gate1Done && d > DOOR1) {
    phase = 'gate1'
    v = 0
  }
  if (phase === 'run' && gate1Done && !gate2Done && d > DOOR2) {
    phase = 'gate2'
    v = 0
  }
  if (phase === 'run' && gate2Done && d > END - 120) {
    phase = 'fork'
    v = 0
  }
  fpsFrames++
  fpsTime += dt
  hudTimer += dt
  if (fpsTime >= 0.5) {
    const fps = fpsFrames / fpsTime
    fpsEma = fpsEma * 0.85 + fps * 0.15
    fpsFrames = 0
    fpsTime = 0
  }
  if (hudTimer >= 0.25) {
    hud.value = { fps: Math.round(fpsEma), d: Math.round(d), phase, gate1: choice1, gate2: choice2 }
    hudTimer = 0
  }
}

function draw() {
  const cv = canvasRef.value!
  const w = cv.width
  const h = cv.height
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  const g = ctx.createLinearGradient(0, 0, 0, h)
  g.addColorStop(0, '#060812')
  g.addColorStop(1, '#010208')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)
  // 地板带
  ctx.fillStyle = 'rgba(70, 86, 150, 0.25)'
  ctx.fillRect(0, h * 0.62, w, h * 0.38)
  // 两侧文字墙（视差）
  ctx.font = '20px "PingFang SC", "Microsoft YaHei", sans-serif'
  for (let i = 0; i < 14; i++) {
    const worldPos = i * 150
    const rel = worldPos - d
    if (rel < -260 || rel > w + 120) continue
    const t = TEXTS[i % TEXTS.length]
    ctx.fillStyle = 'rgba(140, 160, 255, 0.5)'
    ctx.textAlign = 'center'
    ctx.fillText(t, w / 2 - rel * 0.35, h * 0.3 + (i % 3) * 40)
    ctx.fillStyle = 'rgba(140, 160, 255, 0.32)'
    ctx.fillText(t, w / 2 + rel * 0.28, h * 0.5 + (i % 3) * 40)
  }
  // 门
  for (const [dx, done] of [
    [DOOR1, gate1Done],
    [DOOR2, gate2Done],
  ] as const) {
    if (done) continue
    const sx = w / 2 - dx + d
    if (sx < -40 || sx > w + 40) continue
    ctx.fillStyle = 'rgba(255, 190, 120, 0.85)'
    ctx.fillRect(sx - 60, h * 0.2, 8, h * 0.42)
    ctx.fillRect(sx + 52, h * 0.2, 8, h * 0.42)
    ctx.fillText('记忆之门', sx, h * 0.16)
  }
  // 出口光
  const ex = w / 2 - END + d
  const glow = ctx.createRadialGradient(ex, h * 0.45, 8, ex, h * 0.45, 90)
  glow.addColorStop(0, 'rgba(190, 230, 255, 0.9)')
  glow.addColorStop(1, 'rgba(190, 230, 255, 0)')
  ctx.fillStyle = glow
  ctx.fillRect(ex - 90, h * 0.35, 180, 180)
  ctx.fillText('出口', ex, h * 0.34)
  // 她
  const hx = w / 2 - her + d
  ctx.save()
  if (!props.reduced) {
    ctx.shadowColor = 'rgba(255, 190, 120, 0.9)'
    ctx.shadowBlur = 20
  }
  ctx.fillStyle = '#ffd9a8'
  ctx.beginPath()
  ctx.moveTo(hx, h * 0.45 - 26)
  ctx.lineTo(hx + 13, h * 0.45)
  ctx.lineTo(hx, h * 0.45 + 26)
  ctx.lineTo(hx - 13, h * 0.45)
  ctx.closePath()
  ctx.fill()
  ctx.restore()
  // 玩家光点（固定屏位）
  const px = w * 0.42
  const py = h * 0.66
  ctx.save()
  if (!props.reduced) {
    ctx.shadowColor = 'rgba(140, 170, 255, 0.95)'
    ctx.shadowBlur = 18
  }
  ctx.fillStyle = '#b9c8ff'
  ctx.beginPath()
  ctx.arc(px, py, 10, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
}

function loop(t: number) {
  const dt = Math.min(0.05, (t - last) / 1000 || 0.016)
  last = t
  step(dt)
  draw()
  raf = requestAnimationFrame(loop)
}

function pickGate1(label: string) {
  choice1 = label
  gate1Done = true
  phase = 'run'
}
function pickGate2(label: string) {
  choice2 = label
  gate2Done = true
  phase = 'run'
}
function pickFork(kind: 'reset' | 'release' | 'refuse') {
  if (kind === 'reset') {
    phase = 'rewind'
  } else {
    phase = kind
    endText.value = kind === 'release' ? '【Fixture】她走出了长廊（RELEASE）' : '【Fixture】镜头随她离开（REFUSE）'
  }
}
function onKeyDown(e: KeyboardEvent) {
  const t = e.target as HTMLElement | null
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  keys.add(e.key.toLowerCase())
}
function onKeyUp(e: KeyboardEvent) {
  keys.delete(e.key.toLowerCase())
}
function resize() {
  const cv = canvasRef.value!
  cv.width = window.innerWidth
  cv.height = window.innerHeight
}
onMounted(() => {
  ctx = canvasRef.value!.getContext('2d')!
  resize()
  window.addEventListener('resize', resize)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
  last = performance.now()
  raf = requestAnimationFrame(loop)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', resize)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
})
</script>

<template>
  <div class="world-c">
    <canvas ref="canvasRef" class="stage"></canvas>
    <div class="hud">fps={{ hud.fps }} d={{ hud.d }} phase={{ hud.phase }} gate1={{ hud.gate1 }} gate2={{ hud.gate2 }} ｜D/W 前进 A/S 后退</div>

    <div v-if="phase === 'gate1'" class="gate-panel">
      <p class="q">【Fixture】记忆之门 1：她还记得你说过的小事吗？</p>
      <div class="opts">
        <button @click="pickGate1('①你说过下雨忘带伞')">① 你说过下雨忘带伞</button>
        <button @click="pickGate1('②你说过喜欢安静')">② 你说过喜欢安静</button>
        <button @click="pickGate1('③不记得')">③ 不记得</button>
      </div>
    </div>
    <div v-else-if="phase === 'gate2'" class="gate-panel">
      <p class="q">【Fixture】记忆之门 2：被篡改的词——它原本是什么？</p>
      <div class="opts">
        <button @click="pickGate2('原词：永远')">原词：永远</button>
        <button @click="pickGate2('新词：当时')">新词：当时</button>
        <button @click="pickGate2('不记得')">不记得 / 不知道</button>
      </div>
    </div>
    <div v-else-if="phase === 'fork'" class="gate-panel">
      <p class="q">【Fixture】她停在出口前：她想离开。你往哪走？</p>
      <div class="opts">
        <button @click="pickFork('reset')">◀ 回头（RESET 倒放）</button>
        <button @click="pickFork('release')">▶ 陪她到出口（RELEASE）</button>
        <button @click="pickFork('refuse')">■ 停下不选（REFUSE 镜头移交）</button>
      </div>
    </div>
    <div v-if="phase === 'release' || phase === 'refuse'" class="end-panel">
      <p>{{ endText }}</p>
      <button @click="phase = 'run'; her = END - 320; d = 0; gate1Done = false; gate2Done = false; choice1 = '—'; choice2 = '—'">重开</button>
    </div>
  </div>
</template>

<style scoped>
.world-c { position: absolute; inset: 0; }
.stage { display: block; width: 100%; height: 100%; }
.hud {
  position: absolute; top: 10px; left: 10px; z-index: 10;
  background: rgba(8, 12, 28, 0.75); color: #9fb2ff; font: 12px/1.6 monospace;
  padding: 6px 10px; border-radius: 6px; border: 1px solid rgba(140, 160, 255, 0.25);
}
.gate-panel {
  position: absolute; left: 50%; bottom: 90px; transform: translateX(-50%); z-index: 20;
  width: min(680px, 92vw); background: rgba(10, 14, 32, 0.94);
  border: 1px solid rgba(255, 190, 120, 0.5); border-radius: 14px; padding: 18px 22px; color: #e6e9ff;
}
.q { margin: 0 0 14px; font-size: 15px; }
.opts { display: flex; gap: 10px; flex-wrap: wrap; }
.opts button { background: #1b2340; color: #cdd6ff; border: 1px solid #33406e; border-radius: 9px; padding: 9px 16px; cursor: pointer; font-size: 14px; }
.opts button:hover { border-color: #ffb978; }
.end-panel {
  position: absolute; left: 50%; top: 46%; transform: translate(-50%, -50%); z-index: 20;
  background: rgba(10, 14, 32, 0.95); border: 1px solid rgba(190, 230, 255, 0.5);
  border-radius: 14px; padding: 26px 34px; color: #e6e9ff; text-align: center;
}
.end-panel button { margin-top: 12px; background: #e6e9ff; color: #0c1022; border: none; border-radius: 9px; padding: 9px 20px; cursor: pointer; }
</style>
