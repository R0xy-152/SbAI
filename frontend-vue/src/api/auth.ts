import { http } from './http'

export interface AuthUser {
  user_id: string
  display_name: string
  quota_total: number
  quota_used: number
  quota_remaining: number
}

export async function loginWithInvite(inviteCode: string): Promise<AuthUser> {
  const { data } = await http.post<AuthUser>('/auth/login', { invite_code: inviteCode })
  return data
}

export async function getCurrentUser(): Promise<AuthUser> {
  const { data } = await http.get<AuthUser>('/auth/me')
  return data
}

export async function logoutAccount(): Promise<void> {
  await http.post('/auth/logout')
}
