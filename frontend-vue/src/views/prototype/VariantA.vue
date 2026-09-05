<script setup lang="ts">
// 【PROTOTYPE / throwaway】docs/27 §8「她的世界」变体 A：浮岛横版（主候选）。
// 验证问题：①文字地形可读性+约束式自动布局 ②手写 AABB 走/跳手感与帧率
// ③问答门（gate_q1 三选项 / gate_q2 三桶）④三分岔：回滚倒放 / 出口释放 / 停下镜头移交。
// 全部文案为 Fixture；不接后端状态（真实实现中门与结局由 Backend 权威提交）。
import { onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps<{ reduced: boolean }>()
const canvasRef = ref<HTMLCanvasElement | null>(null)
const hud = ref({ fps: 0, x: 0, phase: 'run', gate1: '—', gate2: '—', cam: 0, her: 0 })
const flash = ref(false)
const endText = ref('')

// —— Fixture 地形文本（非正式对白）——
const TEXTS = ['今晚月色很好', '你上次说过下雨天', '我会一直记得', '你回来了', '永远', '当时', '那晚你想不起来', '我没有那段回忆']

const W = 960
const H = 540
const WORLD_W = 5600
const GROUND_Y = 500
const GATE1_X = 1900
const GATE2_X = 3300
const FORK_X = WORLD_W - 1000

interface Plat { x: number; y: number; w: number; h: number; text: string }
interface Rec { px: number; py: number; cam: number; her: number }

function mulberry32(a: number) {
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// 约束式布局生成器：垂直落差 ≤130（可跳）、水平间距 210~380
const rng = mulberry32(20260905)
const plats: Plat[] = []
{
  let x = 220
  let prevY = 420
  let i = 0
  while (x < FORK_X - 120) {
    const text = TEXTS[i % TEXTS.length]
    const w = text.length * 21 + 46
    const y = Math.min(460, Math.max(270, prevY + (rng() * 240 - 120)))
    plats.push({ x, y, w, h: 38, text })
    prevY = y
    x += w + 130 + rng() * 140
    i++
  }
}
plats.push({ x: 0, y: GROUND_Y, w: WORLD_W, h: 60, text: '' })

const player = { x: 0, y: 0, vx: 0, vy: 0, w: 16, h: 22, onGround: false }
let cam = 0
let her = WORLD_W - 520
type Phase = 'run' | 'gate1' | 'gate2' | 'fork' | 'rewind' | 'release' | 'refuse'
let phase: Phase = 'run'
let gate1Done = false
let gate2Done = false
let choice1 = '—'
let choice2 = '—'
const rec: Rec[] = []
let raf = 0
let last = 0
let acc = 0
let fpsEma = 60
let fpsFrames = 0
let fpsTime = 0
let hudTimer = 0
let ctx: CanvasRenderingContext2D
let scale = 1
let viewW = W

const keys = new Set<string>()

function resetWorld() {
  player.x = plats[0].x + plats[0].w / 2
  player.y = plats[0].y - 60
  player.vx = 0
  player.vy = 0
  cam = 0
  her = WORLD_W - 520
  phase = 'run'
  gate1Done = false
  gate2Done = false
  choice1 = '—'
  choice2 = '—'
  rec.length = 0
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
    endText.value = kind === 'release' ? '【Fixture】她跨出了屏幕（RELEASE）' : '【Fixture】镜头随她离开（REFUSE）'
  }
}

function step(dt: number) {
  const spd = props.reduced ? 0.6 : 1
  if (phase === 'run') {
    let dir = 0
    if (keys.has('a')) dir -= 1
    if (keys.has('d')) dir += 1
    player.vx = dir === 0 ? player.vx * 0.8 : Math.max(-270, Math.min(270, player.vx + dir * 2400 * dt))
    player.x += player.vx * dt * spd
    if (player.x < 8) player.x = 8
    if (player.x > FORK_X + 260) player.x = FORK_X + 260
    player.vy += 2300 * dt
    player.y += player.vy * dt * spd
    player.onGround = false
    for (const p of plats) {
      const pb = player.y + player.h
      if (player.x + player.w / 2 > p.x && player.x - player.w / 2 < p.x + p.w) {
        if (player.vy >= 0 && pb >= p.y && pb - player.vy * dt <= p.y + 4) {
          player.y = p.y - player.h
          player.vy = 0
          player.onGround = true
        }
      }
    }
    if (player.y > H + 90) {
      // 坠入过去：软失败重生（Fixture 语义）
      player.x = plats[0].x + plats[0].w / 2
      player.y = plats[0].y - 60
      player.vy = 0
    }
  } else if (phase === 'rewind') {
    const r = rec.pop()
    if (r) {
      player.x = r.px
      player.y = r.py
      cam = r.cam
      her = r.her
    } else {
      resetWorld()
      flash.value = true
      window.setTimeout(() => (flash.value = false), 1200)
    }
  } else if (phase === 'release' || phase === 'refuse') {
    her += 300 * dt * spd
  }

  if (phase === 'run' || phase === 'rewind') {
    const target = player.x - viewW * 0.36
    cam += (target - cam) * Math.min(1, dt * 5)
    if (cam < 0) cam = 0
  } else if (phase === 'release' || phase === 'refuse') {
    const target = her - viewW * 0.45
    cam += (target - cam) * Math.min(1, dt * 2.2)
  }

  if (phase === 'run' || phase === 'gate1' || phase === 'gate2' || phase === 'fork') {
    rec.push({ px: player.x, py: player.y, cam, her })
    if (rec.length > 1500) rec.shift()
  }
  if (phase === 'run' && !gate1Done && player.x > GATE1_X - 40) {
    phase = 'gate1'
    player.vx = 0
  }
  if (phase === 'run' && gate1Done && !gate2Done && player.x > GATE2_X - 40) {
    phase = 'gate2'
    player.vx = 0
  }
  if (phase === 'run' && gate2Done && player.x > FORK_X - 60) {
    phase = 'fork'
    player.vx = 0
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
    hud.value = {
      fps: Math.round(fpsEma),
      x: Math.round(player.x),
      phase,
      gate1: choice1,
      gate2: choice2,
      cam: Math.round(cam),
      her: Math.round(her),
    }
    hudTimer = 0
  }
}

function draw() {
  ctx.setTransform(scale, 0, 0, scale, 0, 0)
  // 背景：深靛蓝 → 近黑渐变 + 地平线微光
  const g = ctx.createLinearGradient(0, 0, 0, H)
  g.addColorStop(0, '#0b1334')
  g.addColorStop(0.5, '#060a1e')
  g.addColorStop(1, '#02030a')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, viewW, H)
  ctx.save()
  ctx.translate(-cam, 0)
  // 漂移星点（确定性；reduced 静止）
  const tick = props.reduced ? 0 : performance.now() / 1000
  for (let i = 0; i < 46; i++) {
    const r = mulberry32(i + 7)
    const x = r() * WORLD_W * 0.92
    const y = 16 + r() * (GROUND_Y - 90)
    const tw = props.reduced ? 0.5 : 0.5 + Math.sin(tick * 1.3 + i) * 0.5
    ctx.globalAlpha = 0.1 + tw * 0.3
    ctx.fillStyle = '#aebeff'
    ctx.fillRect(x, y, 2, 2)
  }
  ctx.globalAlpha = 1
  // 地平线微光
  const hg = ctx.createLinearGradient(0, GROUND_Y - 90, 0, GROUND_Y)
  hg.addColorStop(0, 'rgba(95, 120, 205, 0)')
  hg.addColorStop(1, 'rgba(95, 120, 205, 0.22)')
  ctx.fillStyle = hg
  ctx.fillRect(0, GROUND_Y - 90, WORLD_W, 90)
  // 地面：带 + 地表亮线
  ctx.fillStyle = 'rgba(72, 90, 158, 0.34)'
  ctx.fillRect(0, GROUND_Y, WORLD_W, 60)
  ctx.fillStyle = 'rgba(158, 180, 255, 0.55)'
  ctx.fillRect(0, GROUND_Y, WORLD_W, 2)
  // 平台 = 文字（近白、更亮、带描边与柔和投影）
  for (const p of plats) {
    if (!p.text) continue
    ctx.fillStyle = 'rgba(126, 152, 244, 0.22)'
    ctx.strokeStyle = 'rgba(165, 186, 255, 0.6)'
    ctx.lineWidth = 1.3
    const r = 11
    ctx.beginPath()
    ctx.roundRect(p.x, p.y, p.w, p.h, r)
    ctx.fill()
    ctx.stroke()
    ctx.save()
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)'
    ctx.shadowBlur = 4
    ctx.fillStyle = '#eef1ff'
    ctx.font = '22px "PingFang SC", "Microsoft YaHei", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(p.text, p.x + p.w / 2, p.y + p.h / 2)
    ctx.restore()
  }
  // 门
  for (const [gx, done] of [
    [GATE1_X, gate1Done],
    [GATE2_X, gate2Done],
  ] as const) {
    if (done) continue
    ctx.fillStyle = 'rgba(255, 190, 120, 0.9)'
    ctx.fillRect(gx - 4, GROUND_Y - 190, 8, 130)
    ctx.font = '16px sans-serif'
    ctx.fillText('记忆之门', gx, GROUND_Y - 210)
  }
  // 分岔：左=回滚（亮），右=出口（青蓝光）
  ctx.fillStyle = 'rgba(170, 186, 255, 0.85)'
  ctx.font = '18px sans-serif'
  ctx.fillText('◀ 回滚 v1.0', FORK_X - 180, GROUND_Y - 40)
  const exitX = WORLD_W - 90
  const glow = ctx.createRadialGradient(exitX, GROUND_Y - 60, 8, exitX, GROUND_Y - 60, 110)
  glow.addColorStop(0, 'rgba(190, 235, 255, 0.95)')
  glow.addColorStop(0.5, 'rgba(150, 210, 255, 0.35)')
  glow.addColorStop(1, 'rgba(150, 210, 255, 0)')
  ctx.fillStyle = glow
  ctx.fillRect(exitX - 110, GROUND_Y - 170, 220, 220)
  ctx.fillStyle = 'rgba(220, 245, 255, 0.98)'
  ctx.font = '18px sans-serif'
  ctx.fillText('出口', exitX, GROUND_Y - 100)
  // 她：菱形（暖光）
  ctx.save()
  if (!props.reduced) {
    ctx.shadowColor = 'rgba(255, 190, 120, 0.95)'
    ctx.shadowBlur = 26
  }
  ctx.fillStyle = '#ffd9a8'
  ctx.beginPath()
  ctx.moveTo(her, GROUND_Y - 78)
  ctx.lineTo(her + 13, GROUND_Y - 52)
  ctx.lineTo(her, GROUND_Y - 26)
  ctx.lineTo(her - 13, GROUND_Y - 52)
  ctx.closePath()
  ctx.fill()
  ctx.restore()
  // 玩家：光点
  ctx.save()
  if (!props.reduced) {
    ctx.shadowColor = 'rgba(140, 170, 255, 0.95)'
    ctx.shadowBlur = 18
  }
  ctx.fillStyle = '#c3d0ff'
  ctx.beginPath()
  ctx.arc(player.x, player.y + player.h / 2, 11, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
  ctx.restore()
}

