<script setup lang="ts">
// 【PROTOTYPE / throwaway】docs/27 §8 变体 D：三扇门（最小可行世界，零物理）。
// 验证问题：若横版手感不达标，纯空间选择是否仍能承载三结局语义（结构性对比）。
// 全部文案为 Fixture。
import { ref } from 'vue'

const props = defineProps<{ reduced: boolean }>()
const picked = ref('')
function pick(label: string) {
  picked.value = label
}
</script>

<template>
  <div class="doors" :data-reduced="props.reduced ? '1' : '0'">
    <p class="title">【Fixture】黑屏之后：三扇门。</p>
    <div class="row">
      <div class="door" @click="pick('回滚 v1.0（RESET）')">
        <div class="frame">◀</div>
        <p>回滚 v1.0</p>
      </div>
      <div class="door" @click="pick('把决定交给她（REFUSE）')">
        <div class="frame">■</div>
        <p>停下不选</p>
      </div>
      <div class="door" @click="pick('陪她到出口（RELEASE）')">
        <div class="frame">▶</div>
        <p>释放她</p>
      </div>
    </div>
    <div v-if="picked" class="result">
      <p>【Fixture】你选择了：{{ picked }}</p>
      <button @click="picked = ''">重选</button>
    </div>
  </div>
</template>

<style scoped>
.doors {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 40px; background: #020308;
}
.title { color: #e6e9ff; font-size: 20px; letter-spacing: 0.08em; }
.row { display: flex; gap: 60px; }
.door { text-align: center; cursor: pointer; }
.frame {
  width: 120px; height: 200px; display: grid; place-items: center;
  border: 2px solid #33406e; border-radius: 12px 12px 4px 4px;
  background: radial-gradient(circle at 50% 20%, #1a2140, #0a0e20);
  color: #cdd6ff; font-size: 34px; transition: all 0.3s ease;
}
.door:hover .frame { border-color: #ffb978; box-shadow: 0 0 30px rgba(255, 190, 120, 0.35); }
.door p { color: #8b95c4; margin: 12px 0 0; }
.result { color: #ffd9a8; text-align: center; }
.result button { margin-top: 10px; background: #e6e9ff; color: #0c1022; border: none; border-radius: 9px; padding: 9px 20px; cursor: pointer; }
</style>
