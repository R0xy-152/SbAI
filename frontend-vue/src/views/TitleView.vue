<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { useSavesStore } from '../stores/saves'
import { useUiStore } from '../stores/ui'
import { useSettingsStore } from '../stores/settings'
import { StartPage, StartLogo, StartItem, StartLine, StartList } from '../components/title'
import MeteorAnimation from '../components/effects/MeteorAnimation.vue'
import StarAnimation from '../components/effects/StarAnimation.vue'
import { useParallaxAnimation } from '../composables/useParallaxAnimation'

// docs/15 §4：基于 LingChat MainMenu 视觉层与动画层重建 TitleView ——
// 全亮背景（无遮罩）+ 流星/星星粒子 + 角色立绘 + 鼠标视差 + 电影感菜单。
// 行为语义保持不变（docs/13 §12）：New Game 新建会话；Continue 加载最近存档
//（无存档禁用）；Load/Settings 走路由。按钮保留 .title-btn（E2E 兼容）。
const router = useRouter()
const game = useGameStore()
const saves = useSavesStore()
const ui = useUiStore()
const settings = useSettingsStore()

const DEEPSEEK_CHAR = '/char/deepseek/pic/deepseek_main.png'

const newGameBusy = ref(false)
const newGameError = ref<string | null>(null)
const continueBusy = ref(false)
const continueError = ref<string | null>(null)

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

async function onContinue() {
  // 无存档时禁用（按钮 disabled，兜底提示，docs/13 §12.3：不得创建空 Session）。
  if (!saves.hasAnySave || !saves.mostRecent || continueBusy.value) return
  continueBusy.value = true
  continueError.value = null
  try {
    // Load 创建新 Active Session（docs/13 §19.1）；结果由 GameView 消费。
    const result = await saves.load(saves.mostRecent.id)
    game.pendingLoad = result
    localStorage.removeItem('gal_session_id')
    await router.push('/game')
  } catch (e) {
    continueError.value = e instanceof Error ? e.message : String(e)
  } finally {
    continueBusy.value = false
  }
}

async function refreshSaves() {
  try {
    await saves.refresh()
  } catch (e) {
    console.warn('[TitleView] refresh saves failed', e)
  }
}

onMounted(refreshSaves)

// ── 视差层（docs/15 §4.2） ──
const bgRef = ref<HTMLElement | null>(null)
const charRef = ref<HTMLElement | null>(null)
const starsLayerRef = ref<HTMLElement | null>(null)

const prefersReducedMotion =
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

const { handleMouseMove, handleMouseLeave } = useParallaxAnimation({
  charRef,
  bgRef,
  starsLayerRef,
})

const onMouseMove = (e: MouseEvent) => {
  if (!prefersReducedMotion) handleMouseMove(e)
}

const onMouseLeave = () => {
  if (!prefersReducedMotion) handleMouseLeave()
}

const backendLabel = computed(() =>
  ui.backendOk === true ? '后端已连接' : ui.backendOk === false ? '后端未连接' : '连接后端中…',
)
</script>

<template>
  <div class="relative h-full w-full overflow-hidden bg-[#04070f] text-[#f4f8ff]">
    <!-- 1. 背景层（docs/15 §4.1：全亮无遮罩，120% 宽给视差留余量） -->
    <div ref="bgRef" class="title-bg-layer"></div>

    <!-- 2. 流星层 -->
    <MeteorAnimation :meteors-enabled="settings.mainMenuMeteorsEnabled" :meteor-fps="30" />

    <!-- 3. 星星层（容器承载视差位移） -->
    <div ref="starsLayerRef" class="pointer-events-none absolute inset-0 z-[2]">
      <StarAnimation :stars-enabled="settings.mainMenuStarsEnabled" :stars-fps="30" />
    </div>

    <!-- 4. 角色立绘层（本项目自有素材，docs/15 §2）。src 用绑定避免 Vite 把
         公共路径当静态资源导入（vitest 下会解析失败）。 -->
    <img
      ref="charRef"
      class="title-character"
      :src="DEEPSEEK_CHAR"
      alt="DeepSeek"
    />

    <!-- 5. 菜单层（mousemove/mouseleave 驱动视差） -->
    <StartPage @mousemove="onMouseMove" @mouseleave="onMouseLeave">
      <div class="flex flex-col gap-4">
        <Transition name="slide-left" appear>
          <StartList responsive>
            <StartLine>
              <StartItem :disabled="newGameBusy" @click="onNewGame">{{ newGameBusy ? '创建中…' : '开始游戏' }}</StartItem>
            </StartLine>
            <StartLine>
              <StartItem
                :disabled="!saves.hasAnySave || newGameBusy || continueBusy"
                :title="saves.hasAnySave ? '' : '暂无可继续的存档'"
                @click="onContinue"
              >
                {{ continueBusy ? '读取中…' : '继续游戏' }}
              </StartItem>
            </StartLine>
            <StartLine>
              <StartItem :disabled="newGameBusy" @click="router.push('/load')">读取存档</StartItem>
            </StartLine>
            <StartLine>
              <StartItem :disabled="newGameBusy" @click="router.push('/settings')">设置</StartItem>
            </StartLine>
          </StartList>
        </Transition>

        <p v-if="newGameError" class="max-w-sm text-sm text-red-300 drop-shadow">{{ newGameError }}</p>
        <p v-else-if="continueError" class="max-w-sm text-sm text-red-300 drop-shadow">{{ continueError }}</p>
      </div>

      <StartLogo />

      <!-- 后端连接状态（底部小字 + 呼吸灯点，docs/15 §4.4） -->
      <p class="absolute bottom-[3.2vw] right-[4vw] z-10 flex items-center gap-2 text-xs tracking-wider text-[#a9e8ff]/75 drop-shadow">
        <span
          class="inline-block h-1.5 w-1.5 rounded-full"
          :class="
            ui.backendOk === true
              ? 'bg-emerald-300 shadow-[0_0_6px_rgba(110,231,183,0.9)]'
              : ui.backendOk === false
                ? 'bg-red-300 shadow-[0_0_6px_rgba(248,113,113,0.9)]'
                : 'animate-pulse bg-amber-200 shadow-[0_0_6px_rgba(252,211,77,0.9)]'
          "
        ></span>
        {{ backendLabel }}
      </p>
    </StartPage>
  </div>
</template>

<style scoped>
.title-bg-layer {
  position: absolute;
  top: 0;
  left: -10%;
  width: 120%;
  height: 100%;
  background-image: url('/backgroud/background_title.png');
  background-size: cover;
  background-position: center;
  z-index: 0;
  will-change: transform;
}

.title-character {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 100%;
  max-height: 100%;
  z-index: 3;
  pointer-events: none;
  will-change: transform;
}

/* 菜单入场（docs/15 §4.4） */
.slide-left-enter-active {
  transition: all 0.4s cubic-bezier(0.7, 0, 0.2, 1);
}

.slide-left-enter-from {
  transform: translateX(-120%);
  opacity: 0;
}
</style>
