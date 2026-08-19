<template>
  <div class="relative h-full">
    <!-- 底层图片（当前显示；in-flow，撑开父容器宽度=立绘显示宽度） -->
    <img
      v-show="currentSrc"
      :src="currentSrc"
      class="relative block h-full w-auto object-contain"
    />
    <!-- 顶层图片（淡入的新图；absolute 覆盖，不参与宽度） -->
    <img
      ref="topImgRef"
      v-show="nextSrc"
      :src="nextSrc"
      class="absolute inset-0 h-full w-full object-contain transition-opacity ease-in-out"
      :class="isFadingIn ? 'opacity-100' : 'opacity-0'"
      :style="{ transitionDuration: duration + 'ms' }"
      @transitionend="onTransitionEnd"
    />
  </div>
</template>

<script setup lang="ts">
// docs/13 §9.1 自动站位：立绘用 <img>（有 natural 尺寸）撑开容器宽度，
// 容器 left:autoLeft% + translateX(-50%) 实现精准分位。img 双叠实现
// cross-fade，避免表情切换闪白（Task 2 验收「表情切换不闪白」）。
// 语义等价于 LingChat ImageAcrossFade 的 cross-fade，但角色图用 img 而非
// background，使容器宽度=立绘显示宽度（LingChat 背景 div 无法撑开布局宽）。
import { ref, watch, nextTick } from 'vue'

const props = withDefaults(
  defineProps<{
    src: string
    duration?: number
  }>(),
  { duration: 300 },
)

const topImgRef = ref<HTMLElement | null>(null)
const currentSrc = ref('')
const nextSrc = ref('')
const isFadingIn = ref(false)

let currentLoadPromise: Promise<void> | null = null

const updateImage = async (newUrl: string) => {
  if (!newUrl || newUrl === 'none') return
  let resolveLoad!: () => void
  const loadPromise = new Promise<void>((resolve) => {
    resolveLoad = resolve
  })
  currentLoadPromise = loadPromise

  const img = new Image()
  const imgReady = new Promise<void>((resolve, reject) => {
    img.onload = () => resolve()
    img.onerror = (err) => reject(err)
  })
  img.src = newUrl

  try {
    await imgReady
    await img.decode().catch(() => {})
  } catch (err) {
    console.error(`加载图片失败: ${newUrl}`, err)
    currentLoadPromise = null
    resolveLoad()
    return
  }

  if (currentLoadPromise === loadPromise) {
    if (isFadingIn.value) {
      currentSrc.value = nextSrc.value || currentSrc.value
      isFadingIn.value = false
    }
    nextSrc.value = newUrl
    await nextTick()
    if (topImgRef.value) void topImgRef.value.offsetHeight
    requestAnimationFrame(() => {
      isFadingIn.value = true
    })
  }
  resolveLoad()
}

const onTransitionEnd = () => {
  if (isFadingIn.value) {
    currentSrc.value = nextSrc.value
    isFadingIn.value = false
  }
}

const waitForLoad = () => currentLoadPromise || Promise.resolve()

defineExpose({ waitForLoad })

watch(
  () => props.src,
  (newUrl) => {
    updateImage(newUrl)
  },
  { immediate: true },
)
</script>
