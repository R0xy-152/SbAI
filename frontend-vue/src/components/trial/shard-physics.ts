import type { PhysicsQuality } from './performance'

export interface ShardBody {
  id: string
  x: number
  y: number
  rotation: number
  vx: number
  vy: number
  angularVelocity: number
  mass: number
  inertia: number
  dragging: boolean
  snapped: boolean
  /** 吸附半径（随拼图尺寸缩放）：碎片进入该距离后弹簧才会发力，保证小屏不会一出生就被吸回 */
  snapRadius: number
}

// 吸附半径取拼图短边的比例；散落距离取短边的更大比例，二者同源缩放，
// 确保任何视口下碎片初始都落在吸附域之外，必须由玩家拖近才归位。
const SNAP_RADIUS_FRACTION = 0.18

export function createShardBodies(ids: string[], width: number, height: number): ShardBody[] {
  const scale = Math.min(width, height)
  // 四片向四角散开（单位：短边比例），休息位置约 0.34×scale，明确大于 0.18×scale 的吸附半径
  const impulses = [
    [-0.26, -0.22, -12],
    [0.27, -0.2, 10],
    [0.25, 0.25, -9],
    [-0.24, 0.23, 11],
  ]
  const areaMass = 0.25
  return ids.map((id, index) => {
    const [nx, ny, rotation] = impulses[index] ?? [0, 0, 0]
    return {
      id,
      x: nx * scale,
      y: ny * scale,
      rotation,
      vx: nx * scale * 0.6,
      vy: ny * scale * 0.6,
      angularVelocity: rotation * 0.42,
      mass: areaMass,
      inertia: areaMass * (width * width + height * height) * 0.045,
      dragging: false,
      snapped: false,
      snapRadius: scale * SNAP_RADIUS_FRACTION,
    }
  })
}

export function stepShardBodies(
  source: ShardBody[],
  dtSeconds: number,
  quality: PhysicsQuality,
): ShardBody[] {
  const bodies = source.map((body) => ({ ...body }))
  const substeps = quality === 'high' ? 4 : quality === 'balanced' ? 2 : 1
  const dt = Math.min(dtSeconds, 1 / 30) / substeps
  for (let substep = 0; substep < substeps; substep += 1) {
    for (const body of bodies) {
      if (body.dragging || body.snapped) continue
      const distance = Math.hypot(body.x, body.y)
      const nearTarget = distance < body.snapRadius
      if (nearTarget) {
        const spring = quality === 'high' ? 24 : 19
        body.vx += (-body.x * spring * dt) / body.mass
        body.vy += (-body.y * spring * dt) / body.mass
        body.angularVelocity += -body.rotation * 14 * dt
      }
      const linearDamping = Math.exp(-(nearTarget ? 5.8 : 2.7) * dt)
      const angularDamping = Math.exp(-(nearTarget ? 7.2 : 3.2) * dt)
      body.vx *= linearDamping
      body.vy *= linearDamping
      body.angularVelocity *= angularDamping
      body.x += body.vx * dt
      body.y += body.vy * dt
      body.rotation += body.angularVelocity * dt
      if (
        distance < body.snapRadius * 0.015
        && Math.abs(body.rotation) < 0.8
        && Math.hypot(body.vx, body.vy) < 18
      ) {
        body.x = 0
        body.y = 0
        body.rotation = 0
        body.vx = 0
        body.vy = 0
        body.angularVelocity = 0
        body.snapped = true
      }
    }
  }
  return bodies
}

export function allShardsSolved(bodies: ShardBody[]): boolean {
  return bodies.length === 4 && bodies.every((body) => body.snapped)
}
