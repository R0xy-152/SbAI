import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import LoginView from '../LoginView.vue'

// 档位 B：二维码承载 '#invite=<邀请码>'，前端读 hash 自动登录直达 /（docs/18）。
const routerMock = vi.hoisted(() => ({
  hash: '#invite=CODE-1234-5678',
  query: {} as Record<string, string>,
  replace: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ hash: routerMock.hash, query: routerMock.query }),
  useRouter: () => ({ replace: routerMock.replace }),
}))

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  loginWithInvite: vi.fn(),
  logoutAccount: vi.fn(),
}))
vi.mock('../../api/auth', () => api)

const user = {
  user_id: 'u1',
  display_name: '展示账号 01',
  quota_total: 100,
  quota_used: 0,
  quota_remaining: 100,
}

describe('LoginView（二维码 #invite 直达）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
    routerMock.hash = '#invite=CODE-1234-5678'
    routerMock.query = {}
  })

  it('二维码片段 #invite 自动填充并自动登录后回跳 /', async () => {
    api.loginWithInvite.mockResolvedValue(user)
    const wrapper = mount(LoginView)
    await flushPromises()

    expect(api.loginWithInvite).toHaveBeenCalledTimes(1)
    expect(api.loginWithInvite).toHaveBeenCalledWith('CODE-1234-5678')
    expect(routerMock.replace).toHaveBeenCalledWith('/')
    expect((wrapper.find('#invite-code').element as HTMLInputElement).value).toBe('CODE-1234-5678')
  })

  it('无 #invite 片段时不自动登录', async () => {
    routerMock.hash = ''
    api.loginWithInvite.mockResolvedValue(user)
    mount(LoginView)
    await flushPromises()

    expect(api.loginWithInvite).not.toHaveBeenCalled()
  })

  it('手动提交仍走邀请码登录并回跳 redirect', async () => {
    routerMock.hash = ''
    routerMock.query = { redirect: '/chapters' }
    api.loginWithInvite.mockResolvedValue(user)
    const wrapper = mount(LoginView)

    await wrapper.find('#invite-code').setValue('MANUAL-CODE')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(api.loginWithInvite).toHaveBeenCalledWith('MANUAL-CODE')
    expect(routerMock.replace).toHaveBeenCalledWith('/chapters')
  })
})
