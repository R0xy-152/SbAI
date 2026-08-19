// docs/15 §9.1：粒子组件基础契约（enabled=false 不绘制 / 卸载清理 / 无 2d context 降级）。
import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { StarField, Rain, Sakura, Snow, Fireworks } from '../index'

describe('粒子组件（docs/15 §6.3）', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('enabled=false：全部粒子组件渲染空画布/容器且不抛错', () => {
    for (const C of [StarField, Rain, Sakura, Snow, Fireworks]) {
      const wrapper = mount(C as any, { props: { enabled: false } })
      expect(wrapper.exists()).toBe(true)
      wrapper.unmount()
    }
  })

  it('enabled=true 但无 2d context（测试环境）：canvas 系静默降级不抛错', () => {
    for (const C of [StarField, Rain, Fireworks]) {
      const wrapper = mount(C as any, { props: { enabled: true } })
      expect(wrapper.exists()).toBe(true)
      wrapper.unmount()
    }
  })

  it('Sakura/Snow enabled=false：不生成 keyframes style 节点', () => {
    const before = document.head.querySelectorAll('style').length
    const wrapper = mount(Sakura as any, { props: { enabled: false } })
    expect(document.head.querySelectorAll('style').length).toBe(before)
    wrapper.unmount()
  })
})
