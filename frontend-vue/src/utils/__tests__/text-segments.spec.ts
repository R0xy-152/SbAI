// docs/16 P6：台词分段 —— 按换行切段、trim、过滤空行。
import { describe, it, expect } from 'vitest'
import { splitTextSegments } from '../text-segments'

const NL = String.fromCharCode(10)

describe('splitTextSegments（docs/16 P6）', () => {
  it('按换行切成非空段', () => {
    expect(splitTextSegments('……你醒了' + NL + '别怕，我们先弄清楚这里发生了什么。')).toEqual([
      '……你醒了',
      '别怕，我们先弄清楚这里发生了什么。',
    ])
  })

  it('过滤空行并 trim 首尾空白', () => {
    expect(splitTextSegments('  a  ' + NL + NL + '  b ' + NL)).toEqual(['a', 'b'])
  })

  it('无换行时整段作为单段', () => {
    expect(splitTextSegments('只有一句')).toEqual(['只有一句'])
  })

  it('空串返回空数组', () => {
    expect(splitTextSegments('')).toEqual([])
  })
})

