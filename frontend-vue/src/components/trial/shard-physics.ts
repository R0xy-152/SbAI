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
}

export function createShardBodies(ids: string[], width: number, height: number): ShardBody[] {
  const impulses = [
    [-0.16, -0.13, -12],
    [0.17, -0.11, 10],
    [0.15, 0.15, -9],
    [-0.14, 0.16, 11],
  ]
  const scale = Math.min(width, height)
  return ids.map((id, index) => {
    const [nx, ny, rotation] = impulses[index] ?? [0, 0, 0]
    const areaMass = 0.25
    return {
      id,
      x: nx * width,
      y: ny * height,
      rotation,
      vx: nx * scale * 0.72,
      vy: ny * scale * 0.72,
      angularVelocity: rotation * 0.42,
      mass: areaMass,
      inertia: areaMass * (width * width + height * height) * 0.045,
      dragging: false,
      snapped: false,
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
      const nearTarget = distance < 150
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
      if (distance < 2.2 && Math.abs(body.rotation) < 0.8 && Math.hypot(body.vx, body.vy) < 18) {
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
