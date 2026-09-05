<script setup lang="ts">
// 【PROTOTYPE / throwaway】docs/27「她的世界」可行性探查宿主页。
// 三变体经 ?variant=A|C|D 切换（底部切换条 + ←/→）；?reduced=1 验证减少动态效果档。
// 不接后端状态；全部文案为 Fixture。上线前整目录删除。
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import VariantA from './VariantA.vue'
import VariantC from './VariantC.vue'
import VariantD from './VariantD.vue'
import AwakeningSequence from './AwakeningSequence.vue'

const route = useRoute()
const router = useRouter()
const VARIANTS = ['A', 'C', 'D'] as const
const NAMES: Record<string, string> = { A: '浮岛横版', C: '记忆长廊', D: '三扇门' }
const variant = computed(() => {
  const v = String(route.query.variant ?? 'A')
  return (VARIANTS as readonly string[]).includes(v) ? v : 'A'
})
const reduced = computed(() => route.query.reduced === '1')
const awakeningOpen = ref(false)

function cycle(d: number) {
  const i = VARIANTS.indexOf(variant.value as (typeof VARIANTS)[number])
  const next = VARIANTS[(i + d + VARIANTS.length) % VARIANTS.length]
  router.replace({ query: { ...route.query, variant: next } })
}
function toggleReduced() {
  router.replace({ query: { ...route.query, reduced: reduced.value ? undefined : '1' } })
}
function onKey(e: KeyboardEvent) {
  const t = e.target as HTMLElement | null
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
  if (e.key === 'ArrowLeft') cycle(-1)
  if (e.key === 'ArrowRight') cycle(1)
}
window.addEventListener('keydown', onKey)
</script>

<template>
  <div class="proto-host">
    <VariantA v-if="variant === 'A'" :reduced="reduced" />
    <VariantC v-else-if="variant === 'C'" :reduced="reduced" />
    <VariantD v-else :reduced="reduced" />
    <AwakeningSequence v-if="awakeningOpen" :reduced="reduced" @close="awakeningOpen = false" />
    <div class="proto-bar">
      <button @click="cycle(-1)">◀</button>
      <span class="label">变体 {{ variant }}（{{ NAMES[variant] }}）｜←/→ 切换｜A/D 移动 空格跳</span>
      <button @click="cycle(1)">▶</button>
      <button class="pill" @click="awakeningOpen = true">觉醒演出</button>
      <button class="pill" @click="toggleReduced">{{ reduced ? 'reduced:开' : 'reduced:关' }}</button>
    </div>
  </div>
</template>

<style scoped>
.proto-host { position: fixed; inset: 0; background: #05070f; overflow: hidden; }
.proto-bar {
  position: fixed; left: 50%; bottom: 14px; transform: translateX(-50%);
  display: flex; gap: 10px; align-items: center; z-index: 60000;
  background: rgba(10, 14, 30, 0.92); border: 1px solid rgba(140, 160, 255, 0.35);
  border-radius: 999px; padding: 8px 14px; color: #cdd6ff; font-size: 13px;
}
.proto-bar button { background: #1b2340; color: #cdd6ff; border: 1px solid #33406e; border-radius: 8px; padding: 4px 10px; cursor: pointer; }
.proto-bar .label { min-width: 260px; text-align: center; }
.proto-bar .pill { border-color: rgba(255, 190, 120, 0.5); }
</style>
