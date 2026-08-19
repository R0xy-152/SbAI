// docs/15 §5.3：设置持久化与特效开关默认值（gal_settings 向后兼容）。
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSettingsStore, DEFAULT_SETTINGS } from '../settings'

function setStored(raw: string | null) {
  if (raw === null) localStorage.removeItem('gal_settings')
  else localStorage.setItem('gal_settings', raw)
}

describe('settings store（docs/15 §5.3）', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('无持久化数据：全部取默认值（特效默认开启）', () => {
    const s = useSettingsStore()
    expect(s.textSpeed).toBe(DEFAULT_SETTINGS.textSpeed)
    expect(s.mainMenuStarsEnabled).toBe(true)
    expect(s.mainMenuMeteorsEnabled).toBe(true)
    expect(s.globalMouseTrailEnabled).toBe(true)
    expect(s.clickAnimationEnabled).toBe(true)
    expect(s.sceneEffectsEnabled).toBe(true)
    expect(s.loadingTransitionEnabled).toBe(true)
    expect(s.uiZoom).toBe(1)
  })

  it('旧版数据（只有三个字段）：新字段回落到默认值', () => {
    setStored(JSON.stringify({ textSpeed: 1.5, bgmVolume: 0.3, sfxVolume: 0.4 }))
    const s = useSettingsStore()
    expect(s.textSpeed).toBe(1.5)
    expect(s.bgmVolume).toBe(0.3)
    expect(s.mainMenuStarsEnabled).toBe(true)
    expect(s.sceneEffectsEnabled).toBe(true)
  })

  it('修改特效开关会持久化到 localStorage', async () => {
    const s = useSettingsStore()
    s.mainMenuStarsEnabled = false
    s.uiZoom = 1.2
    await new Promise((r) => setTimeout(r, 10))
    const saved = JSON.parse(localStorage.getItem('gal_settings')!)
    expect(saved.mainMenuStarsEnabled).toBe(false)
    expect(saved.uiZoom).toBe(1.2)
    expect(saved.textSpeed).toBe(1)
  })

  it('损坏的 JSON：回落默认值且不抛错', () => {
    setStored('{not-json')
    const s = useSettingsStore()
    expect(s.textSpeed).toBe(1)
    expect(s.mainMenuStarsEnabled).toBe(true)
  })
})
