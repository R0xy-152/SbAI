<template>
  <div class="relative h-full">
    <!-- 单图节点：新差分预加载完成后原子替换 src。 -->
    <img
      v-show="currentSrc"
      :src="currentSrc"
      class="relative block h-full w-auto object-contain"
    />
  </div>
</template>

<script setup lang="ts">
// docs/13 §9.1 自动站位：立绘用 <img>（有 natural 尺寸）撑开容器宽度，
// 容器 left:autoLeft% + translateX(-50%) 实现精准分位。差分先预加载再
// 替换单一 img 的 src，避免交叉淡化期间两张立绘同时出现。
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    src: string
    duration?: number
  }>(),
  { duration: 300 },
)

const currentSrc = ref('')

let currentLoadPromise: Promise<void> | null = null
let updateId = 0

const updateImage = async (newUrl: string) => {
  if (!newUrl || newUrl === 'none') return
  if (newUrl === currentSrc.value) return
  const id = ++updateId
  const loadPromise = (async () => {
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
      return
    }

    if (id === updateId) currentSrc.value = newUrl
  })()
  currentLoadPromise = loadPromise
  await loadPromise
  if (currentLoadPromise === loadPromise) currentLoadPromise = null
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
