<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useSavesStore } from '../stores/saves'
import { useUiStore } from '../stores/ui'

// docs/13 §12 Title Screen：开始游戏 / 继续游戏 / 读取存档 / 设置。
// New Game 语义（§12.2）：显式新建会话，直接落 Opening；已有 localStorage
// session_id 时清掉再新建（不删除旧存档，docs/13 §14.1）。
// Continue（§12.3）：加载「该 player 最近更新的有效存档」；无存档时禁用。
// Task 6/7 落地后端 Save 前，Continue 数据源为 saves store（当前恒空）。
const router = useRouter()
const game = useGameStore()
const saves = useSavesStore()
const ui = useUiStore()

const BG = '/backgroud/background1.png'
const newGameBusy = ref(false)
const newGameError = ref<string | null>(null)

async function onNewGame() {
  if (newGameBusy.value) return
  newGameBusy.value = true
  newGameError.value = null
  try {
    // 显式新建会话：清掉旧 session 标识，交给 GameView 走 Opening（docs/13 §12.2）。
    localStorage.removeItem('gal_session_id')
    game.sessionId = null
    await router.push('/game')
  } catch (e) {
    newGameError.value = e instanceof Error ? e.message : String(e)
  } finally {
    newGameBusy.value = false
  }
}

function onContinue() {
  // 无存档时禁用（按钮 disabled，兜底提示，docs/13 §12.3：不得创建空 Session）。
  if (!saves.hasAnySave) return
  // 有存档：加载最近存档 → 进入对应会话（Task 6/7 接入后端后实现）。
  void router.push('/game')
}

async function refreshSaves() {
  try {
    await saves.refresh()
  } catch (e) {
    console.warn('[TitleView] refresh saves failed', e)
  }
}

onMounted(refreshSaves)
</script>

<template>
  <div class="relative flex h-full w-full flex-col items-center justify-center overflow-hidden bg-[#10131d] text-[#f4f8ff]">
    <!-- 背景（docs/13 §12.1：Background，与游戏内同一张） -->
    <img
      :src="BG"
      alt=""
      class="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-60"
    />
    <div class="pointer-events-none absolute inset-0 bg-[#070c18]/55"></div>

    <!-- 临时文字 Logo（docs/13 Task 5 第一轮：无需先生成最终 KV） -->
    <h1 class="relative z-10 mb-10 text-center text-4xl font-bold tracking-widest text-[#dff7ff] drop-shadow-lg">
      完蛋，我被AI娘包围了
    </h1>

    <!-- 主菜单（docs/13 §12.1：Menu） -->
    <nav class="relative z-10 flex flex-col items-center gap-3">
      <button class="title-btn" :disabled="newGameBusy" @click="onNewGame">开始游戏</button>
      <button
        class="title-btn"
        :disabled="!saves.hasAnySave || newGameBusy"
        :title="saves.hasAnySave ? '' : '暂无可继续的存档'"
        @click="onContinue"
      >
        继续游戏
      </button>
      <button class="title-btn" :disabled="newGameBusy" @click="router.push('/load')">读取存档</button>
      <button class="title-btn" :disabled="newGameBusy" @click="router.push('/settings')">设置</button>
    </nav>

    <p v-if="newGameError" class="relative z-10 mt-5 max-w-sm text-center text-sm text-red-300">{{ newGameError }}</p>
    <p v-else class="relative z-10 mt-5 text-xs text-[#a9e8ff]/70">
      {{ ui.backendOk === true ? '后端已连接' : ui.backendOk === false ? '后端未连接' : '连接后端中…' }}
    </p>
  </div>
</template>

<style scoped>
/* 按钮：与游戏内 UI 一致（GameDialog / 系统菜单同款深蓝边框 + 悬停高亮）。
   固定宽度避免 resize / 长文案换行导致溢出（docs/13 Task 5 验收：resize 不溢出）。 */
.title-btn {
  width: 13rem;
  max-width: 80vw;
  padding: 0.7rem 1rem;
  border: 1px solid rgba(211, 234, 255, 0.55);
  border-radius: 0.5rem;
  background: rgba(7, 12, 24, 0.85);
  color: #d7effa;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s ease;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.title-btn:hover:not(:disabled) {
  background: rgba(30, 48, 78, 0.9);
}
.title-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
