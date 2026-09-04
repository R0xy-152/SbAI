<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  TRIAL_ID,
  fetchTrialCurrent,
  newTrialCommandId,
  sendTrialCommand,
  type TrialEvidence,
  type TrialInteraction,
  type TrialShardPose,
  type TrialView,
} from '../api/trial'
import { useGameStore } from '../stores/game'
import EvidenceOrbit from '../components/trial/EvidenceOrbit.vue'
import ReasoningTray from '../components/trial/ReasoningTray.vue'
import ServiceStoppedModal from '../components/trial/ServiceStoppedModal.vue'
import ShatterPuzzle from '../components/trial/ShatterPuzzle.vue'
import TrialSceneSnapshot from '../components/trial/TrialSceneSnapshot.vue'

interface ReasoningTrayHandle {
  containsPoint(clientX: number, clientY: number): boolean
}

const router = useRouter()
const game = useGameStore()
const trial = ref<TrialView | null>(null)
const sessionId = ref<string | null>(null)
const busy = ref(false)
const error = ref<string | null>(null)
const playerInput = ref('')
const selectedIds = ref<string[]>([])
const inspectedEvidence = ref<TrialEvidence | null>(null)
const reasoningTray = ref<ReasoningTrayHandle | null>(null)

const interaction = computed<TrialInteraction | null>(() => trial.value?.interaction ?? null)
const isOrbit = computed(() => interaction.value?.kind === 'evidence_orbit')
const phaseLabel = computed(() => {
  const labels: Record<string, string> = {
    not_started: '准备进入',
    opening_warm_chat: '深夜对话',
    opening_input: '你的回应',
    opening_anomaly: '异常信号',
    opening_shatter: '重组连接',
    opening_origin_ai_remains: '残存意识',
    opening_service_stopped: '服务停止',
    fragment_01_deepseek_intro: '单人审问',
    fragment_01_first_reasoning: '失忆推理',
    fragment_01_group_intro: '全员集合',
    fragment_01_group_reasoning: '最终推理',
    fragment_02_handoff_a: '线路 A',
    fragment_02_handoff_b: '线路 B',
  }
  return labels[trial.value?.phase_id ?? ''] ?? '试玩进行中'
})
const selectedEvidence = computed(() => {
  const evidence = trial.value?.authorized_evidence ?? []
  return selectedIds.value
    .map((id) => evidence.find((item) => item.evidence_id === id))
    .filter((item): item is TrialEvidence => Boolean(item))
})
const currentSelectionMax = computed(() =>
  interaction.value?.kind === 'evidence_orbit' ? interaction.value.selection_max : 0,
)
const resultText = computed(() => {
  if (!trial.value) return null
  if (trial.value.outcome === 'NO_MATCH' && isOrbit.value) {
    return '这次推理尚未成立。证据没有被消耗，可以调整后再次提交。'
  }
  if (trial.value.finished) {
    const correctness = trial.value.reasoning_outcome === 'ACCEPTED' ? '推理成立' : '推理未成立'
    const route = trial.value.route_id === 'fragment_02_b' ? '线路 B' : '线路 A'
    return `${correctness}；已确定进入${route}。`
  }
  return null
})

function rememberView(next: TrialView) {
  trial.value = next
  sessionId.value = next.session_id
  game.sessionId = next.session_id
  localStorage.setItem('gal_session_id', next.session_id)
}

async function loadCurrent() {
  busy.value = true
  error.value = null
  const pending = game.pendingLoad
  if (pending?.experience_id === TRIAL_ID) {
    sessionId.value = pending.session_id
    game.pendingLoad = null
  } else if (pending) {
    game.pendingLoad = null
  } else {
    sessionId.value = game.sessionId
  }
  try {
    rememberView(await fetchTrialCurrent(sessionId.value))
  } catch (firstError) {
    if (sessionId.value) {
      sessionId.value = null
      game.sessionId = null
      localStorage.removeItem('gal_session_id')
      try {
        rememberView(await fetchTrialCurrent(null))
        return
      } catch {
        // Surface the original error when both attempts fail.
      }
    }
    error.value = firstError instanceof Error ? firstError.message : String(firstError)
  } finally {
    busy.value = false
  }
}

