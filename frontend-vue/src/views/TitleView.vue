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
import { saveTargetRoute } from '../api/saves'

// docs/15 §4：基于 LingChat MainMenu 视觉层与动画层重建 TitleView ——
// 全亮背景（无遮罩）+ 流星/星星粒子 + 角色立绘 + 鼠标视差 + 电影感菜单。
// docs/15 §4.4.1：New Game 打开章节选择；Continue 加载最近存档
//（无存档禁用）；Load/Settings 走路由。按钮保留 .title-btn（E2E 兼容）。
const router = useRouter()
const game = useGameStore()
const saves = useSavesStore()
const ui = useUiStore()
const settings = useSettingsStore()

const newGameBusy = ref(false)
const newGameError = ref<string | null>(null)
const continueBusy = ref(false)
const continueError = ref<string | null>(null)

async function onNewGame() {
  if (newGameBusy.value) return
  newGameBusy.value = true
  newGameError.value = null
  try {
    // docs/15 §4.4.1：开始游戏只打开章节选择；真正创建新会话由
    // 已解锁章节入口负责，避免玩家返回标题时意外丢失当前会话。
    await router.push('/chapters')
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
    // 按存档类型路由：故事未完结 → /story；已完结（结局后自由聊天）/
    // 旧玩法存档 → /game（docs/17 结局后自由聊天）。
    const result = await saves.load(saves.mostRecent.id)
    game.pendingLoad = result
    localStorage.removeItem('gal_session_id')
    await router.push(saveTargetRoute(result.story_cursor, result.story_finished))
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

// ── 视差层（docs/15 §4.2；v1.1 起无角色层，charRef 不传） ──
const bgRef = ref<HTMLElement | null>(null)
const starsLayerRef = ref<HTMLElement | null>(null)

const prefersReducedMotion =
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

const { handleMouseMove, handleMouseLeave } = useParallaxAnimation({
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
    <!-- 1. 背景层（docs/15 §4.1 + docs/16 P3：普通屏 3:2 近景，宽屏切
         21:9 扩展图；极端比例才用模糊层兜底） -->
    <div ref="bgRef" class="title-bg-layer">
      <div class="title-bg-fill"></div>
      <div class="title-bg-sharp"></div>
    </div>

    <!-- 2. 流星层 -->
    <MeteorAnimation :meteors-enabled="settings.mainMenuMeteorsEnabled" :meteor-fps="30" />

    <!-- 3. 星星层（容器承载视差位移） -->
    <div ref="starsLayerRef" class="pointer-events-none absolute inset-0 z-[2]">
      <StarAnimation :stars-enabled="settings.mainMenuStarsEnabled" :stars-fps="30" />
    </div>

    <!-- 4. 菜单层（mousemove/mouseleave 驱动视差）。
         docs/15 v1.1 修订：首页不放角色立绘 —— 背景图（background_title.png）
         本身已含人物，叠一层立绘会双人撞车。五层结构改为四层（背景/流星/
         星星/菜单），视差作用于背景与星星层。 -->
    <StartPage @mousemove="onMouseMove" @mouseleave="onMouseLeave">
      <div class="flex flex-col gap-4">
        <Transition name="slide-left" appear>
          <StartList>
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
  --title-background: url('/backgroud/background_title.png');
  position: absolute;
  top: 0;
  left: -12px;
  width: calc(100% + 24px);
  height: 100%;
  z-index: 0;
  will-change: transform;
  overflow: hidden;
}

/* docs/16 P3：模糊层只为极端比例与视差边缘兜底。 */
.title-bg-fill {
  position: absolute;
  inset: 0;
  background-image: var(--title-background);
  background-size: cover;
  background-position: center;
  filter: blur(24px) brightness(0.72) saturate(1.05);
  transform: scale(1.08);
}

/* 普通比例以 cover 铺满；3:2 图在 16:9 / 16:10 只裁上下背景。 */
.title-bg-sharp {
  position: absolute;
  inset: 0;
  background-image: var(--title-background);
  background-size: cover;
  background-position: center 48%;
  background-repeat: no-repeat;
}

/* 浏览器内容区接近 2:1 时使用真正的 21:9 扩展图，避免旧 3:2 图过度裁切。 */
@media (min-aspect-ratio: 19 / 10) {
  .title-bg-layer {
    --title-background: url('/backgroud/background_title_21x9.png');
  }
}

/* 32:9 等极端超宽屏不强行 cover 裁掉大量上下内容，允许两侧柔和延展。 */
@media (min-aspect-ratio: 49 / 20) {
  .title-bg-sharp {
    background-size: auto 100%;
  }
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
