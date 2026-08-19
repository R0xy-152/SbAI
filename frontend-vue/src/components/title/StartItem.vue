<!--
  Adapted from LingChat (AGPL-3.0): src/components/views/menu/base/StartItem.vue
  Modification（docs/15 §4.4）：视觉样式收敛到全局 .title-btn / .title-btn--ultra
  （style.css），组件只负责语义与超宽字号切换；保留 class="title-btn" 以兼容
  E2E/视觉基线选择器。
-->
<template>
  <button class="title-btn" :class="{ 'title-btn--ultra': isUltraWide.value }" v-bind="$attrs">
    <slot />
  </button>
</template>

<script setup lang="ts">
import { inject } from 'vue'

const isUltraWide = inject<{ value: boolean }>('isUltraWide', { value: false })
</script>
