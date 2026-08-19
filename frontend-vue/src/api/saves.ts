// Save API（docs/13 §20）。Task 6 后端 Save Snapshot、Task 7 存档 UI 时接入。
// 此处仅定义未来契约类型，避免 Task 1 提前实现后端未提供的能力。

export type SaveSlotType = 'AUTO' | 'MANUAL'

export interface GameSaveInfo {
  id: string
  player_id: string
  slot_type: SaveSlotType
  /** AUTO 为 null，MANUAL 为 1..6。 */
  slot_index: number | null
  title: string
  source_session_id: string
  chapter_id: string
  phase: string
  created_at: string
  updated_at: string
}

export interface SaveListResponse {
  auto: GameSaveInfo | null
  manual: Array<GameSaveInfo | null>
}
