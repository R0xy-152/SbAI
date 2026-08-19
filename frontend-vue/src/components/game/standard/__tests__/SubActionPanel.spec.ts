// docs/14 §2.2（T3）：小面板渲染与 payload 组装（D6/D7：只回传所选 id）。
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SubActionPanel from '../SubActionPanel.vue'
import type { GameOption } from '../../../../api/game'

function option(partial: Partial<GameOption> & { id: string }): GameOption {
  return { label: partial.id, kind: 'evidence_present', payload: {}, ...partial }
}

describe('SubActionPanel（出示证据 / 私审质询）', () => {
  it('出示证据：选择证据与角色后提交对应 ids', async () => {
    const wrapper = mount(SubActionPanel, {
      props: {
        option: option({
          id: 'evidence_present',
          label: '出示证据',
          kind: 'evidence_present',
          payload: {
            character_id: 'claude',
            evidence: [
              { id: 'EV01_NOTE_V03', title: '压痕纸条', summary: '03:17 的笔记。' },
              { id: 'EV04_CURRENT_DEEPSEEK_REGISTRY', title: '当前DeepSeek实例信息', summary: 'DEEPSEEK#04' },
            ],
            characters: ['deepseek', 'claude'],
          },
        }),
        busy: false,
        message: null,
      },
    })
    const radios = wrapper.findAll('input[type="radio"]')
    // 证据 2 个 + 角色 2 个
    expect(radios).toHaveLength(4)
    await radios[1].setValue()
    await radios[3].setValue()
    await wrapper.find('[data-testid="sub-action-submit"]').trigger('click')
    const emitted = wrapper.emitted('submit')
    expect(emitted).toBeTruthy()
    expect(emitted?.[0]?.[0]).toEqual({
      character_id: 'claude',
      claim_ids: [],
      evidence_ids: ['EV04_CURRENT_DEEPSEEK_REGISTRY'],
    })
  })

  it('Claude 私审：勾选证词后提交 claim_ids', async () => {
    const wrapper = mount(SubActionPanel, {
      props: {
        option: option({
          id: 'private_interview:claude',
          label: '与 Claude 对质（私审）',
          kind: 'private_interview',
          payload: {
            character_id: 'claude',
            claims: [
              { id: 'CL_CLAUDE_01', text: '门是 DeepSeek 打开的。' },
              { id: 'CL_CLAUDE_02', text: 'Claude 没有看到 DeepSeek 本人。' },
            ],
            evidence: [],
            observation_options: [],
          },
        }),
        busy: false,
        message: null,
      },
    })
    const checks = wrapper.findAll('input[type="checkbox"]')
    expect(checks).toHaveLength(2)
    await checks[0].setValue()
    await checks[1].setValue()
    await wrapper.find('[data-testid="sub-action-submit"]').trigger('click')
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      character_id: 'claude',
      claim_ids: ['CL_CLAUDE_01', 'CL_CLAUDE_02'],
      evidence_ids: [],
    })
  })

  it('豆包私审：预选证词 + 观察选项提交到 evidence_ids 通道', async () => {
    const wrapper = mount(SubActionPanel, {
      props: {
        option: option({
          id: 'private_interview:doubao',
          label: '与豆包对质（私审）',
          kind: 'private_interview',
          payload: {
            character_id: 'doubao',
            claims: [{ id: 'CL_DB_01', text: 'GPT 早就在这里了。', preselected: true }],
            evidence: [],
            observation_options: [
              { id: 'OBSERVED_GPT_TEXT_ON_SCREEN', text: '她看到屏幕上出现了 GPT 相关文字。' },
              { id: 'GPT_CHARACTER_PRESENT', text: 'GPT 本人早已在场。' },
            ],
          },
        }),
        busy: false,
        message: null,
      },
    })
    // 未选观察时不可提交
    expect(wrapper.find('[data-testid="sub-action-submit"]').attributes('disabled')).toBeDefined()
    await wrapper.findAll('input[type="radio"]')[0].setValue()
    await wrapper.find('[data-testid="sub-action-submit"]').trigger('click')
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      character_id: 'doubao',
      claim_ids: ['CL_DB_01'],
      evidence_ids: ['OBSERVED_GPT_TEXT_ON_SCREEN'],
    })
  })

  it('GPT 私审：单条证据自动选中，直接提交', async () => {
    const wrapper = mount(SubActionPanel, {
      props: {
        option: option({
          id: 'private_interview:chatgpt',
          label: '与 ChatGPT 对质（私审）',
          kind: 'private_interview',
          payload: {
            character_id: 'chatgpt',
            claims: [],
            evidence: [{ id: 'EV06_SESSION_REPLAY_MARKER', text: 'EV06：恢复会话标记' }],
            observation_options: [],
          },
        }),
        busy: false,
        message: null,
      },
    })
    await wrapper.find('[data-testid="sub-action-submit"]').trigger('click')
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      character_id: 'chatgpt',
      claim_ids: [],
      evidence_ids: ['EV06_SESSION_REPLAY_MARKER'],
    })
  })

  it('关闭按钮触发 close 事件', async () => {
    const wrapper = mount(SubActionPanel, {
      props: {
        option: option({ id: 'x', payload: { character_id: 'claude' } }),
        busy: false,
        message: null,
      },
    })
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
