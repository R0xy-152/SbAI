<!--
  Adapted from LingChat (AGPL-3.0): src/components/views/menu/base/StartPage.vue
  Modification（docs/15 §4）：边框内缩从 6vw 调为 4vw；窄屏居中 / 宽屏靠左。
-->
<template>
  <div
    class="absolute inset-0 z-[5] flex items-center border-[4vw] border-transparent will-change-transform [transform-style:preserve-3d]"
    :class="isNarrow ? 'justify-center' : 'justify-start'"
    v-bind="$attrs"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { useUIStore } from '../../adapters/lingchat-compat'

const uiStore = useUIStore()
const isNarrow = uiStore.isNarrowScreen
</script>
