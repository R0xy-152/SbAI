<template>
  <Transition name="character-fade">
    <div
      class="absolute h-full pointer-events-none origin-[center_0%] role-container-transition"
      :style="containerStyle"
      @animationend="handleAnimationEnd"
    >
      <!-- 角色立绘（img 双叠 cross-fade；docs/13 §9.1：img 撑开容器宽，
           left:autoLeft% + translateX(-50%) 实现自动站位） -->
      <RoleSprite
        ref="imageFadeRef"
        class="h-full"
        :class="containerClasses"
        :src="targetAvatarUrl"
        :duration="300"
      />
    </div>
  </Transition>
</template>

<script setup lang="ts">
// Adapted from LingChat (AGPL-3.0): src/components/game/standard/GameRoleAvatar.vue
// Modification: replaced useGameStore/useUIStore with 本项目 Mock 兼容层；
// removed invoke/convertFileSrc (资源走 asset-resolver)；removed TouchAreas；
// bubble/audio 无素材，保留结构但移除播放逻辑；立绘改用 RoleSprite（img 撑宽
// 实现真正的自动站位分位，LingChat 的 background-contain 在满宽容器内会重叠）。
import { ref, computed, watch, nextTick, toRefs } from 'vue'
import { getAvatarFile, useGameStore, useUIStore, EMOTION_CONFIG, EMOTION_CONFIG_EMO } from '../../../adapters/lingchat-compat'
import RoleSprite from './RoleSprite.vue'
import './avatar-animation.css'

interface MockRole {
  roleId: string
  emotion: string
  scale: number
  offsetY: number
  offsetX: number
  /** 显式 slot：百分比站位，覆盖自动排位（T2review P1-13）。 */
  slot?: string | null
  /** 后端下发的 named animation（shake / fade_in / fade_out，P1-11）。 */
  animation?: string | null
  show: boolean
  character_folder: string
  clothesName: string
  bubbleTop: number
  bubbleLeft: number
}

const props = defineProps<{
  role: MockRole
}>()

const gameStore = useGameStore()
const uiStore = useUIStore()
const { role } = toRefs(props)

const imageFadeRef = ref<InstanceType<typeof RoleSprite> | null>(null)

const activeAnimationClass = ref('normal')

let latestEmotionId = 0

// --- 窄屏/宽屏补偿（docs/13 §11.2 保留） ---

// 窄屏适配：宽高比 1.0→0.5 区间，高度 100%→80%（rate=40）
const computedObjectFit = computed(() => {
  const ratio = uiStore.aspectRatio
  if (ratio >= 1.0) return 'contain'
  const percent = Math.max(80, 100 - (1.0 - ratio) * 40)
  return `auto ${Math.round(percent)}%`
})

// 窄屏 Y 轴补偿：同步上述区间，0%→20% 视口高度上移（rate=40）
const narrowScreenYCompensation = computed(() => {
  const ratio = uiStore.aspectRatio
  if (ratio >= 1.0) return 0
  const percent = Math.min(20, (1.0 - ratio) * 40)
  return Math.round((uiStore.viewportHeight * percent) / 100)
})

const wideScreenYCompensation = computed(() => {
  const ratio = uiStore.aspectRatio
  if (ratio < 2.0) return 0
  const percent = Math.min(10, (ratio - 2.0) * 20)
  return Math.round((uiStore.viewportHeight * percent) / 100)
})

// --- 样式计算 ---
const layoutPosition = computed(() => {
  const allIds = gameStore.presentRoleIds
  const myIndex = allIds.indexOf(role.value.roleId)
  const totalCount = allIds.length
  if (myIndex === -1) return 50
  return ((myIndex + 1) / (totalCount + 1)) * 100
})

// T2review P1-13：slot 是百分比站位——显式 slot 覆盖自动排位；offsetX 只
// 承载手动偏移（同样按百分比语义），不再把百分比当 px 叠加。
const SLOT_LEFT: Record<string, number> = {
  LEFT: 25,
  CENTER_LEFT: 40,
  CENTER: 50,
  CENTER_RIGHT: 60,
  RIGHT: 75,
}

