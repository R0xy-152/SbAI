<script setup lang="ts">
import { computed, ref } from 'vue'
import type { TrialEvidence } from '../../api/trial'

const props = defineProps<{
  selected: TrialEvidence[]
  selectionMin: number
  selectionMax: number
  busy: boolean
}>()

const emit = defineEmits<{
  (event: 'remove', evidenceId: string): void
  (event: 'submit', message: string): void
}>()

const root = ref<HTMLElement | null>(null)
const message = ref('')
const canSubmit = computed(
  () =>
    !props.busy &&
    props.selected.length >= props.selectionMin &&
    props.selected.length <= props.selectionMax &&
    Boolean(message.value.trim()),
)

function containsPoint(clientX: number, clientY: number): boolean {
  const rect = root.value?.getBoundingClientRect()
  return Boolean(
    rect && clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom,
  )
}

function submit() {
  if (!canSubmit.value) return
  emit('submit', message.value.trim())
}

defineExpose({ containsPoint })
</script>

<template>
  <aside ref="root" class="reasoning-tray" data-reasoning-tray data-testid="reasoning-tray">
    <header>
      <div>
        <small>REASONING BUFFER</small>
        <h2>推理槽</h2>
      </div>
      <span>{{ selected.length }} / {{ selectionMax }}</span>
    </header>

    <div class="selected-evidence" :class="{ empty: selected.length === 0 }">
      <p v-if="selected.length === 0">把关键证据拖到这里</p>
      <button
        v-for="item in selected"
        :key="item.evidence_id"
        type="button"
        :aria-label="`移除 ${item.title}`"
        @click="emit('remove', item.evidence_id)"
      >
        <span>{{ item.title }}</span><i aria-hidden="true">×</i>
      </button>
    </div>

    <label for="trial-reasoning-input">你的推理</label>
    <textarea
      id="trial-reasoning-input"
      v-model="message"
      rows="6"
      maxlength="4000"
      placeholder="结合选中的证据，说出你的判断……"
      @keydown.meta.enter.prevent="submit"
      @keydown.ctrl.enter.prevent="submit"
    ></textarea>
    <button class="submit-reasoning" type="button" :disabled="!canSubmit" @click="submit">
      {{ busy ? '提交中…' : '提交推理' }}
    </button>
    <small class="submit-hint">至少 {{ selectionMin }} 条，最多 {{ selectionMax }} 条证据</small>
  </aside>
</template>

<style scoped>
.reasoning-tray {
  display: flex;
  min-width: 18rem;
  flex-direction: column;
  gap: 0.8rem;
  padding: 1.1rem;
  border: 1px solid rgba(121, 222, 255, 0.38);
  border-radius: 1rem;
  color: #e9faff;
  background: linear-gradient(155deg, rgba(3, 15, 24, 0.96), rgba(7, 26, 37, 0.9));
  box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.32);
}

header { display: flex; align-items: flex-end; justify-content: space-between; }
header small { color: #5fa8bc; font-size: 0.62rem; letter-spacing: 0.17em; }
h2 { margin: 0.1rem 0 0; color: #9deaff; font-size: 1.35rem; }
header > span {
  padding: 0.25rem 0.55rem;
  border: 1px solid rgba(126, 221, 248, 0.26);
  border-radius: 999px;
  color: #8dc7d5;
  font-size: 0.75rem;
}

.selected-evidence {
  display: flex;
  min-height: 7.6rem;
  align-content: flex-start;
  flex-wrap: wrap;
  gap: 0.55rem;
  padding: 0.75rem;
  border: 1px dashed rgba(132, 225, 250, 0.32);
  border-radius: 0.75rem;
  background: rgba(3, 9, 15, 0.44);
}
.selected-evidence.empty { align-items: center; justify-content: center; }
.selected-evidence p { margin: 0; color: #7198a4; font-size: 0.8rem; }
.selected-evidence button {
  display: flex;
  height: fit-content;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.65rem;
  border: 1px solid rgba(138, 228, 255, 0.4);
  border-radius: 999px;
  color: #dff8ff;
  background: rgba(21, 72, 91, 0.56);
  cursor: pointer;
}
.selected-evidence i { color: #ff8ca2; font-style: normal; }

label { color: #8edcf1; font-size: 0.78rem; letter-spacing: 0.12em; }
textarea {
  width: 100%;
  min-height: 7.5rem;
  resize: vertical;
  border: 1px solid rgba(125, 220, 248, 0.28);
  border-radius: 0.65rem;
  padding: 0.75rem;
  color: #f2fbff;
  background: rgba(1, 6, 11, 0.62);
  font: inherit;
  line-height: 1.65;
  outline: none;
}
textarea:focus { border-color: #82daf3; box-shadow: 0 0 0 3px rgba(85, 199, 235, 0.12); }
.submit-reasoning {
  border: 1px solid rgba(141, 231, 255, 0.58);
  border-radius: 0.6rem;
  padding: 0.72rem;
  color: #041018;
  background: linear-gradient(110deg, #a9efff, #5bc8e8);
  font-weight: 850;
  cursor: pointer;
}
.submit-reasoning:disabled { cursor: not-allowed; filter: grayscale(0.7); opacity: 0.45; }
.submit-hint { color: #729ba7; text-align: center; }
</style>
