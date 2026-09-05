<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  prompt: string
  placeholder: string
  label: string
  busy?: boolean
}>()
const emit = defineEmits<{ (event: 'submit', message: string): void }>()

const text = ref('')

function submit() {
  const message = text.value.trim()
  if (!message) return
  text.value = ''
  emit('submit', message)
}
</script>

<template>
  <div class="judgment-input">
    <label>{{ prompt }}</label>
    <textarea
      v-model="text"
      :placeholder="placeholder"
      rows="2"
      @keydown.enter.exact.prevent="submit"
    ></textarea>
    <button type="button" :disabled="busy || !text.trim()" @click="submit">
      {{ busy ? '处理中…' : label }}
    </button>
  </div>
</template>

<style scoped>
.judgment-input {
  position: absolute;
  right: clamp(1rem, 7vw, 7rem);
  bottom: clamp(1rem, 4vh, 3rem);
  left: clamp(1rem, 7vw, 7rem);
  z-index: 14;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.7rem;
  padding: 1rem;
  border: 1px solid rgba(137, 225, 255, 0.44);
  border-radius: 0.75rem;
  background: rgba(2, 11, 19, 0.92);
  backdrop-filter: blur(14px);
}
label { grid-column: 1 / -1; color: #8ddff7; font-weight: 750; }
textarea {
  resize: none;
  border: 1px solid rgba(134, 220, 245, 0.26);
  border-radius: 0.55rem;
  padding: 0.7rem;
  color: white;
  background: rgba(1, 6, 10, 0.74);
  font: inherit;
  outline: none;
}
button {
  border: 1px solid rgba(142, 229, 255, 0.52);
  border-radius: 0.55rem;
  padding: 0.65rem 1rem;
  color: #e7faff;
  background: rgba(18, 88, 111, 0.62);
  font-weight: 750;
  cursor: pointer;
}
button:disabled { cursor: not-allowed; opacity: 0.42; }
@media (max-width: 760px) {
  .judgment-input { grid-template-columns: 1fr; }
  label { grid-column: 1; }
}
</style>
