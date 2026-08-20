import { createRouter, createWebHistory } from 'vue-router'
import TitleView from '../../views/TitleView.vue'
import GameView from '../../views/GameView.vue'
import StoryView from '../../views/StoryView.vue'
import LoadView from '../../views/LoadView.vue'
import SettingsView from '../../views/SettingsView.vue'

// docs/13 §6：Title / Game / Load / Settings 四个 View。
// Title 完成行为在 Task 5，存档页在 Task 7。
// 快速上线：/story 为现役入口（07 固定剧本，AI 停用）；/game 保留旧调查
// 玩法但不再有 UI 入口（用户确认「入口隐藏」），代码不动、可随时恢复。
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'title', component: TitleView },
    { path: '/game', name: 'game', component: GameView },
    { path: '/story', name: 'story', component: StoryView },
    { path: '/load', name: 'load', component: LoadView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})
