<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'

interface ChapterEntry {
  id: string
  title: string
  mark: string
  unlocked: boolean
}

// docs/15 §4.4.1：这里只描述入口状态，不承载或推断任何剧情内容。
const chapters: ChapterEntry[] = [
  { id: 'prologue', title: '序章', mark: '✦', unlocked: true },
  { id: 'chapter-1', title: '第一章', mark: '✧', unlocked: false },
  { id: 'chapter-2', title: '第二章', mark: '◇', unlocked: false },
  { id: 'chapter-3', title: '第三章', mark: '✥', unlocked: false },
  { id: 'chapter-4', title: '第四章', mark: '❖', unlocked: false },
  { id: 'finale', title: '终章', mark: '✤', unlocked: false },
]

const router = useRouter()
const game = useGameStore()
const opening = ref(false)
const error = ref<string | null>(null)

async function openChapter(chapter: ChapterEntry) {
  if (!chapter.unlocked || opening.value) return
  opening.value = true
  error.value = null
  try {
    // docs/19：「序章」进入固定剧本；结尾选择角色后再进入 AI 自由聊天。
    localStorage.removeItem('gal_session_id')
    game.sessionId = null
    game.pendingLoad = null
    await router.push('/story?story_id=prologue')
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    opening.value = false
  }
}
</script>

<template>
  <main class="chapter-select">
    <div class="chapter-bg" aria-hidden="true">
      <div class="chapter-bg-fill"></div>
      <div class="chapter-bg-sharp"></div>
    </div>

    <section class="chapter-panel" aria-labelledby="chapter-select-title">
      <header class="chapter-heading">
        <div class="heading-line"><span></span><i></i></div>
        <h1 id="chapter-select-title">开始游戏</h1>
        <div class="heading-line heading-line--right"><i></i><span></span></div>
        <p>章节选择</p>
      </header>

      <div class="chapter-grid">
        <button
          v-for="chapter in chapters"
          :key="chapter.id"
          class="chapter-card"
          :class="{ 'chapter-card--unlocked': chapter.unlocked, 'chapter-card--locked': !chapter.unlocked }"
          :disabled="!chapter.unlocked || opening"
          :aria-label="chapter.unlocked ? chapter.title : `${chapter.title}（未开发）`"
          @click="openChapter(chapter)"
        >
          <span class="chapter-emblem" aria-hidden="true">{{ chapter.mark }}</span>
          <span class="chapter-name">{{ chapter.title }}</span>
          <span v-if="!chapter.unlocked" class="chapter-lock">
            <span aria-hidden="true">▣</span> 未开发
          </span>
          <span v-else class="chapter-ready">{{ opening ? '进入中…' : '已解锁' }}</span>
        </button>
      </div>

      <p v-if="error" class="chapter-error" role="alert">{{ error }}</p>
      <div class="panel-ornament" aria-hidden="true"><span></span><i>◇</i><span></span></div>
    </section>

    <button class="chapter-back" type="button" @click="router.push('/')">
      <span aria-hidden="true">↶</span> 返回
    </button>
  </main>
</template>

<style scoped>
.chapter-select {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 32rem;
  overflow: auto;
  padding: clamp(1rem, 4vh, 2.5rem) clamp(1rem, 6vw, 7rem) clamp(5.5rem, 11vh, 7rem);
  color: #172650;
  isolation: isolate;
}

.chapter-bg,
.chapter-bg > div {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.chapter-bg {
  z-index: -2;
  overflow: hidden;
  background: #202650;
}

.chapter-bg-fill,
.chapter-bg-sharp {
  background-image: url('/backgroud/background_title_21x9.png');
  background-position: center;
  background-repeat: no-repeat;
}

.chapter-bg-fill {
  background-size: cover;
  filter: blur(26px) brightness(0.62) saturate(0.9);
  transform: scale(1.09);
}

.chapter-bg-sharp {
  background-size: cover;
}

.chapter-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(14, 21, 57, 0.08), rgba(12, 17, 45, 0.3));
}

