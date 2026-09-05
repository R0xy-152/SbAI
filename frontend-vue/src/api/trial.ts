import { http } from './http'

export const TRIAL_ID = 'trial_v2' as const

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
  video?: string
  poster?: string
  music?: string
  fixture_art: boolean
  characters: TrialCharacter[]
}

export interface TrialEvidence {
  evidence_id: string
  title: string
  summary: string
}

export interface TrialChoiceOption {
  option_id: string
  label: string
}

export interface TrialMemoryItem {
  title: string
  edited_title: string
  summary: string
}

export type TrialInteraction =
  | { kind: 'advance'; label: string }
  | { kind: 'text_input'; label: string }
  | { kind: 'shatter_puzzle'; puzzle_id: string; shard_ids: string[] }
  | { kind: 'paper_rubbing'; label: string; answer: string }
  | { kind: 'service_stop_modal'; message: string; label: string }
  | {
      kind: 'evidence_orbit'
      deduction_id: string
      selection_min: number
      selection_max: number
      allow_retry: boolean
      seed: number
    }
  | {
      kind: 'permission_request'
      permission_id: string
      permission_name: string
      description: string
      grant_label: string
      deny_label: string
    }
  | {
      kind: 'memory_tamper'
      label: string
      items: TrialMemoryItem[]
      diff: { original: string; edited: string; editor: string; timestamp: string }
    }
  | {
      kind: 'judgment'
      judgment_id: string
      label: string
      prompt: string
      placeholder: string
    }
  | {
      kind: 'choice'
      choice_id: string
      prompt: string
      options: TrialChoiceOption[]
    }
  | { kind: 'world_runner'; world_id: string; label: string; terrain_text: string[] }
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
  ending: 'reset' | 'release' | 'refuse' | null
  reply_delay_ms: number
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
  | { type: 'PERMISSION_RESPONSE'; command_id: string; permission_id: string; grant: boolean }
  | { type: 'CHOOSE'; command_id: string; option_id: string }
  | { type: 'SUBMIT_JUDGMENT'; command_id: string; judgment_id: string; message: string }

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