async function send(command: Parameters<typeof sendTrialCommand>[1]) {
  if (busy.value) return
  busy.value = true
  error.value = null
  try {
    rememberView(await sendTrialCommand(sessionId.value, command))
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    busy.value = false
  }
}

async function advance() {
  selectedIds.value = []
  inspectedEvidence.value = null
  await send({ type: 'ADVANCE', command_id: newTrialCommandId() })
}

async function submitPlayerInput() {
  const message = playerInput.value.trim()
  if (!message) return
  playerInput.value = ''
  await send({ type: 'PLAYER_INPUT', command_id: newTrialCommandId(), message })
}

async function completeShatter(poses: TrialShardPose[]) {
  await send({
    type: 'COMPLETE_SHATTER',
    command_id: newTrialCommandId(),
    shards: poses,
  })
}

function inspectEvidence(evidenceId: string) {
  inspectedEvidence.value =
    trial.value?.authorized_evidence.find((item) => item.evidence_id === evidenceId) ?? null
}

function addEvidence(evidenceId: string) {
  if (selectedIds.value.includes(evidenceId)) return
  if (selectedIds.value.length >= currentSelectionMax.value) {
    error.value = `本轮最多选择 ${currentSelectionMax.value} 条证据。`
    return
  }
  selectedIds.value = [...selectedIds.value, evidenceId]
  inspectedEvidence.value = null
  error.value = null
}

function removeEvidence(evidenceId: string) {
  selectedIds.value = selectedIds.value.filter((id) => id !== evidenceId)
}

function handleEvidenceDrop(payload: { evidenceId: string; clientX: number; clientY: number }) {
  if (reasoningTray.value?.containsPoint(payload.clientX, payload.clientY)) {
    addEvidence(payload.evidenceId)
  }
}

async function submitReasoning(message: string) {
  const current = interaction.value
  if (current?.kind !== 'evidence_orbit') return
  const beforeDeduction = current.deduction_id
  await send({
    type: 'SUBMIT_REASONING',
    command_id: newTrialCommandId(),
    deduction_id: beforeDeduction,
    evidence_ids: [...selectedIds.value],
    message,
  })
  const after = interaction.value
  if (after?.kind !== 'evidence_orbit' || after.deduction_id !== beforeDeduction) {
    selectedIds.value = []
  }
}

watch(
  () => (interaction.value?.kind === 'evidence_orbit' ? interaction.value.deduction_id : null),
  () => {
    selectedIds.value = []
    inspectedEvidence.value = null
  },
)

onMounted(loadCurrent)
</script>

