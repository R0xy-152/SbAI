export interface OrbitBody {
  id: string
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  dragged?: boolean
}

export interface OrbitBounds {
  width: number
  height: number
}

export interface OrbitPhysicsConfig {
  gravity: number
  softening: number
  repulsion: number
  avoidancePadding: number
  centerStrength: number
  edgeStrength: number
  damping: number
  maxSpeed: number
  margin: number
}

export const DEFAULT_ORBIT_CONFIG: OrbitPhysicsConfig = {
  gravity: 360_000,
  softening: 42,
  repulsion: 2_200,
  avoidancePadding: 42,
  centerStrength: 0.012,
  edgeStrength: 4.8,
  damping: 0.045,
  maxSpeed: 115,
  margin: 62,
}

function smoothstep(edge0: number, edge1: number, value: number): number {
  if (edge0 === edge1) return value < edge0 ? 0 : 1
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)))
  return t * t * (3 - 2 * t)
}

function seededRandom(seed: number): () => number {
  let state = seed >>> 0 || 0x9e3779b9
  return () => {
    state += 0x6d2b79f5
    let value = state
    value = Math.imul(value ^ (value >>> 15), value | 1)
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61)
    return ((value ^ (value >>> 14)) >>> 0) / 4_294_967_296
  }
}

export function createOrbitBodies(
  ids: string[],
  bounds: OrbitBounds,
  seed: number,
  radius = 54,
): OrbitBody[] {
  const random = seededRandom(seed)
  const centerX = bounds.width / 2
  const centerY = bounds.height / 2
  const baseRadius = Math.min(bounds.width, bounds.height) * 0.28
  return ids.map((id, index) => {
    const angle = (index / Math.max(1, ids.length)) * Math.PI * 2 + random() * 0.7
    const radial = baseRadius * (0.72 + random() * 0.5)
    const tangentialSpeed = 42 + random() * 42
    const direction = index % 3 === 0 ? -1 : 1
    return {
      id,
      x: centerX + Math.cos(angle) * radial,
      y: centerY + Math.sin(angle) * radial * 0.7,
      vx: -Math.sin(angle) * tangentialSpeed * direction + (random() - 0.5) * 18,
      vy: Math.cos(angle) * tangentialSpeed * direction + (random() - 0.5) * 18,
      radius,
    }
  })
}

export function stepOrbitBodies(
  source: OrbitBody[],
  bounds: OrbitBounds,
  dtSeconds: number,
  config: OrbitPhysicsConfig = DEFAULT_ORBIT_CONFIG,
  substeps = 1,
): OrbitBody[] {
  const bodies = source.map((body) => ({ ...body }))
  const count = bodies.length
  const step = Math.min(1 / 30, Math.max(0, dtSeconds)) / Math.max(1, substeps)
  const centerX = bounds.width / 2
  const centerY = bounds.height / 2

  for (let substep = 0; substep < Math.max(1, substeps); substep += 1) {
    const acceleration = bodies.map(() => ({ x: 0, y: 0 }))
    for (let i = 0; i < count; i += 1) {
      for (let j = i + 1; j < count; j += 1) {
        const dx = bodies[j].x - bodies[i].x
        const dy = bodies[j].y - bodies[i].y
        const distanceSquared = dx * dx + dy * dy
        const distance = Math.sqrt(Math.max(distanceSquared, 0.0001))
        const normalX = distanceSquared < 0.0001 ? (i + j) % 2 === 0 ? 1 : -1 : dx / distance
        const normalY = distanceSquared < 0.0001 ? 0 : dy / distance
        const softened = Math.pow(distanceSquared + config.softening ** 2, 1.5)
        const attraction = config.gravity / softened
        let forceX = dx * attraction
        let forceY = dy * attraction

        const contactDistance = bodies[i].radius + bodies[j].radius
        const avoidanceDistance = contactDistance + config.avoidancePadding
        if (distance < avoidanceDistance) {
          // The force ramps up *before* the text bounds touch.  This is a
          // continuous barrier rather than a post-collision teleport/bounce.
          const weight = 1 - smoothstep(contactDistance, avoidanceDistance, distance)
          const repulsion = config.repulsion * weight
          forceX -= normalX * repulsion
          forceY -= normalY * repulsion
        }
        acceleration[i].x += forceX
        acceleration[i].y += forceY
        acceleration[j].x -= forceX
        acceleration[j].y -= forceY
      }
    }

    for (let i = 0; i < count; i += 1) {
      const body = bodies[i]
      if (body.dragged) continue
      acceleration[i].x += (centerX - body.x) * config.centerStrength
      acceleration[i].y += (centerY - body.y) * config.centerStrength

      const left = config.margin - body.x
      const right = body.x - (bounds.width - config.margin)
      const top = config.margin - body.y
      const bottom = body.y - (bounds.height - config.margin)
      if (left > 0) acceleration[i].x += left * config.edgeStrength
      if (right > 0) acceleration[i].x -= right * config.edgeStrength
      if (top > 0) acceleration[i].y += top * config.edgeStrength
      if (bottom > 0) acceleration[i].y -= bottom * config.edgeStrength

      const damping = Math.exp(-config.damping * step)
      body.vx = (body.vx + acceleration[i].x * step) * damping
      body.vy = (body.vy + acceleration[i].y * step) * damping
      const speed = Math.hypot(body.vx, body.vy)
      if (speed > config.maxSpeed) {
        const scale = config.maxSpeed / speed
        body.vx *= scale
        body.vy *= scale
      }
      body.x += body.vx * step
      body.y += body.vy * step
    }
  }
  return bodies
}
