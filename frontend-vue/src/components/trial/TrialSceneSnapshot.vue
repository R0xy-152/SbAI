<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { TrialScene } from '../../api/trial'
import { setFrozenFrame } from './mediaFrame'

const props = defineProps<{
  scene: TrialScene
  // 冻结帧（dataURL）：非空则以冻结图代替实时视频（用作碎裂源，避免四片各自挂不同步视频）
  frozen?: string | null
}>()

const assetByCharacter: Record<string, string> = {
  deepseek: '/char/deepseek/pic/deepseek_main.png',
  chatgpt: '/char/chatgpt/pic/chatgpt_main.png',
  claude: '/char/claude/pic/claude_main.png',
  doubao: '/char/doubao/pic/doubao_placeholder.svg',
}

const slotLeft: Record<TrialScene['characters'][number]['slot'], string> = {
  LEFT: '13%',
  CENTER_LEFT: '35%',
  CENTER: '50%',
  CENTER_RIGHT: '65%',
  RIGHT: '87%',
}

const characters = computed(() =>
  props.scene.characters.map((character) => ({
    ...character,
    src: assetByCharacter[character.character_id] ?? null,
    left: slotLeft[character.slot],
  })),
)

// 开场特写：视频 + 音乐同时起播（docs/27 §7.1/§7.2）。视频 muted 自动播放；
// 音乐若被自动播放策略拦截，则等首次交互再播，保证与视频「同时出场」。
const hasMedia = computed(() => Boolean(props.scene.video))
const videoEl = ref<HTMLVideoElement | null>(null)
const audioEl = ref<HTMLAudioElement | null>(null)

let resumePointer: (() => void) | null = null
let resumeKey: (() => void) | null = null

function clearResumeListeners() {
  if (resumePointer) window.removeEventListener('pointerdown', resumePointer)
  if (resumeKey) window.removeEventListener('keydown', resumeKey)
  resumePointer = null
  resumeKey = null
}

function stopMedia() {
  videoEl.value?.pause()
  audioEl.value?.pause()
  clearResumeListeners()
}

function startMedia() {
  if (!hasMedia.value) return
  const v = videoEl.value
  const a = audioEl.value
  if (v) v.play().catch(() => {})
  const tryAudio = () => {
    if (a) a.play().catch(() => {})
  }
  tryAudio() // 若进入时有手势激活则立即起播
  // 兜底：若仍暂停，等首次交互再起播（保证与视频「同时出场」）
  // 注意：pointerdown 与 keydown 是两个独立 listener，任一触发后必须把
  // 两个都摘掉，否则残留的 keydown 会在后续（如输密码按 Enter）把已停的
  // 开场音乐重新 play 起来。
  const resume = () => {
    if (a && a.paused) a.play().catch(() => {})
    clearResumeListeners()
  }
  resumePointer = resume
  resumeKey = resume
  window.addEventListener('pointerdown', resume, { once: true })
  window.addEventListener('keydown', resume, { once: true })
}

const frozen = computed(() => props.frozen ?? null)

// 离开视频/进入冻结帧后立即停掉音乐：把 <audio> 移出 DOM 并不会自动停止
// 已播放的元素，必须显式 pause，否则「Aira」会一直循环到后续章节/退出试玩后。
watch(
  () => Boolean(props.scene.video && props.scene.music && !frozen.value),
  (shouldPlay) => {
    if (!shouldPlay) stopMedia()
  },
)
let captureTimer: number | undefined
let captureCanvas: HTMLCanvasElement | null = null
const CAPTURE_W = 960

function captureVideoFrame() {
  const v = videoEl.value
  if (!v || v.readyState < 2 || v.videoWidth === 0) return
  const ratio = v.videoWidth / v.videoHeight
  const w = CAPTURE_W
  const h = Math.round(CAPTURE_W / ratio)
  captureCanvas = captureCanvas ?? document.createElement('canvas')
  captureCanvas.width = w
  captureCanvas.height = h
  const c = captureCanvas.getContext('2d')
  if (!c) return
  c.drawImage(v, 0, 0, w, h)
  try {
    setFrozenFrame(captureCanvas.toDataURL('image/jpeg', 0.82))
  } catch {
    // 画布被污染则跳过，靠海报/静态背景兜底
  }
}

function startCapture() {
  if (!hasMedia.value) return
  captureVideoFrame()
  captureTimer = window.setInterval(captureVideoFrame, 260)
}

onMounted(() => {
  startMedia()
  startCapture()
})

onBeforeUnmount(() => {
  if (captureTimer) {
    window.clearInterval(captureTimer)
    captureTimer = undefined
  }
  // 捕获最后一帧作为碎裂源（docs/27 §7.1 异常冻结帧）
  if (hasMedia.value) captureVideoFrame()
  stopMedia()
})
</script>

