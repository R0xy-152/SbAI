<script setup lang="ts">
import { computed, ref } from 'vue'
import type { GameOption } from '../../../api/game'

// docs/14 §2.2（T3，D6）：需要上下文的小型面板——evidence_present
//（选证据×角色）与 private_interview（选证词/观察/证据）。选项 payload 由
// 后端随 options 下发（D7），本组件只渲染标签并回传所选 id，不解释语义。
const props = defineProps<{
  option: GameOption
  busy: boolean
  message: string | null
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: { character_id: string; claim_ids: string[]; evidence_ids: string[] }]
}>()

type PanelPayload = {
  character_id: string
  characters?: string[]
  claims?: Array<{ id: string; text: string; preselected?: boolean }>
  evidence?: Array<{ id: string; title?: string; text?: string; summary?: string }>
  observation_options?: Array<{ id: string; text: string }>
}

const payload = computed(() => props.option.payload as PanelPayload)
const isEvidence = computed(() => props.option.kind === 'evidence_present')

const CHARACTER_NAMES: Record<string, string> = {
  deepseek: 'DeepSeek',
  claude: 'Claude',
  chatgpt: 'ChatGPT',
  doubao: '豆包',
}

const selectedEvidenceId = ref<string | null>(null)
const selectedCharacterId = ref<string | null>(null)
const checkedClaims = ref<Set<string>>(new Set())
const selectedObservationId = ref<string | null>(null)

function init() {
  const p = payload.value
  selectedEvidenceId.value = null
  selectedCharacterId.value = null
  selectedObservationId.value = null
  const preselected = new Set<string>()
  for (const c of p.claims ?? []) {
    if (c.preselected) preselected.add(c.id)
  }
  checkedClaims.value = preselected
  // 单条证据（GPT 私审）自动选中
  if (!isEvidence.value && (p.evidence ?? []).length === 1) {
    selectedEvidenceId.value = p.evidence?.[0]?.id ?? null
  }
}

init()

