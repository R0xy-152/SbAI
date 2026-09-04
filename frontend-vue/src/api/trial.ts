import { http } from './http'

export const TRIAL_ID = 'trial_v1' as const

export interface TrialLine {
  kind: 'line'
  speaker_id: string
  speaker_label: string
  text: string
}

export interface TrialCharacter {
  character_id: string
  display_name: string
  slot: 'LEFT' | 'CENTER_LEFT' | 'CENTER' | 'CENTER_RIGHT' | 'RIGHT'
}

export interface TrialScene {
  scene_id: string
  background: string
  fixture_art: boolean
  characters: TrialCharacter[]
}

export interface TrialEvidence {
  evidence_id: string
  title: string
  summary: string
}

export type TrialInteraction =
  | { kind: 'advance'; label: string }
  | { kind: 'text_input'; label: string }
  | { kind: 'shatter_puzzle'; puzzle_id: string; shard_ids: string[] }
  | { kind: 'service_stop_modal'; message: string; label: string }
  | {
      kind: 'evidence_orbit'
      deduction_id: string
      selection_min: number
      selection_max: number
      allow_retry: boolean
    }
  | { kind: 'complete'; label: string }

export interface TrialView {
  session_id: string
  experience_id: typeof TRIAL_ID
  started: boolean
  finished: boolean
  phase_id: string
  node: TrialLine | null
  scene: TrialScene
  interaction: TrialInteraction
  authorized_evidence: TrialEvidence[]
  story_tokens: string[]
  outcome: 'ACCEPTED' | 'NO_MATCH' | null
  reasoning_outcome: 'ACCEPTED' | 'NO_MATCH' | null
  route_id: 'fragment_02_a' | 'fragment_02_b' | null
  fixture_content: boolean
}

export interface TrialShardPose {
  shard_id: string
  x: number
  y: number
  rotation: number
}

export type TrialCommand =
  | { type: 'ADVANCE'; command_id: string }
  | { type: 'PLAYER_INPUT'; command_id: string; message: string }
  | { type: 'COMPLETE_SHATTER'; command_id: string; shards: TrialShardPose[] }
  | {
      type: 'SUBMIT_REASONING'
      command_id: string
      deduction_id: string
      evidence_ids: string[]
      message: string
    }

export function newTrialCommandId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `trial-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export async function fetchTrialCurrent(sessionId: string | null): Promise<TrialView> {
  const { data } = await http.get<TrialView>('/trial/current', {
    params: sessionId ? { session_id: sessionId } : undefined,
  })
  return data
}

export async function sendTrialCommand(
  sessionId: string | null,
  command: TrialCommand,
): Promise<TrialView> {
  const { data } = await http.post<TrialView>('/trial/command', {
    session_id: sessionId,
    command,
  })
  return data
}
