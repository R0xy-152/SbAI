<template>
  <div
    v-if="visible"
    class="chapter-opening fixed inset-0 z-[20000] overflow-hidden"
    role="status"
    aria-live="polite"
    data-testid="chapter-opening"
  >
    <div
      class="chapter-opening-bg absolute inset-[-3%]"
      :style="{ backgroundImage: `url(${background})` }"
    ></div>
    <div class="chapter-opening-shade absolute inset-0"></div>

    <div class="chapter-frame absolute inset-[3.2%]" aria-hidden="true">
      <span class="corner corner-tl"></span>
      <span class="corner corner-tr"></span>
      <span class="corner corner-bl"></span>
      <span class="corner corner-br"></span>
    </div>

    <div class="chapter-ribbon absolute inset-x-[3.2%] top-1/2">
      <div class="chapter-ribbon-facet facet-left" aria-hidden="true"></div>
      <div class="chapter-ribbon-facet facet-right" aria-hidden="true"></div>
      <div class="chapter-copy">
        <p class="chapter-label">{{ chapterLabel }}</p>
        <span class="chapter-accent" aria-hidden="true"></span>
        <h1 class="chapter-title">{{ title }}</h1>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

defineProps<{
  chapterLabel: string
  title: string
  background: string
}>()

const emit = defineEmits<{ (event: 'complete'): void }>()
const visible = ref(true)
let timer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  timer = setTimeout(() => {
    visible.value = false
    emit('complete')
  }, reduced ? 1500 : 3800)
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})
</script>

<style scoped>
.chapter-opening {
  pointer-events: auto;
  animation: opening-life 3.8s both cubic-bezier(0.22, 1, 0.36, 1);
  color: #173a62;
}

.chapter-opening-bg {
  background-position: center;
  background-size: cover;
  filter: blur(15px) brightness(0.55) saturate(0.72);
  transform: scale(1.1);
  animation: background-drift 3.8s both ease-out;
}

.chapter-opening-shade {
  background:
    radial-gradient(circle at 50% 50%, rgba(101, 164, 199, 0.12), transparent 55%),
    linear-gradient(180deg, rgba(3, 9, 18, 0.34), rgba(3, 8, 17, 0.48));
}

.chapter-frame {
  border: 1px solid rgba(216, 240, 250, 0.55);
  box-shadow:
    inset 0 0 0 5px rgba(207, 234, 246, 0.13),
    0 0 24px rgba(2, 12, 24, 0.3);
  animation: frame-reveal 0.9s 0.18s both cubic-bezier(0.22, 1, 0.36, 1);
}

.corner {
  position: absolute;
  width: 2.1rem;
  height: 2.1rem;
  opacity: 0.78;
}

.corner::before,
.corner::after {
  content: '';
  position: absolute;
  background: rgba(225, 244, 252, 0.75);
}

.corner::before { width: 100%; height: 1px; }
.corner::after { width: 1px; height: 100%; }
.corner-tl { left: 0.75rem; top: 0.75rem; }
.corner-tr { right: 0.75rem; top: 0.75rem; transform: rotate(90deg); }
.corner-bl { left: 0.75rem; bottom: 0.75rem; transform: rotate(-90deg); }
.corner-br { right: 0.75rem; bottom: 0.75rem; transform: rotate(180deg); }

.chapter-ribbon {
  height: clamp(13rem, 25vh, 18rem);
  transform: translateY(-50%) scaleX(0);
  transform-origin: center;
  background:
    linear-gradient(90deg, rgba(178, 215, 232, 0.82), rgba(247, 251, 252, 0.97) 30%, rgba(255, 255, 255, 0.98) 50%, rgba(224, 241, 248, 0.9) 72%, rgba(172, 207, 226, 0.82));
  border-block: 1px solid rgba(197, 228, 241, 0.8);
  box-shadow: 0 12px 42px rgba(0, 12, 28, 0.28);
  animation: ribbon-open 0.72s 0.55s both cubic-bezier(0.16, 1, 0.3, 1);
}

.chapter-ribbon-facet {
  position: absolute;
  inset-block: 0;
  width: min(18vw, 20rem);
  opacity: 0.24;
  background: linear-gradient(135deg, rgba(33, 92, 129, 0.22), transparent 58%);
}

.facet-left { left: 0; clip-path: polygon(0 0, 58% 0, 100% 100%, 20% 100%); }
.facet-right { right: 0; transform: scaleX(-1); clip-path: polygon(0 0, 58% 0, 100% 100%, 20% 100%); }

.chapter-copy {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: translateY(0.9rem);
  animation: copy-arrive 0.7s 1.05s both ease-out;
}

.chapter-label {
  margin: 0;
  font-size: clamp(1rem, 1.5vw, 1.45rem);
  font-weight: 600;
  letter-spacing: 0.22em;
  color: #273b52;
}

.chapter-accent {
  width: 4.2rem;
  height: 0.2rem;
  margin-top: -0.12rem;
  background: linear-gradient(90deg, transparent, #efcf45 22%, #efcf45 78%, transparent);
  transform: scaleX(0);
  animation: accent-draw 0.55s 1.42s both ease-out;
}

.chapter-title {
  margin: 1.2rem 1rem 0;
  max-width: 90%;
  text-align: center;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', serif;
  font-size: clamp(2rem, 4vw, 4rem);
  font-weight: 600;
  line-height: 1.16;
  letter-spacing: 0.09em;
  color: #315986;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.8);
}

@keyframes opening-life {
  0% { opacity: 0; }
  10%, 82% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes background-drift {
  from { transform: scale(1.12); }
  to { transform: scale(1.06); }
}

@keyframes frame-reveal {
  from { opacity: 0; clip-path: inset(48% 48%); }
  to { opacity: 1; clip-path: inset(0); }
}

@keyframes ribbon-open {
  from { transform: translateY(-50%) scaleX(0); opacity: 0; }
  to { transform: translateY(-50%) scaleX(1); opacity: 1; }
}

@keyframes copy-arrive {
  to { opacity: 1; transform: translateY(0); }
}

@keyframes accent-draw {
  to { transform: scaleX(1); }
}

@media (prefers-reduced-motion: reduce) {
  .chapter-opening { animation: opening-life 1.5s both linear; }
  .chapter-opening-bg,
  .chapter-frame,
  .chapter-ribbon,
  .chapter-copy,
  .chapter-accent {
    animation: none;
  }
  .chapter-opening-bg { transform: scale(1.06); }
  .chapter-frame { opacity: 1; }
  .chapter-ribbon { transform: translateY(-50%) scaleX(1); }
  .chapter-copy { opacity: 1; transform: none; }
  .chapter-accent { transform: scaleX(1); }
}

@media (max-width: 640px) {
  .chapter-frame { inset: 2.2%; }
  .chapter-ribbon { inset-inline: 2.2%; height: 12rem; }
  .chapter-title { font-size: clamp(1.65rem, 8vw, 2.4rem); letter-spacing: 0.04em; }
}
</style>
