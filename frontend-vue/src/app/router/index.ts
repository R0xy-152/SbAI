import { createRouter, createWebHistory } from 'vue-router'
import TitleView from '../../views/TitleView.vue'
import ChapterSelectView from '../../views/ChapterSelectView.vue'
import GameView from '../../views/GameView.vue'
import StoryView from '../../views/StoryView.vue'
import LoadView from '../../views/LoadView.vue'
import SettingsView from '../../views/SettingsView.vue'
import LoginView from '../../views/LoginView.vue'
import TrialView from '../../views/TrialView.vue'
import WorldPrototypeView from '../../views/prototype/WorldPrototype.vue' // PROTOTYPE throwaway（docs/27 可行性探查）
import MediaSyncPrototypeView from '../../views/prototype/MediaSyncPrototype.vue' // PROTOTYPE throwaway（视频+音乐同步验证）
import ShatterFreezePrototypeView from '../../views/prototype/ShatterFreezePrototype.vue' // PROTOTYPE throwaway（冻结帧喂四片玻璃）
import { useAuthStore } from '../../stores/auth'

// docs/13 §6：Title / Game / Load / Settings 四个 View。
// Title 完成行为在 Task 5，存档页在 Task 7。
// docs/19：开始游戏先进入 /chapters；「序章」以 story_id=prologue 复用
// /story 播放器。未带 story_id 的 /story 继续恢复既有第一章故事存档。
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/', name: 'title', component: TitleView },
    { path: '/chapters', name: 'chapters', component: ChapterSelectView },
    { path: '/game', name: 'game', component: GameView },
    { path: '/story', name: 'story', component: StoryView },
    { path: '/trial', name: 'trial', component: TrialView },
    { path: '/prototype/world', name: 'prototype-world', component: WorldPrototypeView, meta: { public: true } }, // PROTOTYPE throwaway
    { path: '/prototype/media', name: 'prototype-media', component: MediaSyncPrototypeView, meta: { public: true } }, // PROTOTYPE throwaway
    { path: '/prototype/shatter', name: 'prototype-shatter', component: ShatterFreezePrototypeView, meta: { public: true } }, // PROTOTYPE throwaway
    { path: '/load', name: 'load', component: LoadView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

router.beforeEach(async (to) => {
  // 本地开发免登录（仅 Vite dev；线上构建 import.meta.env.DEV=false，登录逻辑不变）
  // 配合后端 GAL_AUTH_REQUIRED=false 使用
  if (import.meta.env.DEV) return true
  const auth = useAuthStore()
  await auth.restore()
  if (to.meta.public) {
    return to.name === 'login' && auth.authenticated ? { name: 'title' } : true
  }
  if (!auth.authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})
