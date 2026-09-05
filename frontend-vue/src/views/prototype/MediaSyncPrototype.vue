<script setup lang="ts">
// 【PROTOTYPE / throwaway】验证 TrialSceneSnapshot 的开场视频+音乐同步起播（docs/27 §7.1/§7.2）。
import TrialSceneSnapshot from '../../components/trial/TrialSceneSnapshot.vue'
import type { TrialScene } from '../../api/trial'

const scene: TrialScene = {
  scene_id: 'TRIAL_OPENING',
  background: '/backgroud/background_ai.png',
  video: '/backgroud/kei_opening_720p.mp4',
  poster: '/backgroud/kei_opening_poster.png',
  music: '/backgroud/aira_full.m4a',
  fixture_art: true,
  characters: [{ character_id: 'origin_ai', display_name: '████', slot: 'CENTER' }],
}
</script>

<template>
  <div style="position: fixed; inset: 0; background: #02060c;">
    <TrialSceneSnapshot :scene="scene" />
  </div>
</template>
