<script setup lang="ts">
import { ref } from 'vue'
import type { TrialMemoryItem } from '../../api/trial'

const props = defineProps<{
  items: TrialMemoryItem[]
  diff: { original: string; edited: string; editor: string; timestamp: string }
  busy?: boolean
}>()
const emit = defineEmits<{ (event: 'continue'): void }>()

const opened = ref(false)
const active = ref<TrialMemoryItem | null>(null)

function open(item: TrialMemoryItem) {
  active.value = item
  opened.value = true
}
</script>

<template>
  <div class="memory-tamper">
    <div class="orbit" role="list">
      <button
        v-for="(item, index) in props.items"
        :key="index"
        type="button"
        class="orb"
        :class="{ tampered: item.edited_title !== item.title }"
        @click="open(item)"
      >
        {{ item.edited_title }}
      </button>
    </div>

    <button class="mt-continue" type="button" :disabled="busy" @click="emit('continue')">
      {{ busy ? '处理中…' : '继续' }}
    </button>

    <div v-if="opened" class="mt-detail" role="dialog" aria-modal="true">
      <section>
        <small>EDIT RECORD · DIFF</small>
        <div v-if="active" class="mt-summary">{{ active.summary }}</div>
        <div class="diff">
          <div class="diff-col">
            <span class="diff-label">原始</span>
            <span class="diff-word old">{{ props.diff.original }}</span>
          </div>
          <div class="diff-arrow" aria-hidden="true">→</div>
          <div class="diff-col">
            <span class="diff-label">修改后</span>
            <span class="diff-word new">{{ props.diff.edited }}</span>
          </div>
        </div>
        <div class="diff-meta">编辑者 {{ props.diff.editor }} · {{ props.diff.timestamp }}</div>
        <button type="button" @click="opened = false">关闭</button>
      </section>
    </div>
  </div>
</template>

<style scoped>
.memory-tamper {
  position: absolute;
  inset: 4.8rem 1rem 1rem;
  z-index: 16;
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 1.2rem;
}
.orbit { display: flex; flex-wrap: wrap; justify-content: center; gap: 1.2rem; }
.orb {
  width: 5.6rem;
  height: 5.6rem;
  border: 1px solid rgba(146, 233, 255, 0.4);
  border-radius: 50%;
  color: #dff8ff;
  background: radial-gradient(circle at 32% 28%, rgba(70, 199, 237, 0.32), rgba(4, 22, 32, 0.9));
  box-shadow: 0 0 22px rgba(70, 199, 237, 0.22);
  font-weight: 750;
  cursor: pointer;
}
.orb.tampered { border-color: #ff5f77; color: #ffd7de; box-shadow: 0 0 26px rgba(255, 60, 90, 0.4); }
.mt-continue {
  border: 1px solid rgba(142, 229, 255, 0.52);
  border-radius: 999px;
  padding: 0.7rem 1.6rem;
  color: #e7faff;
  background: rgba(5, 25, 36, 0.84);
  font-weight: 750;
  cursor: pointer;
}
.mt-continue:disabled { cursor: not-allowed; opacity: 0.42; }
.mt-detail {
  position: absolute;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  background: rgba(0, 4, 8, 0.72);
  backdrop-filter: blur(12px);
}
.mt-detail section {
  width: min(34rem, calc(100% - 2rem));
  padding: 1.5rem;
  border: 1px solid rgba(137, 227, 253, 0.42);
  border-radius: 1rem;
  background: linear-gradient(145deg, rgba(4, 18, 28, 0.98), rgba(7, 31, 43, 0.96));
}
.mt-detail small { color: #63b9d0; letter-spacing: 0.18em; }
.mt-summary { margin: 1rem 0; color: #cce4eb; line-height: 1.7; }
.diff { display: flex; align-items: center; gap: 1rem; margin: 1rem 0; }
.diff-col { display: grid; justify-items: center; gap: 0.3rem; }
.diff-label { color: #6b9aa8; font-size: 0.72rem; }
.diff-word { font-size: 1.7rem; font-weight: 800; }
.diff-word.old { color: #a4ecff; text-decoration: line-through; opacity: 0.75; }
.diff-word.new { color: #ff7d92; }
.diff-arrow { color: #63b9d0; }
.diff-meta { color: #6b9aa8; font: 0.72rem/1.4 monospace; }
.mt-detail section > button {
  float: right;
  border: 1px solid rgba(142, 229, 255, 0.52);
  border-radius: 0.55rem;
  padding: 0.55rem 1rem;
  color: #e7faff;
  background: rgba(18, 88, 111, 0.62);
  cursor: pointer;
}
</style>