<template>
  <div class="trial-snapshot" :class="{ 'has-video': scene.video }" :style="scene.video ? undefined : { backgroundImage: `url(${scene.background})` }">
    <video
      v-if="scene.video && !frozen"
      ref="videoEl"
      class="trial-snapshot__video"
      :src="scene.video"
      :poster="scene.poster"
      autoplay
      muted
      loop
      playsinline
      @loadeddata="captureVideoFrame"
    ></video>
    <img
      v-else-if="scene.video && frozen"
      class="trial-snapshot__video"
      :src="frozen"
      alt=""
    />
    <audio v-if="scene.video && scene.music && !frozen" ref="audioEl" :src="scene.music" loop preload="auto"></audio>
    <div class="trial-snapshot__shade" aria-hidden="true"></div>
    <div class="trial-snapshot__scan" aria-hidden="true"></div>

    <div v-if="!scene.video" class="trial-snapshot__stage" aria-hidden="true">
      <template v-for="character in characters" :key="character.character_id">
        <img
          v-if="character.src"
          :src="character.src"
          :alt="character.display_name"
          class="trial-snapshot__character"
          :style="{ left: character.left }"
        />
        <div
          v-else
          class="trial-snapshot__redacted-presence"
          :style="{ left: character.left }"
        >
          <span></span><i></i><b></b>
        </div>
      </template>
    </div>

    <div class="trial-snapshot__frame" aria-hidden="true">
      <span class="corner corner--nw"></span>
      <span class="corner corner--ne"></span>
      <span class="corner corner--se"></span>
      <span class="corner corner--sw"></span>
    </div>
  </div>
</template>

<style scoped>
.trial-snapshot {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background-color: #050910;
  background-position: center;
  background-size: cover;
  color: #eefaff;
}

.trial-snapshot__video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.trial-snapshot.has-video .trial-snapshot__shade {
  opacity: 0.55;
}

.trial-snapshot__shade {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 38%, transparent 0 26%, rgba(0, 4, 10, 0.34) 72%),
    linear-gradient(180deg, rgba(2, 6, 14, 0.08), rgba(1, 5, 12, 0.52));
}

.trial-snapshot__scan {
  position: absolute;
  inset: 0;
  opacity: 0.13;
  background: repeating-linear-gradient(0deg, transparent 0 3px, rgba(135, 230, 255, 0.16) 4px);
  mix-blend-mode: screen;
}

.trial-snapshot__stage {
  position: absolute;
  inset: 5% 0 19%;
}

.trial-snapshot__character {
  position: absolute;
  bottom: -2%;
  height: min(82vh, 94%);
  max-width: 31vw;
  object-fit: contain;
  transform: translateX(-50%);
  filter: drop-shadow(0 18px 22px rgba(0, 0, 0, 0.48));
}

.trial-snapshot__redacted-presence {
  position: absolute;
  bottom: 1%;
  width: min(26vw, 19rem);
  height: min(68vh, 36rem);
  transform: translateX(-50%);
  filter: drop-shadow(0 0 28px rgba(119, 224, 255, 0.42));
}

.trial-snapshot__redacted-presence span,
.trial-snapshot__redacted-presence i,
.trial-snapshot__redacted-presence b {
  position: absolute;
  display: block;
  background: linear-gradient(90deg, rgba(3, 8, 14, 0.96), rgba(19, 32, 48, 0.92));
  box-shadow: inset 0 0 24px rgba(115, 222, 255, 0.12);
}

.trial-snapshot__redacted-presence span {
  top: 3%;
  left: 31%;
  width: 38%;
  aspect-ratio: 1;
  border-radius: 50%;
}

.trial-snapshot__redacted-presence i {
  inset: 25% 10% 0;
  border-radius: 48% 48% 12% 12%;
  clip-path: polygon(23% 0, 77% 0, 100% 100%, 0 100%);
}

.trial-snapshot__redacted-presence b {
  top: 19%;
  left: 12%;
  width: 76%;
  height: 13%;
  background: repeating-linear-gradient(
    90deg,
    rgba(180, 242, 255, 0.7) 0 7px,
    rgba(8, 14, 24, 0.94) 7px 15px
  );
  filter: blur(3px);
  transform: skewX(-8deg);
}

.trial-snapshot__frame {
  position: absolute;
  inset: clamp(0.55rem, 1vw, 1rem);
  border: 1px solid rgba(151, 232, 255, 0.16);
  pointer-events: none;
}

.corner {
  position: absolute;
  width: 1.4rem;
  height: 1.4rem;
  border-color: rgba(149, 229, 255, 0.66);
}
.corner--nw { top: -1px; left: -1px; border-top: 2px solid; border-left: 2px solid; }
.corner--ne { top: -1px; right: -1px; border-top: 2px solid; border-right: 2px solid; }
.corner--se { right: -1px; bottom: -1px; border-right: 2px solid; border-bottom: 2px solid; }
.corner--sw { bottom: -1px; left: -1px; border-bottom: 2px solid; border-left: 2px solid; }

@media (max-aspect-ratio: 4/5) {
  .trial-snapshot__character { max-width: 48vw; height: 70%; }
  .trial-snapshot__redacted-presence { width: 48vw; height: 58vh; }
}
</style>
