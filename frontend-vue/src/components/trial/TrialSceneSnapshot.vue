<script setup lang="ts">
import { computed } from 'vue'
import type { TrialLine, TrialScene } from '../../api/trial'

const props = defineProps<{
  scene: TrialScene
  node: TrialLine | null
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
</script>

<template>
  <div class="trial-snapshot" :style="{ backgroundImage: `url(${scene.background})` }">
    <div class="trial-snapshot__shade" aria-hidden="true"></div>
    <div class="trial-snapshot__scan" aria-hidden="true"></div>

    <div class="trial-snapshot__stage" aria-hidden="true">
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

    <div v-if="node" class="trial-snapshot__dialogue">
      <div class="trial-snapshot__speaker" :class="{ redacted: node.speaker_id === 'origin_ai' }">
        {{ node.speaker_label }}
      </div>
      <p>{{ node.text }}</p>
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

.trial-snapshot__dialogue {
  position: absolute;
  right: clamp(1rem, 7vw, 7rem);
  bottom: clamp(1rem, 4vh, 3rem);
  left: clamp(1rem, 7vw, 7rem);
  min-height: 8.5rem;
  padding: 1.25rem 1.6rem 1.35rem;
  border: 1px solid rgba(137, 225, 255, 0.44);
  border-radius: 0.5rem;
  background: linear-gradient(135deg, rgba(2, 10, 18, 0.9), rgba(8, 23, 35, 0.74));
  box-shadow:
    0 1.25rem 3.5rem rgba(0, 0, 0, 0.45),
    inset 0 0 28px rgba(79, 200, 255, 0.06);
  backdrop-filter: blur(12px);
}

.trial-snapshot__speaker {
  width: fit-content;
  margin-bottom: 0.55rem;
  color: #9be7ff;
  font-size: clamp(1rem, 1.7vw, 1.35rem);
  font-weight: 800;
  letter-spacing: 0.08em;
}

.trial-snapshot__speaker.redacted {
  color: transparent;
  text-shadow: 0 0 7px rgba(177, 240, 255, 0.95);
  background: repeating-linear-gradient(90deg, #b8f2ff 0 7px, #07131f 7px 13px);
  background-clip: text;
  filter: blur(1.2px);
}

.trial-snapshot__dialogue p {
  margin: 0;
  font-size: clamp(1rem, 1.55vw, 1.3rem);
  font-weight: 650;
  line-height: 1.8;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.9);
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
  .trial-snapshot__dialogue { min-height: 10rem; }
}
</style>
