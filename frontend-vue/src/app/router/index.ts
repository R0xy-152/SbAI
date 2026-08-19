import { createRouter, createWebHistory } from 'vue-router'
import TitleView from '../../views/TitleView.vue'
import GameView from '../../views/GameView.vue'
import LoadView from '../../views/LoadView.vue'
import SettingsView from '../../views/SettingsView.vue'

// docs/13 §6：Title / Game / Load / Settings 四个 View。
// Title 完成行为在 Task 5，存档页在 Task 7。
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'title', component: TitleView },
    { path: '/game', name: 'game', component: GameView },
    { path: '/load', name: 'load', component: LoadView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})
