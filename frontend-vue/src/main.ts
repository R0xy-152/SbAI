import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './app/router'
import './style.css'
import { useAuthStore } from './stores/auth'
import { setUnauthorizedHandler } from './api/http'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
setUnauthorizedHandler(() => {
  useAuthStore(pinia).clear()
  if (router.currentRoute.value.name !== 'login') {
    void router.replace({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  }
})
app.mount('#app')