.chapter-panel {
  position: relative;
  width: min(74rem, 100%);
  margin: auto;
  padding: clamp(1rem, 2.6vh, 2rem) clamp(1rem, 3vw, 3rem) clamp(1rem, 2vh, 1.5rem);
  border: 2px solid rgba(222, 217, 232, 0.85);
  border-radius: clamp(1.1rem, 2vw, 2rem);
  background:
    linear-gradient(135deg, transparent 18px, rgba(250, 249, 253, 0.91) 0) top left,
    linear-gradient(-135deg, transparent 18px, rgba(250, 249, 253, 0.91) 0) top right,
    linear-gradient(45deg, transparent 18px, rgba(250, 249, 253, 0.91) 0) bottom left,
    linear-gradient(-45deg, transparent 18px, rgba(250, 249, 253, 0.91) 0) bottom right;
  background-size: 51% 51%;
  background-repeat: no-repeat;
  box-shadow: 0 1.5rem 4rem rgba(17, 22, 61, 0.4), inset 0 0 0 5px rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(9px) saturate(0.8);
}

.chapter-panel::before {
  content: '';
  position: absolute;
  inset: 0.65rem;
  border: 1px solid rgba(119, 111, 148, 0.24);
  border-radius: calc(clamp(1.1rem, 2vw, 2rem) - 0.3rem);
  pointer-events: none;
}

.chapter-heading {
  display: grid;
  grid-template-columns: minmax(2rem, 1fr) auto minmax(2rem, 1fr);
  align-items: center;
  column-gap: clamp(0.75rem, 2vw, 1.7rem);
  text-align: center;
  margin-bottom: clamp(0.8rem, 2vh, 1.3rem);
}

.chapter-heading h1 {
  margin: 0;
  font-family: inherit;
  font-size: clamp(2.3rem, 5vw, 4.6rem);
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.08em;
  color: #172451;
  text-shadow: 0 2px 0 rgba(255, 255, 255, 0.75);
}

.chapter-heading p {
  grid-column: 1 / -1;
  margin: clamp(0.45rem, 1vh, 0.8rem) 0 0;
  font-family: inherit;
  font-size: clamp(1rem, 1.7vw, 1.45rem);
  letter-spacing: 0.22em;
}

.heading-line {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  color: #9d91a9;
}

.heading-line span {
  width: min(12rem, 100%);
  height: 1px;
  background: linear-gradient(90deg, transparent, currentColor);
}

.heading-line i {
  width: 0.65rem;
  height: 0.65rem;
  background: currentColor;
  transform: rotate(45deg);
}

.heading-line--right {
  justify-content: flex-start;
}

.heading-line--right span {
  background: linear-gradient(90deg, currentColor, transparent);
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: clamp(0.65rem, 1.5vh, 1rem) clamp(0.8rem, 2vw, 2rem);
}

.chapter-card {
  position: relative;
  display: grid;
  grid-template-columns: clamp(3.5rem, 6vw, 5.5rem) 1fr auto;
  align-items: center;
  min-height: clamp(5.25rem, 13.2vh, 8.75rem);
  padding: 0.65rem clamp(0.8rem, 2vw, 1.5rem) 0.65rem clamp(0.7rem, 1.5vw, 1.1rem);
  overflow: hidden;
  border: 2px solid rgba(70, 76, 132, 0.72);
  clip-path: polygon(4% 0, 96% 0, 100% 17%, 100% 83%, 96% 100%, 4% 100%, 0 83%, 0 17%);
  background:
    linear-gradient(100deg, rgba(242, 239, 255, 0.96), rgba(203, 216, 248, 0.82)),
    radial-gradient(circle at 80% 20%, rgba(141, 159, 225, 0.45), transparent 55%);
  color: #14214d;
  font: inherit;
  text-align: left;
  box-shadow: inset 0 0 0 4px rgba(255, 255, 255, 0.55), 0 0.35rem 0.65rem rgba(23, 29, 68, 0.18);
  transition: transform 180ms ease, filter 180ms ease, box-shadow 180ms ease;
}

.chapter-card::after {
  content: '';
  position: absolute;
  right: -8%;
  bottom: -55%;
  width: 58%;
  aspect-ratio: 1;
  border-radius: 50%;
  border: 1px solid rgba(71, 83, 145, 0.18);
  box-shadow: 0 0 0 1.2rem rgba(92, 112, 177, 0.07), 0 0 0 2.6rem rgba(92, 112, 177, 0.05);
}

