<script setup lang="ts">
import { useRouter } from 'vue-router'

// 游戏内系统菜单（docs/13 §13）：保存 / 读取 / 历史 / 设置 / 返回标题。
// docs/15 §8：统一皮肤 —— .gal-modal-mask（背景模糊）+ .gal-panel + .gal-btn，
// 与 Title/Save/Load/Settings 共享同一套视觉语言（docs/13 §27.3）。
const emit = defineEmits<{
  open: ['save' | 'load' | 'history']
  close: []
}>()

const router = useRouter()

function returnTitle() {
  emit('close')
  router.push('/')
}
</script>

<template>
  <div class="gal-modal-mask" @click.self="emit('close')">
    <div class="gal-panel w-[min(88vw,320px)] gap-2 p-5">
      <h2 class="mb-1 text-center text-base font-bold tracking-[0.2em] text-[#dff7ff] drop-shadow">
        系统菜单
      </h2>
      <button class="gal-btn" @click="emit('open', 'save')">保存</button>
      <button class="gal-btn" @click="emit('open', 'load')">读取</button>
      <button class="gal-btn" @click="emit('open', 'history')">历史</button>
      <button class="gal-btn" @click="router.push('/settings')">设置</button>
      <button class="gal-btn gal-btn-danger" @click="returnTitle">返回标题</button>
      <button class="gal-btn mt-1" @click="emit('close')">关闭</button>
    </div>
  </div>
</template>
