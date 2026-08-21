<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const inviteCode = ref('')

async function submit() {
  const code = inviteCode.value.trim()
  if (!code || auth.busy) return
  try {
    await auth.login(code)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.replace(redirect.startsWith('/') ? redirect : '/')
  } catch {
    // Store owns the user-facing error.
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card" aria-labelledby="login-title">
      <p class="login-kicker">ACCESS VERIFICATION</p>
      <h1 id="login-title">输入展示邀请码</h1>
      <p class="login-copy">邀请码会绑定你的存档与 AI 对话额度，在其他设备可重复使用。</p>
      <form @submit.prevent="submit">
        <label for="invite-code">邀请码</label>
        <input
          id="invite-code"
          v-model="inviteCode"
          name="invite-code"
          type="text"
          autocomplete="off"
          autocapitalize="characters"
          spellcheck="false"
          maxlength="128"
          placeholder="XXXX-XXXX-XXXX-XXXX"
          autofocus
        />
        <p v-if="auth.error" class="login-error" role="alert">{{ auth.error }}</p>
        <button type="submit" :disabled="!inviteCode.trim() || auth.busy">
          {{ auth.busy ? '验证中…' : '进入游戏' }}
        </button>
      </form>
      <p class="login-warning">当前为 HTTP 小规模展示环境，请勿在公共网络分享邀请码。</p>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100%; display: grid; place-items: center; padding: 24px;
  color: #edfaff; background:
    radial-gradient(circle at 25% 15%, rgba(23, 157, 210, 0.2), transparent 38%),
    linear-gradient(145deg, #030710, #071524 55%, #03070d);
}
.login-card {
  width: min(440px, 100%); padding: 38px; border: 1px solid rgba(131, 225, 255, 0.26);
  border-radius: 18px; background: rgba(4, 15, 27, 0.9); box-shadow: 0 28px 90px #0009;
}
.login-kicker { margin: 0 0 10px; color: #69d9ff; font-size: 12px; letter-spacing: .22em; }
h1 { margin: 0; font-size: 28px; font-weight: 600; }
.login-copy, .login-warning { color: #abc2d0; line-height: 1.65; }
form { display: grid; gap: 12px; margin-top: 28px; }
label { font-size: 13px; color: #c9e9f4; }
input {
  width: 100%; padding: 14px 15px; border: 1px solid #407189; border-radius: 9px;
  color: white; background: #06111e; font: 500 16px/1.2 ui-monospace, monospace;
  letter-spacing: .08em; outline: none;
}
input:focus { border-color: #6ddcff; box-shadow: 0 0 0 3px #35bde724; }
button {
  margin-top: 4px; padding: 13px; border: 1px solid #69d9ff; border-radius: 9px;
  color: #03101a; background: #80e2ff; font-weight: 700; cursor: pointer;
}
button:disabled { opacity: .45; cursor: not-allowed; }
.login-error { margin: 0; color: #ff9a9a; font-size: 13px; }
.login-warning { margin: 24px 0 0; font-size: 12px; }
</style>