.chapter-card--unlocked {
  cursor: pointer;
  background: linear-gradient(105deg, rgba(244, 239, 255, 0.98), rgba(184, 187, 239, 0.86));
}

.chapter-card--unlocked:hover,
.chapter-card--unlocked:focus-visible {
  z-index: 1;
  transform: translateY(-3px) scale(1.012);
  filter: brightness(1.04);
  box-shadow: inset 0 0 0 4px rgba(255, 255, 255, 0.72), 0 0.65rem 1.2rem rgba(34, 37, 91, 0.28);
  outline: none;
}

.chapter-card--locked {
  cursor: not-allowed;
  filter: grayscale(0.78) saturate(0.35);
  opacity: 0.62;
}

.chapter-emblem {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: clamp(2.8rem, 5vw, 4.6rem);
  aspect-ratio: 1;
  border: 2px solid rgba(255, 255, 255, 0.9);
  outline: 1px solid rgba(52, 61, 119, 0.75);
  background: linear-gradient(145deg, #7378ac, #31396f);
  color: white;
  font-size: clamp(1.2rem, 2.2vw, 2rem);
  transform: rotate(45deg) scale(0.72);
  box-shadow: 0 0.25rem 0.6rem rgba(28, 31, 75, 0.3);
}

.chapter-emblem::first-letter {
  transform: rotate(-45deg);
}

.chapter-name {
  position: relative;
  z-index: 1;
  font-family: inherit;
  font-size: clamp(1.65rem, 3.3vw, 3.2rem);
  font-weight: 700;
  letter-spacing: 0.08em;
  text-align: center;
  white-space: nowrap;
}

.chapter-lock,
.chapter-ready {
  position: relative;
  z-index: 1;
  align-self: end;
  padding-bottom: 0.25rem;
  font-size: clamp(0.66rem, 1vw, 0.82rem);
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.chapter-lock { color: #4f5266; }
.chapter-ready { color: #435a91; }

.panel-ornament {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  margin-top: clamp(0.7rem, 1.3vh, 1rem);
  color: rgba(150, 128, 117, 0.58);
}

.panel-ornament span {
  width: clamp(2.5rem, 7vw, 6rem);
  height: 1px;
  background: currentColor;
}

.panel-ornament i { font-style: normal; }

.chapter-error {
  margin: 0.75rem 0 0;
  color: #9f2437;
  text-align: center;
}

.chapter-back {
  position: fixed;
  left: clamp(1rem, 3vw, 3.2rem);
  bottom: clamp(1rem, 3vh, 2rem);
  z-index: 2;
  min-width: clamp(8rem, 14vw, 12rem);
  padding: 0.55rem 1.2rem;
  border: 1px solid rgba(221, 226, 255, 0.82);
  clip-path: polygon(9% 0, 91% 0, 100% 50%, 91% 100%, 9% 100%, 0 50%);
  background: linear-gradient(180deg, rgba(45, 57, 112, 0.94), rgba(29, 38, 82, 0.96));
  color: #f7f8ff;
  font-family: inherit;
  font-size: clamp(1.15rem, 2vw, 1.8rem);
  letter-spacing: 0.12em;
  cursor: pointer;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.45);
  transition: transform 180ms ease, filter 180ms ease;
}

.chapter-back:hover,
.chapter-back:focus-visible {
  transform: translateX(-3px);
  filter: brightness(1.16);
  outline: none;
}

@media (min-aspect-ratio: 49 / 20) {
  .chapter-bg-sharp { background-size: auto 100%; }
}

@media (max-width: 700px) {
  .chapter-select {
    min-height: 100%;
    /* 为 App 全局账号状态条预留安全区，避免遮住「开始游戏」标题。 */
    padding: 4.25rem 0.75rem 5.5rem;
  }

  .chapter-panel { padding: 1rem 0.75rem; }
  .chapter-heading { grid-template-columns: 1fr auto 1fr; }
  .chapter-grid { grid-template-columns: 1fr; }
  .chapter-card { min-height: 5.4rem; }
  .chapter-back { position: fixed; }
}

@media (prefers-reduced-motion: reduce) {
  .chapter-card,
  .chapter-back { transition: none; }
}
</style>
