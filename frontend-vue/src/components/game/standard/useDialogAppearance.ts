import { ref, computed } from 'vue'
import { useSettingsStore } from '../../../adapters/lingchat-compat'

export interface UseDialogAppearanceOptions {
  openHistory: () => void
}

export function useDialogAppearance(_options: UseDialogAppearanceOptions) {
  const settingsStore = useSettingsStore()

  const dialogBgImage = computed(() => settingsStore.dialogBackgroundImage)
  const dialogOpacity = computed(() => settingsStore.dialogOpacity)
  const dialogBlur = computed(() => settingsStore.dialogBlur)
  const dialogGradientColor = computed(() => settingsStore.dialogGradientColor)
  const dialogTextColorValue = computed(() => settingsStore.dialogTextColor)

  const isHidden = ref(false)

  function hide() {
    isHidden.value = true
  }

  const dialogWrapperStyle = computed(() => {
    const hasImage = Boolean(dialogBgImage.value)
    const style: Record<string, string> = {
      color: dialogTextColorValue.value,
    }
    if (hasImage) {
      style.backgroundImage = `url(${dialogBgImage.value})`
      style.backgroundSize = 'cover'
      style.backgroundPosition = 'center'
      style.backdropFilter = `blur(${dialogBlur.value}px)`
      style.backgroundColor = 'rgba(0,0,0,0.2)'
    } else {
      style.background = `linear-gradient(to top, ${hexToRgba(dialogGradientColor.value, dialogOpacity.value)}, ${hexToRgba(dialogGradientColor.value, Math.max(0, dialogOpacity.value - 0.1))})`
      style.backdropFilter = 'none'
    }
    return style
  })

  function handleWheelHistory(e: WheelEvent) {
    // 当前无历史面板，保留结构
    void e
    void _options
  }

  return {
    isHidden,
    hide,
    dialogWrapperStyle,
    dialogTextColorValue,
    handleWheelHistory,
  }
}

// 与 LingChat utils/color.hexToRgba 等价的本地实现
function hexToRgba(hex: string, alpha: number): string {
  let h = hex.replace('#', '')
  if (h.length === 3) {
    h = h
      .split('')
      .map((c) => c + c)
      .join('')
  }
  const r = parseInt(h.slice(0, 2), 16) || 0
  const g = parseInt(h.slice(2, 4), 16) || 0
  const b = parseInt(h.slice(4, 6), 16) || 0
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
