<script setup lang="ts">
import type { TrialChoiceOption } from '../../api/trial'

defineProps<{
  prompt: string
  options: TrialChoiceOption[]
  busy?: boolean
}>()
const emit = defineEmits<{ (event: 'choose', optionId: string): void }>()
</script>

<template>
  <div class="choice-panel" role="group" :aria-label="prompt">
    <p class="choice-prompt">{{ prompt }}</p>
    <div class="choice-options">
      <button
        v-for="option in options"
        :key="option.option_id"
        type="button"
        :disabled="busy"
        @click="emit('choose', option.option_id)"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.choice-panel {
  position: absolute;
  right: clamp(1rem, 6vw, 6rem);
  bottom: clamp(1rem, 5vh, 3.6rem);
  left: clamp(1rem, 6vw, 6rem);
  z-index: 14;
  padding: 1rem;
  border: 1px solid rgba(137, 225, 255, 0.42);
  border-radius: 0.85rem;
  background: rgba(2, 11, 19, 0.92);
  backdrop-filter: blur(14px);
}
.choice-prompt { margin: 0 0 0.85rem; color: #8ddff7; font-weight: 750; line-height: 1.55; }
.choice-options { display: grid; gap: 0.55rem; }
button {
  border: 1px solid rgba(134, 220, 245, 0.3);
  border-radius: 0.55rem;
  padding: 0.7rem 1rem;
  color: #eafaff;
  background: rgba(9, 42, 55, 0.6);
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
button:hover:not(:disabled) { border-color: rgba(146, 233, 255, 0.7); background: rgba(18, 88, 111, 0.72); }
button:disabled { cursor: not-allowed; opacity: 0.45; }
</style>
