<script setup lang="ts">
import { useRouter } from 'vue-router'

// 游戏内系统菜单（docs/13 §13）：保存 / 读取 / 历史 / 设置 / 返回标题。
// 菜单本身只发事件由 GameView 打开对应面板；「返回标题」直接导航回 Title
//（docs/13 §13.4：不删除 Session，不强制任意中间态 snapshot —— Auto Save
// 的合法 checkpoint 由 Task 8 接线）。
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
  <div
    class="fixed inset-0 z-30 flex items-center justify-center bg-black/60"
    @click.self="emit('close')"
  >
    <div class="flex w-[min(88vw,300px)] flex-col gap-2 rounded-xl border border-white/15 bg-[#0b1424]/95 p-4 text-[#f4f8ff] shadow-2xl">
      <h2 class="mb-1 text-center text-sm font-bold text-[#dff7ff]">系统菜单</h2>
      <button
        class="sys-menu-btn"
        @click="emit('open', 'save')"
      >
        保存
      </button>
      <button
        class="sys-menu-btn"
        @click="emit('open', 'load')"
      >
        读取
      </button>
      <button
        class="sys-menu-btn"
        @click="emit('open', 'history')"
      >
        历史
      </button>
      <button class="sys-menu-btn" @click="router.push('/settings')">设置</button>
      <button
        class="sys-menu-btn text-[#ff9d9d]"
        @click="returnTitle"
      >
        返回标题
      </button>
      <button class="sys-menu-btn mt-1" @click="emit('close')">关闭</button>
    </div>
  </div>
</template>

<style scoped>
.sys-menu-btn {
  width: 100%;
  padding: 0.65rem 1rem;
  border: 1px solid rgba(211, 234, 255, 0.3);
  border-radius: 0.5rem;
  background: rgba(7, 12, 24, 0.8);
  color: #d7effa;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.2s ease;
}
.sys-menu-btn:hover {
  background: rgba(30, 48, 78, 0.9);
}
</style>
