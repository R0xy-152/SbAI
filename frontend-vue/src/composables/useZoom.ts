import { onMounted, onUnmounted, watch } from 'vue'
import { useSettingsStore } from '../stores/settings'

// Ctrl+滚轮 UI 缩放（docs/15 §5.2）：#app 应用 CSS zoom，范围 0.8~1.5，
// 步进 0.05；Ctrl+0 复位到 1。zoom 持久化到设置（uiZoom）。
// 光标特效 canvas teleport 到 body，避免 #app zoom 造成的坐标偏移
//（与 LingChat 同方案）。
const MIN_ZOOM = 0.8
const MAX_ZOOM = 1.5
const STEP = 0.05

export function useZoom(): void {
  const settings = useSettingsStore()

  const clamp = (value: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value))

  const apply = () => {
    const app = document.getElementById('app')
    if (app) {
      app.style.zoom = String(settings.uiZoom)
    }
  }

  const onWheel = (e: WheelEvent) => {
    if (!e.ctrlKey) return
    e.preventDefault()
    const delta = e.deltaY < 0 ? STEP : -STEP
    settings.uiZoom = clamp(Math.round((settings.uiZoom + delta) * 100) / 100)
  }

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.ctrlKey && e.key === '0') {
      e.preventDefault()
      settings.uiZoom = 1
    }
  }

  watch(() => settings.uiZoom, apply)

  onMounted(() => {
    apply()
    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('keydown', onKeyDown)
  })

  onUnmounted(() => {
    window.removeEventListener('wheel', onWheel)
    window.removeEventListener('keydown', onKeyDown)
  })
}
