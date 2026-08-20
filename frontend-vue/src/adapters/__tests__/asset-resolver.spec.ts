// docs/17 §6.3：差分立绘接线 —— emotion → {角色}_{emotion英文id}.png，
// 编程式 Image 探测（在途去重 + 永久缓存）+ 404/加载失败回落 main 单图。
import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveCharacterAsset } from '../asset-resolver'

/** 可编程 Image 桩：src 赋值后按 loadOk() 决定 onload / onerror */
function stubImage(loadOk: () => boolean): { constructed: () => number } {
  let count = 0
  class FakeImage {
    onload: (() => void) | null = null
    onerror: (() => void) | null = null
    set src(_v: string) {
      count++
      queueMicrotask(() => (loadOk() ? this.onload?.() : this.onerror?.()))
    }
  }
  vi.stubGlobal('Image', FakeImage)
  return { constructed: () => count }
}

describe('asset-resolver 差分立绘接线', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('差分存在 → /char/{角色}/pic/{角色}_{emotion}.png', async () => {
    stubImage(() => true)
    const url = await resolveCharacterAsset({ characterId: 'deepseek', emotion: 'surprised' })
    expect(url).toBe('/char/deepseek/pic/deepseek_surprised.png')
  })

  it('差分加载失败 → 回落 main 单图', async () => {
    stubImage(() => false)
    const url = await resolveCharacterAsset({ characterId: 'claude', emotion: 'sad' })
    expect(url).toBe('/char/claude/pic/claude_main.png')
  })

  it('neutral → main，且不发探测', async () => {
    const { constructed } = stubImage(() => true)
    const url = await resolveCharacterAsset({ characterId: 'deepseek', emotion: 'neutral' })
    expect(url).toBe('/char/deepseek/pic/deepseek_main.png')
    expect(constructed()).toBe(0)
  })

  it('并发调用共享同一探测（在途去重）', async () => {
    const { constructed } = stubImage(() => true)
    const [a, b] = await Promise.all([
      resolveCharacterAsset({ characterId: 'deepseek', emotion: 'happy' }),
      resolveCharacterAsset({ characterId: 'deepseek', emotion: 'happy' }),
    ])
    expect(a).toBe('/char/deepseek/pic/deepseek_happy.png')
    expect(b).toBe(a)
    expect(constructed()).toBe(1)
  })

  it('同一 (角色, 表情) 只探测一次（结果缓存）', async () => {
    const { constructed } = stubImage(() => true)
    await resolveCharacterAsset({ characterId: 'deepseek', emotion: 'embarrassed' })
    await resolveCharacterAsset({ characterId: 'deepseek', emotion: 'embarrassed' })
    expect(constructed()).toBe(1)
  })

  it('未登记角色 → legacy characterAssetUrl 回退，且不探测', async () => {
    const { constructed } = stubImage(() => true)
    const url = await resolveCharacterAsset({ characterId: 'unknown', emotion: 'happy' })
    expect(url).toBe('/frontend-deprecated/public/characters/unknown/happy.png')
    expect(constructed()).toBe(0)
  })
})
