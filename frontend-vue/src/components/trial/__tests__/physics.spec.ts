import { describe, expect, it } from 'vitest'
import { AdaptivePhysicsQuality } from '../performance'
import {
  createOrbitBodies,
  stepOrbitBodies,
  type OrbitPhysicsConfig,
} from '../physics'
import { allShardsSolved, stepShardBodies, type ShardBody } from '../shard-physics'

const isolatedConfig: OrbitPhysicsConfig = {
  gravity: 360_000,
  softening: 20,
  repulsion: 0,
  avoidancePadding: 0,
  centerStrength: 0,
  edgeStrength: 0,
  damping: 0,
  maxSpeed: 10_000,
  margin: 0,
}

describe('试玩版文字天体物理', () => {
  it('相同 seed 产生确定性且等质量代理半径一致的初态', () => {
    const first = createOrbitBodies(['a', 'b', 'c', 'd'], { width: 900, height: 600 }, 2049)
    const second = createOrbitBodies(['a', 'b', 'c', 'd'], { width: 900, height: 600 }, 2049)

    expect(first).toEqual(second)
    expect(new Set(first.map((body) => body.radius))).toEqual(new Set([54]))
  })

  it('两体只受相互引力时保持等大反向动量变化', () => {
    const stepped = stepOrbitBodies(
      [
        { id: 'left', x: 200, y: 200, vx: 0, vy: 0, radius: 20 },
        { id: 'right', x: 400, y: 200, vx: 0, vy: 0, radius: 20 },
      ],
      { width: 600, height: 400 },
      1 / 60,
      isolatedConfig,
      4,
    )

    expect(stepped[0].vx).toBeGreaterThan(0)
    expect(stepped[1].vx).toBeLessThan(0)
    expect(stepped[0].vx + stepped[1].vx).toBeCloseTo(0, 8)
    expect(stepped.every((body) => Number.isFinite(body.x) && Number.isFinite(body.y))).toBe(true)
  })

  it('默认五体系统长时间运行仍保持文字包围体的安全间距', () => {
    let bodies = createOrbitBodies(
      ['a', 'b', 'c', 'd', 'e'],
      { width: 960, height: 540 },
      31704,
    )
    let minimumDistance = Number.POSITIVE_INFINITY
    for (let frame = 0; frame < 60 * 90; frame += 1) {
      bodies = stepOrbitBodies(bodies, { width: 960, height: 540 }, 1 / 60, undefined, 4)
      for (let i = 0; i < bodies.length; i += 1) {
        for (let j = i + 1; j < bodies.length; j += 1) {
          minimumDistance = Math.min(
            minimumDistance,
            Math.hypot(bodies[i].x - bodies[j].x, bodies[i].y - bodies[j].y),
          )
        }
      }
    }

    expect(minimumDistance).toBeGreaterThanOrEqual(108)
    expect(bodies.every((body) => Number.isFinite(body.x) && Number.isFinite(body.y))).toBe(true)
  })

  it('连续慢帧会逐级降档，低档稳定快帧允许恢复到平衡档', () => {
    const quality = new AdaptivePhysicsQuality('high')
    for (let index = 0; index < 90; index += 1) quality.recordFrame(30)
    expect(quality.quality).toBe('balanced')
    for (let index = 0; index < 90; index += 1) quality.recordFrame(30)
    expect(quality.quality).toBe('low')
    for (let index = 0; index < 90; index += 1) quality.recordFrame(10)
    expect(quality.quality).toBe('balanced')
  })
})

describe('试玩版玻璃碎片归位物理', () => {
  it('进入吸附域的四块碎片由弹簧和阻尼平滑收敛并全部锁定', () => {
    let bodies: ShardBody[] = [55, -48, 39, -63].map((x, index) => ({
      id: `shard-${index}`,
      x,
      y: x * -0.45,
      rotation: index % 2 === 0 ? 5 : -6,
      vx: 0,
      vy: 0,
      angularVelocity: 0,
      mass: 0.25,
      inertia: 1,
      dragging: false,
      snapped: false,
    }))

    for (let index = 0; index < 600 && !allShardsSolved(bodies); index += 1) {
      bodies = stepShardBodies(bodies, 1 / 60, 'high')
    }

    expect(allShardsSolved(bodies)).toBe(true)
    expect(bodies.every((body) => body.x === 0 && body.y === 0 && body.rotation === 0)).toBe(true)
  })
})
