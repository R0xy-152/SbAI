import { describe, expect, it } from 'vitest'
import { shouldIgnoreStoryAdvance } from '../story-input'

describe('shouldIgnoreStoryAdvance', () => {
  it('忽略按钮与可编辑表单控件', () => {
    const button = document.createElement('button')
    const input = document.createElement('input')
    const textarea = document.createElement('textarea')
    expect(shouldIgnoreStoryAdvance(button)).toBe(true)
    expect(shouldIgnoreStoryAdvance(input)).toBe(true)
    expect(shouldIgnoreStoryAdvance(textarea)).toBe(true)
  })

  it('允许普通画面和只读台词框触发推进', () => {
    const stage = document.createElement('div')
    const textarea = document.createElement('textarea')
    textarea.readOnly = true
    expect(shouldIgnoreStoryAdvance(stage)).toBe(false)
    expect(shouldIgnoreStoryAdvance(textarea)).toBe(false)
  })
})
