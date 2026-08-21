import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  loginWithInvite: vi.fn(),
  logoutAccount: vi.fn(),
}))

vi.mock('../../api/auth', () => api)

import { useAuthStore } from '../auth'

const user = {
  user_id: 'u1',
  display_name: '展示账号 01',
  quota_total: 100,
  quota_used: 2,
  quota_remaining: 98,
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('邀请码登录后清理旧匿名身份并更新额度', async () => {
    localStorage.setItem('gal_player_id', 'legacy-player')
    localStorage.setItem('gal_session_id', 'legacy-session')
    api.loginWithInvite.mockResolvedValue(user)
    const auth = useAuthStore()

    await auth.login('CODE')

    expect(auth.user?.display_name).toBe('展示账号 01')
    expect(localStorage.getItem('gal_player_id')).toBeNull()
    expect(localStorage.getItem('gal_session_id')).toBeNull()
    auth.setQuota(97)
    expect(auth.user?.quota_used).toBe(3)
  })

  it('恢复失败保持未登录，退出清理本地状态', async () => {
    api.getCurrentUser.mockRejectedValue(new Error('401'))
    api.logoutAccount.mockResolvedValue(undefined)
    const auth = useAuthStore()
    await auth.restore()
    expect(auth.authenticated).toBe(false)

    auth.user = { ...user }
    localStorage.setItem('gal_session_id', 'active')
    await auth.logout()
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('gal_session_id')).toBeNull()
  })
})
