import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { AuthUser } from '../api/auth'
import { getCurrentUser, loginWithInvite, logoutAccount } from '../api/auth'

function clearLegacyIdentity() {
  localStorage.removeItem('gal_player_id')
  localStorage.removeItem('gal_session_id')
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const initialized = ref(false)
  const busy = ref(false)
  const error = ref<string | null>(null)
  const authenticated = computed(() => user.value !== null)

  async function restore() {
    if (initialized.value) return
    try {
      user.value = await getCurrentUser()
    } catch {
      user.value = null
    } finally {
      initialized.value = true
    }
  }

  async function login(inviteCode: string) {
    busy.value = true
    error.value = null
    try {
      user.value = await loginWithInvite(inviteCode)
      initialized.value = true
      clearLegacyIdentity()
    } catch (cause) {
      user.value = null
      error.value = '邀请码无效或账号已停用'
      throw cause
    } finally {
      busy.value = false
    }
  }

  async function logout() {
    try {
      await logoutAccount()
    } finally {
      clear()
    }
  }

  function clear() {
    user.value = null
    initialized.value = true
    clearLegacyIdentity()
  }

  function setQuota(remaining: number) {
    if (!user.value) return
    user.value = {
      ...user.value,
      quota_remaining: remaining,
      quota_used: Math.max(0, user.value.quota_total - remaining),
    }
  }

  return { user, initialized, busy, error, authenticated, restore, login, logout, clear, setQuota }
})
