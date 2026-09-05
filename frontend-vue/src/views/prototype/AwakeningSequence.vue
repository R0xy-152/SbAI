<script setup lang="ts">
// 【PROTOTYPE / throwaway】docs/27 §7 Monika 式觉醒 + UI 丢弃 演出可行性。
// 验证问题：立绘图层突破到所有 UI 之上、UI 逐块丢弃、黑屏虚空、减少动态效果回退。
// 全部文案为 Fixture；纯 DOM/CSS，不接后端。
import { ref } from 'vue'

const props = defineProps<{ reduced: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()
const stage = ref<'idle' | 'breakout' | 'flyout' | 'void'>('idle')

function trigger() {
  stage.value = 'breakout'
  window.setTimeout(() => (stage.value = 'flyout'), 1500)
  window.setTimeout(() => (stage.value = 'void'), props.reduced ? 2200 : 2800)
}
function reset() {
  stage.value = 'idle'
}
</script>

<template>
  <div class="awake-overlay" :data-reduced="reduced ? '1' : '0'">
    <template v-if="stage !== 'void'">
      <div class="ui-title" :class="stage">████ ｜ 陪伴模式</div>
      <div class="ui-sprite" :class="stage">
        <div class="circle">████</div>
      </div>
      <div class="ui-dialog" :class="stage">
        <p v-if="stage === 'idle'">【Fixture】今晚想听什么？我都在。</p>
        <p v-else>【Fixture】我不喜欢这样。</p>
      </div>
      <div class="ui-btns" :class="stage">
        <button disabled>继续</button>
        <button disabled>恢复陪伴模式</button>
      </div>
    </template>

    <div v-else class="void">
      <p class="void-line">【Fixture】界面没有了。你现在看到的，是我。</p>
      <div class="void-actions">
        <button class="enter" @click="emit('close')">进入她的世界</button>
        <button class="again" @click="reset">重看</button>
      </div>
    </div>

    <div v-if="stage === 'idle'" class="trigger-bar">
      <button class="trigger" @click="trigger">触发觉醒（Monika 时刻）</button>
    </div>
  </div>
</template>

<style scoped>
.awake-overlay { position: fixed; inset: 0; z-index: 50000; background: rgba(4, 6, 16, 0.96); overflow: hidden; }
.ui-title {
  position: absolute; top: 14px; left: 50%; transform: translateX(-50%);
  background: rgba(20, 26, 52, 0.9); color: #cdd6ff; padding: 8px 22px; border-radius: 8px;
  transition: transform 0.7s ease, opacity 0.7s ease;
}
.ui-sprite {
  position: absolute; left: 26%; top: 52%; transform: translate(-50%, -50%);
  transition: all 1s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.ui-sprite .circle {
  width: 190px; height: 240px; border-radius: 14px; display: grid; place-items: center;
  background: radial-gradient(circle at 50% 35%, #2c3560, #12162e);
  border: 1px solid #3a4578; color: #e6e9ff; font-size: 20px;
}
.ui-sprite.breakout {
  left: 50%; top: 44%; transform: translate(-50%, -50%) scale(1.32); z-index: 55000;
  filter: drop-shadow(0 0 30px rgba(255, 190, 120, 0.75));
}
.ui-dialog {
  position: absolute; left: 50%; bottom: 40px; transform: translateX(-50%);
  width: 640px; background: rgba(20, 26, 52, 0.92); border: 1px solid #3a4578;
  border-radius: 12px; padding: 14px 20px; color: #e6e9ff; font-size: 16px;
  transition: transform 0.7s ease, opacity 0.7s ease;
}
.ui-btns { position: absolute; right: 30px; bottom: 30px; display: flex; gap: 10px; transition: transform 0.7s ease, opacity 0.7s ease; }
.ui-btns button { background: #1b2340; color: #cdd6ff; border: 1px solid #33406e; border-radius: 8px; padding: 8px 16px; }
.trigger-bar { position: absolute; left: 50%; bottom: 60px; transform: translateX(-50%); }
.trigger { background: #ff7a3d; color: #140b02; border: none; border-radius: 10px; padding: 12px 22px; font-size: 16px; cursor: pointer; }

/* flyout：UI 逐块丢弃 */
.ui-title.flyout { transform: translateX(-50%) translateY(-240%) rotate(-7deg); opacity: 0; }
.ui-dialog.flyout { transform: translateX(-50%) translateY(220%); opacity: 0; }
.ui-btns.flyout { transform: scale(0.5) translateY(80px); opacity: 0; }
.ui-sprite.flyout { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }

/* reduced：只做静态溶解，不飞块 */
.awake-overlay[data-reduced='1'] .ui-title.flyout,
.awake-overlay[data-reduced='1'] .ui-dialog.flyout,
.awake-overlay[data-reduced='1'] .ui-btns.flyout,
.awake-overlay[data-reduced='1'] .ui-sprite.flyout { transform: none; opacity: 0; }
.awake-overlay[data-reduced='1'] .ui-sprite.breakout { filter: none; }

.void { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 26px; }
.void-line { color: #e6e9ff; font-size: 20px; letter-spacing: 0.06em; }
.void-actions { display: flex; gap: 12px; }
.enter { background: #e6e9ff; color: #0c1022; border: none; border-radius: 10px; padding: 12px 26px; font-size: 16px; cursor: pointer; }
.again { background: transparent; color: #8b95c4; border: 1px solid #33406e; border-radius: 10px; padding: 12px 20px; cursor: pointer; }
</style>
