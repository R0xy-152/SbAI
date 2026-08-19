<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useUiStore } from './stores/ui'
import { checkBackendHealth } from './api/game'

const ui = useUiStore()

onMounted(() => {
  void checkBackendHealth()
    .then((ok) => (ui.backendOk = ok))
    .catch(() => (ui.backendOk = false))
})
</script>

<template>
  <RouterView />
</template>
