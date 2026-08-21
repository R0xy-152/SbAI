/** 全局剧情推进不得抢占现有交互控件。只读台词框仍属于可点击推进区域。 */
export function shouldIgnoreStoryAdvance(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false
  const interactive = target.closest(
    'button, a, input, select, [role="button"], [contenteditable="true"], [data-no-story-advance]',
  )
  if (interactive) return true
  const textarea = target.closest('textarea')
  return textarea instanceof HTMLTextAreaElement && !textarea.readOnly
}