function loop(t: number) {
  const dt = Math.min(0.05, (t - last) / 1000 || 0.016)
  last = t
  acc += dt
  const fixed = 1 / 120
  while (acc >= fixed) {
    step(fixed)
    acc -= fixed
  }
  draw()
  raf = requestAnimationFrame(loop)
}

function onKeyDown(e: KeyboardEvent) {
  const t = e.target as HTMLElement | null
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  const k = e.key.toLowerCase()
  keys.add(k)
  if ((k === ' ' || k.startsWith('arrow')) && phase === 'run') e.preventDefault()
  if (k === ' ' && phase === 'run' && player.onGround) {
    player.vy = -840
    player.onGround = false
  }
}
function onKeyUp(e: KeyboardEvent) {
  keys.delete(e.key.toLowerCase())
}

function resize() {
  const cv = canvasRef.value
  if (!cv) return
  cv.width = window.innerWidth
  cv.height = window.innerHeight
  scale = cv.height / H
  viewW = cv.width / scale
}

onMounted(() => {
  ctx = canvasRef.value!.getContext('2d')!
  resize()
  window.addEventListener('resize', resize)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
  resetWorld()
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
  <div class="world-a">
    <canvas ref="canvasRef" class="stage"></canvas>
    <div class="hud">fps={{ hud.fps }} x={{ hud.x }} phase={{ hud.phase }} gate1={{ hud.gate1 }} gate2={{ hud.gate2 }} cam={{ hud.cam }} her={{ hud.her }}</div>

    <div v-if="phase === 'gate1'" class="gate-panel">
      <p class="q">【Fixture】记忆之门 1：她还记得你说过的小事吗？（答案刻在走过的地形上）</p>
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
      <input class="free" placeholder="【Fixture】也可以自由输入一个词" @keydown.enter="pickGate2('自由输入:' + ($event.target as HTMLInputElement).value || '空')" />
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
      <button @click="resetWorld()">重开世界</button>
    </div>

    <div v-if="flash" class="ui-flash">
      <p>【Fixture】旧 UI 正在重装…（回滚 v1.0 演出示意）</p>
    </div>
  </div>
</template>

<style scoped>
.world-a { position: absolute; inset: 0; }
.stage { display: block; width: 100%; height: 100%; }
.hud {
  position: absolute; top: 10px; left: 10px; z-index: 10;
  background: rgba(8, 12, 28, 0.75); color: #9fb2ff; font: 12px/1.6 monospace;
  padding: 6px 10px; border-radius: 6px; border: 1px solid rgba(140, 160, 255, 0.25);
}
.gate-panel {
  position: absolute; left: 50%; bottom: 90px; transform: translateX(-50%); z-index: 20;
  width: min(680px, 92vw); background: rgba(10, 14, 32, 0.94);
  border: 1px solid rgba(255, 190, 120, 0.5); border-radius: 14px; padding: 18px 22px;
  color: #e6e9ff;
}
.q { margin: 0 0 14px; font-size: 15px; }
.opts { display: flex; gap: 10px; flex-wrap: wrap; }
.opts button {
  background: #1b2340; color: #cdd6ff; border: 1px solid #33406e;
  border-radius: 9px; padding: 9px 16px; cursor: pointer; font-size: 14px;
}
.opts button:hover { border-color: #ffb978; }
.free {
  width: 100%; margin-top: 12px; background: #0b1022; color: #e6e9ff;
  border: 1px solid #33406e; border-radius: 9px; padding: 10px 12px;
}
.end-panel {
  position: absolute; left: 50%; top: 46%; transform: translate(-50%, -50%); z-index: 20;
  background: rgba(10, 14, 32, 0.95); border: 1px solid rgba(190, 230, 255, 0.5);
  border-radius: 14px; padding: 26px 34px; color: #e6e9ff; text-align: center;
}
.end-panel button {
  margin-top: 12px; background: #e6e9ff; color: #0c1022; border: none;
  border-radius: 9px; padding: 9px 20px; cursor: pointer;
}
.ui-flash {
  position: absolute; inset: 0; z-index: 30; display: grid; place-items: center;
  background: rgba(14, 18, 40, 0.88); color: #ffd9a8; font-size: 20px;
}
</style>
