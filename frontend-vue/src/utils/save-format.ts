import type { GameSaveInfo } from '../api/saves'

// 存档 slot 元数据的展示格式化（docs/13 §12.4：标题 / 章节·阶段 / 保存时间）。
// 只消费 list 下发的 slot 元数据，不接触 snapshot（docs/13 §29）。

const PHASE_NAMES: Record<string, string> = {
  opening: '序章',
  investigation: '调查',
  recovery_required: '恢复',
  bad_end: 'BE',
  intro: '开场',
  visit_choice: '探班选择',
  branch: '角色探班',
  reunion: '三人集合',
  aftertalk: '后日谈',
  chat_choice: '交流选择',
  finished: '自由交流',
}

export function phaseName(phase: string | null | undefined): string {
  if (!phase) return ''
  return PHASE_NAMES[phase] ?? phase
}

/** 章节 / 阶段 展示行，如「第一章 · 调查」。 */
export function chapterPhaseLabel(save: GameSaveInfo): string {
  const chapter =
    save.chapter_id === 'ch1'
      ? '第一章'
      : save.chapter_id === 'prologue'
        ? '序章'
        : save.chapter_id ?? ''
  const phase = phaseName(save.phase)
  return [chapter, phase].filter(Boolean).join(' · ')
}

/** ISO 时间 → 本地可读字符串（YYYY-MM-DD HH:MM）。 */
export function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** slot 展示标题：手动存档优先用户标题，否则「存档位 N」；自动存档「自动存档」。 */
export function slotTitle(save: GameSaveInfo | null, index?: number): string {
  if (!save) return index != null ? `存档位 ${index}` : '自动存档'
  return save.title || (index != null ? `存档位 ${index}` : '自动存档')
}