<template>
  <main class="trial-view">
    <template v-if="trial">
      <TrialSceneSnapshot
        v-if="interaction?.kind !== 'shatter_puzzle'"
        :scene="trial.scene"
        :node="trial.node"
      />

      <header class="trial-toolbar">
        <button type="button" @click="router.push('/chapters')">← 章节选择</button>
        <div>
          <span>试玩版</span>
          <small>{{ phaseLabel }}</small>
        </div>
        <div class="trial-fixture-badge">玩法原型</div>
      </header>

      <ShatterPuzzle
        v-if="interaction?.kind === 'shatter_puzzle'"
        :scene="trial.scene"
        :node="trial.node"
        :shard-ids="interaction.shard_ids"
        @complete="completeShatter"
      />

      <section v-if="isOrbit && interaction?.kind === 'evidence_orbit'" class="reasoning-workspace">
        <EvidenceOrbit
          :evidence="trial.authorized_evidence"
          :selected-ids="selectedIds"
          :seed="interaction.deduction_id === 'TRIAL_DEDUCTION_GROUP_TRUTH' ? 2049 : 31704"
          @inspect="inspectEvidence"
          @drop="handleEvidenceDrop"
        />
        <ReasoningTray
          ref="reasoningTray"
          :selected="selectedEvidence"
          :selection-min="interaction.selection_min"
          :selection-max="interaction.selection_max"
          :busy="busy"
          @remove="removeEvidence"
          @submit="submitReasoning"
        />
      </section>

      <form
        v-if="interaction?.kind === 'text_input'"
        class="trial-input"
        @submit.prevent="submitPlayerInput"
      >
        <label for="trial-player-input">回应</label>
        <textarea
          id="trial-player-input"
          v-model="playerInput"
          rows="3"
          maxlength="2000"
          autofocus
          placeholder="输入你的话……"
        ></textarea>
        <button type="submit" :disabled="busy || !playerInput.trim()">
          {{ busy ? '发送中…' : interaction.label }}
        </button>
      </form>

      <button
        v-if="interaction?.kind === 'advance'"
        class="trial-advance"
        type="button"
        :disabled="busy"
        @click="advance"
      >
        {{ busy ? '处理中…' : interaction.label }} <span aria-hidden="true">›</span>
      </button>

      <ServiceStoppedModal
        v-if="interaction?.kind === 'service_stop_modal'"
        :message="interaction.message"
        :busy="busy"
        @continue="advance"
      />

      <section v-if="interaction?.kind === 'complete'" class="trial-complete">
        <small>FRAGMENT 01 COMMITTED</small>
        <h1>片段 1 完成</h1>
        <p>{{ resultText }}</p>
        <p>片段 2 内容尚未定义，当前停在权威线路交接点。</p>
        <button type="button" @click="router.push('/chapters')">返回章节选择</button>
      </section>

      <div v-if="trial.story_tokens.includes('RING') && interaction?.kind === 'service_stop_modal'" class="ring-token">
        <span aria-hidden="true">◌</span> 已获得：戒指
      </div>

      <div v-if="resultText && !trial.finished" class="trial-result" role="status">{{ resultText }}</div>

      <div v-if="inspectedEvidence" class="evidence-detail" role="dialog" aria-modal="true">
        <section>
          <small>EVIDENCE</small>
          <h2>{{ inspectedEvidence.title }}</h2>
          <p>{{ inspectedEvidence.summary }}</p>
          <div>
            <button type="button" @click="inspectedEvidence = null">关闭</button>
            <button type="button" @click="addEvidence(inspectedEvidence.evidence_id)">加入推理槽</button>
          </div>
        </section>
      </div>
    </template>

    <div v-else class="trial-loading">正在建立试玩会话…</div>
    <div v-if="error" class="trial-error" role="alert">{{ error }}</div>
  </main>
</template>

<style scoped>
.trial-view {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 34rem;
  overflow: hidden;
  color: #ecfaff;
  background: #02060c;
  isolation: isolate;
}

