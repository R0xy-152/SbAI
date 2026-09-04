export type PhysicsQuality = 'high' | 'balanced' | 'low'

interface NavigatorHints extends Navigator {
  deviceMemory?: number
}

export function initialPhysicsQuality(): PhysicsQuality {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return 'balanced'
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return 'low'
  const nav = navigator as NavigatorHints
  const cores = nav.hardwareConcurrency ?? 4
  const memory = nav.deviceMemory ?? 4
  if (cores >= 8 && memory >= 8) return 'high'
  if (cores >= 4 && memory >= 4) return 'balanced'
  return 'low'
}

export class AdaptivePhysicsQuality {
  private samples: number[] = []
  private readonly reducedMotion: boolean
  quality: PhysicsQuality

  constructor(initial = initialPhysicsQuality()) {
    this.quality = initial
    this.reducedMotion =
      typeof window !== 'undefined' &&
      Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
  }

  recordFrame(frameMs: number): PhysicsQuality {
    if (!Number.isFinite(frameMs) || frameMs <= 0 || frameMs > 250) return this.quality
    this.samples.push(frameMs)
    if (this.samples.length < 90) return this.quality
    const ordered = [...this.samples].sort((a, b) => a - b)
    const p90 = ordered[Math.floor(ordered.length * 0.9)] ?? frameMs
    this.samples = []
    if (this.reducedMotion) {
      this.quality = 'low'
    } else if (p90 > 24) {
      this.quality = this.quality === 'high' ? 'balanced' : 'low'
    } else if (p90 < 12 && this.quality === 'low') {
      this.quality = 'balanced'
    }
    return this.quality
  }

  get substeps(): number {
    return this.quality === 'high' ? 4 : this.quality === 'balanced' ? 2 : 1
  }

  get targetFrameMs(): number {
    return this.quality === 'low' ? 1000 / 30 : 1000 / 60
  }
}