function toggleClaim(id: string) {
  const next = new Set(checkedClaims.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  checkedClaims.value = next
}

const canSubmit = computed(() => {
  const p = payload.value
  if (isEvidence.value) {
    return selectedEvidenceId.value !== null && selectedCharacterId.value !== null
  }
  if ((p.observation_options ?? []).length > 0) {
    return selectedObservationId.value !== null
  }
  return true
})

function onSubmit() {
  if (props.busy || !canSubmit.value) return
  const p = payload.value
  if (isEvidence.value) {
    emit('submit', {
      character_id: selectedCharacterId.value ?? p.character_id,
      claim_ids: [],
      evidence_ids: selectedEvidenceId.value ? [selectedEvidenceId.value] : [],
    })
    return
  }
  // private_interview：GPT 用 evidence、豆包用 observation（都走 evidence_ids 通道）
  const evidenceIds =
    (p.observation_options ?? []).length > 0
      ? selectedObservationId.value
        ? [selectedObservationId.value]
        : []
      : selectedEvidenceId.value
        ? [selectedEvidenceId.value]
        : []
  emit('submit', {
    character_id: p.character_id,
    claim_ids: Array.from(checkedClaims.value),
    evidence_ids: evidenceIds,
  })
}
</script>

<template>
  <div
    data-testid="sub-action-panel"
    class="fixed inset-0 z-30 flex items-center justify-center bg-black/70"
    @click.self="emit('close')"
  >
    <div class="flex max-h-[85vh] w-[min(92vw,560px)] flex-col rounded-xl border border-white/15 bg-[#0b1424]/95 p-5 text-[#f4f8ff] shadow-2xl">
      <header class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-bold text-[#dff7ff]">{{ option.label }}</h2>
        <button class="text-sm text-[#d7effa]/70 hover:text-[#dff7ff]" @click="emit('close')">关闭</button>
      </header>

      <main class="flex flex-col gap-3 overflow-y-auto pr-1">
        <p v-if="option.hint" class="text-xs text-[#a9e8ff]/80">{{ option.hint }}</p>

        <!-- 出示证据：证据 × 在场角色 -->
        <template v-if="isEvidence">
          <fieldset class="flex flex-col gap-1.5">
            <legend class="mb-1 text-sm text-[#d7effa]">选择证据</legend>
            <label
              v-for="e in payload.evidence ?? []"
              :key="e.id"
              class="cursor-pointer rounded border border-white/10 bg-black/30 p-2"
              :class="selectedEvidenceId === e.id ? 'border-[#04bcff]/60' : ''"
            >
              <span class="flex items-start gap-2">
                <input v-model="selectedEvidenceId" type="radio" :value="e.id" class="mt-1" />
                <span class="flex flex-col gap-0.5">
                  <span class="text-sm text-[#dff7ff]">{{ e.title }}</span>
                  <span class="whitespace-pre-wrap text-xs text-[#a9e8ff]/70">{{ e.summary }}</span>
                </span>
              </span>
            </label>
          </fieldset>
          <fieldset class="flex flex-col gap-1.5">
            <legend class="mb-1 text-sm text-[#d7effa]">出示给</legend>
            <label
              v-for="cid in payload.characters ?? []"
              :key="cid"
              class="cursor-pointer rounded border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-[#d7effa]"
              :class="selectedCharacterId === cid ? 'border-[#04bcff]/60' : ''"
            >
              <input v-model="selectedCharacterId" type="radio" :value="cid" class="mr-2" />
              {{ CHARACTER_NAMES[cid] ?? cid }}
            </label>
          </fieldset>
        </template>

        <!-- 私审质询 -->
        <template v-else>
          <fieldset v-if="(payload.claims ?? []).length" class="flex flex-col gap-1.5">
            <legend class="mb-1 text-sm text-[#d7effa]">证词</legend>
            <label
              v-for="c in payload.claims"
              :key="c.id"
              class="cursor-pointer rounded border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-[#d7effa]"
              :class="checkedClaims.has(c.id) ? 'border-[#04bcff]/60' : ''"
            >
              <input type="checkbox" class="mr-2" :checked="checkedClaims.has(c.id)" @change="toggleClaim(c.id)" />
              {{ c.text }}
            </label>
          </fieldset>
          <fieldset v-if="(payload.evidence ?? []).length" class="flex flex-col gap-1.5">
            <legend class="mb-1 text-sm text-[#d7effa]">关键证据</legend>
            <label
              v-for="e in payload.evidence"
              :key="e.id"
              class="cursor-pointer rounded border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-[#d7effa]"
              :class="selectedEvidenceId === e.id ? 'border-[#04bcff]/60' : ''"
            >
              <input v-model="selectedEvidenceId" type="radio" :value="e.id" class="mr-2" />
              {{ e.text ?? e.title }}
            </label>
          </fieldset>
          <fieldset v-if="(payload.observation_options ?? []).length" class="flex flex-col gap-1.5">
            <legend class="mb-1 text-sm text-[#d7effa]">她实际看到了什么？</legend>
            <label
              v-for="o in payload.observation_options"
              :key="o.id"
              class="cursor-pointer rounded border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-[#d7effa]"
              :class="selectedObservationId === o.id ? 'border-[#04bcff]/60' : ''"
            >
              <input v-model="selectedObservationId" type="radio" :value="o.id" class="mr-2" />
              {{ o.text }}
            </label>
          </fieldset>
        </template>
      </main>

      <footer class="mt-4 flex items-center justify-between">
        <p class="min-h-5 flex-1 text-xs text-[#a9e8ff]/80">{{ message ?? ' ' }}</p>
        <button
          data-testid="sub-action-submit"
          class="rounded border border-[#04bcff]/50 bg-[#0a2c4e]/80 px-3 py-1.5 text-sm text-[#9ff] transition-colors hover:bg-[#123c63] disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="busy || !canSubmit"
          @click="onSubmit"
        >
          {{ busy ? '提交中…' : isEvidence ? '出示' : '提交质询' }}
        </button>
      </footer>
    </div>
  </div>
</template>