const containerStyle = computed(() => {
  const autoLeft = layoutPosition.value
  const explicitSlot = role.value.slot
  const leftValue =
    explicitSlot && SLOT_LEFT[explicitSlot] != null
      ? `${SLOT_LEFT[explicitSlot]}%`
      : `calc(${autoLeft}% + ${role.value.offsetX || 0}%)`
  const objectFit = computedObjectFit.value
  const widthClause = typeof objectFit === 'string' && objectFit.startsWith('auto')
    ? 'auto'
    : 'auto'

  return {
    left: leftValue,
    top: `${role.value.offsetY - narrowScreenYCompensation.value - wideScreenYCompensation.value}px`,
    transform: `translateX(-50%) scale(${role.value.scale})`,
    opacity: `${role.value.show ? 1 : 0}`,
    zIndex: '1',
    width: widthClause,
  }
})

const containerClasses = computed(() => ({
  [activeAnimationClass.value]: true,
}))

const targetAvatarUrl = ref('')

let resolveAvatarId = 0

async function resolveAvatar() {
  const r = role.value
  const clothesName = r.clothesName === '默认' || !r.clothesName ? 'default' : r.clothesName
  const emotion = r.emotion
  const mappedEmotion = EMOTION_CONFIG_EMO[emotion] || 'neutral'

  const currentId = ++resolveAvatarId
  try {
    const url = await getAvatarFile(r.character_folder, mappedEmotion, clothesName)
    if (currentId === resolveAvatarId) {
      targetAvatarUrl.value = url
    }
  } catch {
    if (currentId === resolveAvatarId) {
      targetAvatarUrl.value = ''
    }
  }
}

watch(
  () => [role.value.roleId, role.value.emotion, role.value.clothesName, role.value.character_folder],
  () => resolveAvatar(),
  { immediate: true },
)

// 监听表情，配合子组件的加载状态播放特效
watch(
  () => role.value.emotion,
  async (newEmotion) => {
    const currentId = ++latestEmotionId

    // 1. 等待异步头像路径解析完成
    await resolveAvatar()

    // 2. 等待 Vue 更新 DOM 并传递给子组件
    await nextTick()

    // 3. 等待子组件的图片加载 Promise 结束
    if (imageFadeRef.value) {
      await imageFadeRef.value.waitForLoad()
    }

    // 检查是否仍然是最新的表情更新
    if (currentId !== latestEmotionId) return

    const config = EMOTION_CONFIG[newEmotion]
    if (!config) return

    if (config.animation && config.animation !== 'none') {
      activeAnimationClass.value = config.animation
    }
  },
  { immediate: true },
)

const handleAnimationEnd = () => {
  if (activeAnimationClass.value !== 'normal') {
    activeAnimationClass.value = 'normal'
  }
}

// T2review P1-11：消费后端下发的 named animation（shake / fade_in / fade_out）。
const ANIMATION_CLASS: Record<string, string> = {
  shake: 'shake',
  fade_in: 'fade-in',
  fade_out: 'fade-out',
}

watch(
  () => role.value.animation,
  (animation) => {
    if (!animation || animation === 'none') return
    const cls = ANIMATION_CLASS[animation]
    if (cls) activeAnimationClass.value = cls
  },
)
</script>

<style scoped>
.role-container-transition {
  transition:
    left 0.5s cubic-bezier(0.25, 0.8, 0.5, 1),
    top 0.3s ease,
    opacity 0.3s ease-in-out;
}

/* --- 角色进场/退场动画 (Vue Transition 组件必需的样式) --- */
.character-fade-enter-active,
.character-fade-leave-active {
  transition:
    opacity 0.5s ease-in-out,
    transform 0.5s ease-out;
}

.character-fade-enter-from,
.character-fade-leave-to {
  opacity: 0;
}
</style>
