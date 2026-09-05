<script setup lang="ts">
// 【PROTOTYPE / throwaway】验证「异常冻结帧喂四片玻璃」（docs/27 §7.1）。
// 阶段1：直播视频（TrialSceneSnapshot 周期性捕获帧到 mediaFrame）；
// 阶段2：触发异常 → ShatterPuzzle 挂载，四片应渲染同一张冻结帧（而非 4 个不同步视频）。
import { ref } from 'vue'
import TrialSceneSnapshot from '../../components/trial/TrialSceneSnapshot.vue'
import ShatterPuzzle from '../../components/trial/ShatterPuzzle.vue'
import type { TrialScene, TrialLine, TrialShardPose } from '../../api/trial'

const scene: TrialScene = {
  scene_id: 'TRIAL_OPENING',
  background: '/backgroud/background_ai.png',
  video: '/backgroud/kei_opening_720p.mp4',
  poster: '/backgroud/kei_opening_poster.png',
  music: '/backgroud/aira_full.m4a',
  fixture_art: true,
  characters: [{ character_id: 'origin_ai', display_name: '████', slot: 'CENTER' }],
}
const node: TrialLine = { kind: 'line', speaker_id: 'origin_ai', speaker_label: '████', text: '【Fixture】画面连接正在断裂…' }
const shardIds = ['SHARD_NW', 'SHARD_NE', 'SHARD_SE', 'SHARD_SW']
const phase = ref<'live' | 'shatter'>('live')
function triggerBreak() {
  phase.value = 'shatter'
}
function onComplete(poses: TrialShardPose[]) {
  console.log('shatter complete', poses.length)
}
</script>

<template>
  <div style="position: fixed; inset: 0; background: #02060c;">
    <TrialSceneSnapshot v-if="phase === 'live'" :scene="scene" :node="node" />
    <ShatterPuzzle v-else :scene="scene" :node="node" :shard-ids="shardIds" @complete="onComplete" />
    <button
      v-if="phase === 'live'"
      style="position: absolute; bottom: 16px; left: 16px; z-index: 60; padding: 10px 18px; border-radius: 10px; border: 1px solid #ffb978; background: #2a1c08; color: #ffd9a8; font-size: 15px; cursor: pointer;"
      @click="triggerBreak"
    >
      触发异常 → 碎裂
    </button>
    <div v-else style="position: absolute; bottom: 16px; left: 16px; z-index: 60; color: #9ec8ff; font-size: 13px; background: rgba(8,12,28,.8); padding: 8px 12px; border-radius: 8px;">
      碎裂中：四片应为同一张冻结帧
    </div>
  </div>
</template>
