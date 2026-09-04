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
  predictionHorizon: number
  predictionStrength: number
  braidStrength: number
  braidTargetSpeed: number
  braidRange: number
  centerStrength: number
  edgeStrength: number
  damping: number
  maxSpeed: number
  margin: number
}

export const DEFAULT_ORBIT_CONFIG: OrbitPhysicsConfig = {
  gravity: 440_000,
  softening: 48,
  repulsion: 2_600,
  avoidancePadding: 56,
  predictionHorizon: 0.8,
  predictionStrength: 520,
  braidStrength: 34,
  braidTargetSpeed: 82,
  braidRange: 390,
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

function stablePairSpin(firstId: string, secondId: string): -1 | 1 {
  const key = [firstId, secondId].sort().join('|')
  let hash = 2_166_136_261
  for (let index = 0; index < key.length; index += 1) {
    hash ^= key.charCodeAt(index)
    hash = Math.imul(hash, 16_777_619)
  }
  return (hash >>> 0) % 2 === 0 ? 1 : -1
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value))
}

export function createOrbitBodies(
  ids: string[],
  bounds: OrbitBounds,
  seed: number,
  radius = 64,
): OrbitBody[] {
  const random = seededRandom(seed)
  const centerX = bounds.width / 2
  const centerY = bounds.height / 2
  const baseRadius = Math.min(bounds.width, bounds.height) * 0.34
  const phase = random() * Math.PI * 2
  const direction = random() < 0.5 ? -1 : 1
  return ids.map((id, index) => {
    const angle = phase
      + (index / Math.max(1, ids.length)) * Math.PI * 2
      + (random() - 0.5) * 0.16
    const radial = baseRadius * (0.92 + random() * 0.16)
    const tangentialSpeed = 44 + random() * 34
    return {
      id,
      x: centerX + Math.cos(angle) * radial,
      y: centerY + Math.sin(angle) * radial * 0.7,
      vx: -Math.sin(angle) * tangentialSpeed * direction + (random() - 0.5) * 12,
      vy: Math.cos(angle) * tangentialSpeed * direction + (random() - 0.5) * 12,
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
        const tangentX = -normalY
        const tangentY = normalX
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

        const relativeVx = bodies[j].vx - bodies[i].vx
        const relativeVy = bodies[j].vy - bodies[i].vy
        const relativeTangentialSpeed = relativeVx * tangentX + relativeVy * tangentY
        const angularMomentum = dx * relativeVy - dy * relativeVx
        const spin = Math.abs(angularMomentum) > distance * 2
          ? angularMomentum < 0 ? -1 : 1
          : stablePairSpin(bodies[i].id, bodies[j].id)

        // A symmetric tangential steering force maintains pairwise angular
        // momentum in the middle distance. Near-contact motion is left to the
        // safety barrier, so paths braid without introducing a fixed hub.
        const braidStart = contactDistance + config.avoidancePadding * 0.75
        const braidBand = smoothstep(braidStart, braidStart + 72, distance)
          * (1 - smoothstep(config.braidRange * 0.76, config.braidRange, distance))
        const braidError = spin * config.braidTargetSpeed - relativeTangentialSpeed
        const braidSideForce = clamp(
          braidError * 0.22,
          -config.braidStrength,
          config.braidStrength,
        ) * braidBand
        forceX -= tangentX * braidSideForce
        forceY -= tangentY * braidSideForce

        // Look ahead for the closest approach and begin a continuous sidestep
        // before the visible text capsules touch. The equal/opposite pair force
        // preserves the equal-mass model and avoids a rigid collision response.
        const relativeSpeedSquared = relativeVx ** 2 + relativeVy ** 2
        const approachRate = -(dx * relativeVx + dy * relativeVy) / distance
        if (
          config.predictionHorizon > 0
          && config.predictionStrength > 0
          && relativeSpeedSquared > 0.001
          && approachRate > 0
          && distance > contactDistance
        ) {
          const closestTime = clamp(
            -(dx * relativeVx + dy * relativeVy) / relativeSpeedSquared,
            0,
            config.predictionHorizon,
          )
          const closestX = dx + relativeVx * closestTime
          const closestY = dy + relativeVy * closestTime
          const closestDistance = Math.hypot(closestX, closestY)
          const collisionRisk = 1 - smoothstep(contactDistance, avoidanceDistance, closestDistance)
          const urgency = 0.35 + 0.65 * (1 - closestTime / config.predictionHorizon)
          const approachWeight = smoothstep(4, 42, approachRate)
          const predictionSideForce = spin * config.predictionStrength
            * collisionRisk * urgency * approachWeight * 0.5
          forceX -= tangentX * predictionSideForce
          forceY -= tangentY * predictionSideForce
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