.trial-toolbar {
  position: absolute;
  top: 1rem;
  right: 1rem;
  left: 1rem;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
}
.trial-toolbar button,
.trial-toolbar > div {
  pointer-events: auto;
}
.trial-toolbar button {
  border: 1px solid rgba(131, 224, 251, 0.32);
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  color: #dff8ff;
  background: rgba(2, 12, 20, 0.76);
  cursor: pointer;
  backdrop-filter: blur(10px);
}
.trial-toolbar > div:nth-child(2) {
  display: grid;
  justify-items: center;
  color: #a2e9ff;
  font-weight: 800;
  letter-spacing: 0.16em;
}
.trial-toolbar small { color: #6b9aa8; font: 0.58rem/1.4 monospace; letter-spacing: 0.03em; }
.trial-fixture-badge {
  border: 1px solid rgba(255, 198, 94, 0.38);
  border-radius: 999px;
  padding: 0.4rem 0.65rem;
  color: #ffd58c;
  background: rgba(34, 22, 4, 0.76);
  font: 0.62rem/1 monospace;
}

.trial-advance {
  position: absolute;
  right: clamp(1.6rem, 8vw, 8rem);
  bottom: clamp(1.25rem, 5vh, 3.8rem);
  z-index: 8;
  border: 1px solid rgba(146, 233, 255, 0.5);
  border-radius: 999px;
  padding: 0.7rem 1.2rem;
  color: #e7fbff;
  background: rgba(5, 25, 36, 0.84);
  box-shadow: 0 0 24px rgba(70, 199, 237, 0.18);
  font-weight: 750;
  cursor: pointer;
}
.trial-advance span { margin-left: 0.7rem; color: #7bdaf5; font-size: 1.3rem; }

.trial-input {
  position: absolute;
  right: clamp(1rem, 7vw, 7rem);
  bottom: clamp(1rem, 4vh, 3rem);
  left: clamp(1rem, 7vw, 7rem);
  z-index: 10;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.7rem;
  padding: 1rem;
  border: 1px solid rgba(137, 225, 255, 0.44);
  border-radius: 0.75rem;
  background: rgba(2, 11, 19, 0.92);
  backdrop-filter: blur(14px);
}
.trial-input label { grid-column: 1 / -1; color: #8ddff7; font-weight: 750; }
.trial-input textarea {
  resize: none;
  border: 1px solid rgba(134, 220, 245, 0.26);
  border-radius: 0.55rem;
  padding: 0.7rem;
  color: white;
  background: rgba(1, 6, 10, 0.74);
  font: inherit;
  outline: none;
}
.trial-input button,
.trial-complete button,
.evidence-detail button {
  border: 1px solid rgba(142, 229, 255, 0.52);
  border-radius: 0.55rem;
  padding: 0.65rem 1rem;
  color: #e7faff;
  background: rgba(18, 88, 111, 0.62);
  font-weight: 750;
  cursor: pointer;
}
.trial-input button:disabled { cursor: not-allowed; opacity: 0.42; }

.reasoning-workspace {
  position: absolute;
  inset: 4.8rem 1rem 1rem;
  z-index: 12;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 25vw);
  gap: 0.85rem;
  padding: 0.8rem;
  border-radius: 1.25rem;
  background: rgba(0, 5, 10, 0.52);
  backdrop-filter: blur(7px);
}

.service-stop + .ring-token,
.ring-token {
  position: absolute;
  top: 5rem;
  left: 50%;
  z-index: 35;
  transform: translateX(-50%);
  border: 1px solid rgba(255, 224, 168, 0.5);
  border-radius: 999px;
  padding: 0.55rem 1rem;
  color: #ffe4aa;
  background: rgba(34, 18, 5, 0.9);
  box-shadow: 0 0 24px rgba(255, 182, 72, 0.2);
}

.trial-result,
.trial-error {
  position: absolute;
  z-index: 50;
  bottom: 1rem;
  left: 50%;
  width: min(40rem, calc(100% - 2rem));
  transform: translateX(-50%);
  border-radius: 0.55rem;
  padding: 0.7rem 1rem;
  text-align: center;
  backdrop-filter: blur(12px);
}
.trial-result { border: 1px solid rgba(247, 200, 103, 0.4); color: #ffe2a4; background: rgba(38, 25, 4, 0.86); }
.trial-error { border: 1px solid rgba(255, 95, 119, 0.54); color: #ffdce2; background: rgba(43, 3, 11, 0.92); }

.trial-complete {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: grid;
  place-content: center;
  justify-items: center;
  padding: 2rem;
  color: #eafaff;
  background: rgba(1, 8, 13, 0.82);
  text-align: center;
  backdrop-filter: blur(12px);
}
.trial-complete small { color: #70c8df; letter-spacing: 0.22em; }
.trial-complete h1 { margin: 0.8rem 0; font-size: clamp(2.5rem, 7vw, 5.5rem); }
.trial-complete p { max-width: 42rem; color: #bddbe4; }
.trial-complete button { margin-top: 1rem; }

.evidence-detail {
  position: absolute;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  background: rgba(0, 4, 8, 0.72);
  backdrop-filter: blur(12px);
}
.evidence-detail section {
  width: min(32rem, calc(100% - 2rem));
  padding: 1.5rem;
  border: 1px solid rgba(137, 227, 253, 0.42);
  border-radius: 1rem;
  background: linear-gradient(145deg, rgba(4, 18, 28, 0.98), rgba(7, 31, 43, 0.96));
  box-shadow: 0 2rem 5rem rgba(0, 0, 0, 0.52);
}
.evidence-detail small { color: #63b9d0; letter-spacing: 0.18em; }
.evidence-detail h2 { color: #a4ecff; font-size: 2rem; }
.evidence-detail p { color: #cce4eb; line-height: 1.7; }
.evidence-detail section > div { display: flex; justify-content: flex-end; gap: 0.6rem; }

.trial-loading {
  display: grid;
  height: 100%;
  place-items: center;
  color: #85d9ef;
  background: #02070d;
}

@media (max-width: 760px) {
  .reasoning-workspace {
    inset: 4.5rem 0.5rem 0.5rem;
    grid-template-columns: 1fr;
    grid-template-rows: minmax(18rem, 1fr) auto;
    overflow: auto;
  }
  .trial-fixture-badge { display: none; }
  .trial-input { grid-template-columns: 1fr; }
  .trial-input label { grid-column: 1; }
}
</style>
