<script setup lang="ts">
defineProps<{
  permissionName: string
  description: string
  grantLabel: string
  denyLabel: string
  busy?: boolean
}>()
const emit = defineEmits<{ (event: 'respond', grant: boolean): void }>()
</script>

<template>
  <div class="permission-request" role="dialog" aria-modal="true" aria-labelledby="perm-title">
    <section>
      <div class="perm-kicker">SYSTEM · PERMISSION REQUEST</div>
      <h2 id="perm-title">她申请以下权限</h2>
      <div class="perm-name">
        <span aria-hidden="true">◆</span> {{ permissionName }}
      </div>
      <p class="perm-desc">{{ description }}</p>
      <div class="perm-actions">
        <button class="deny" type="button" :disabled="busy" @click="emit('respond', false)">
          {{ denyLabel }}
        </button>
        <button class="grant" type="button" :disabled="busy" @click="emit('respond', true)">
          {{ grantLabel }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.permission-request {
  position: absolute;
  inset: 0;
  z-index: 32;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(3, 10, 17, 0.62);
  backdrop-filter: blur(10px) saturate(0.85);
}
section {
  width: min(32rem, 100%);
  padding: clamp(1.5rem, 5vw, 2.6rem);
  border: 1px solid rgba(131, 224, 251, 0.42);
  border-radius: 0.9rem;
  color: #e7faff;
  background: linear-gradient(160deg, rgba(4, 18, 28, 0.97), rgba(6, 28, 40, 0.96));
  box-shadow: 0 2rem 5rem rgba(0, 0, 0, 0.55), 0 0 32px rgba(70, 199, 237, 0.16);
}
.perm-kicker {
  color: #63b9d0;
  font: 700 0.7rem/1.4 monospace;
  letter-spacing: 0.18em;
}
h2 { margin: 0.9rem 0 1.2rem; color: #a4ecff; font-size: clamp(1.5rem, 5vw, 2.2rem); }
.perm-name {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 0.9rem;
  border: 1px solid rgba(146, 233, 255, 0.32);
  border-radius: 0.55rem;
  color: #dff8ff;
  font-weight: 750;
  background: rgba(8, 40, 54, 0.5);
}
.perm-name span { color: #7bdaf5; }
.perm-desc { margin: 1rem 0 0; color: #a9ccd6; line-height: 1.7; }
.perm-actions { display: flex; justify-content: flex-end; gap: 0.7rem; margin-top: 1.6rem; }
button {
  border: 1px solid rgba(142, 229, 255, 0.5);
  border-radius: 0.55rem;
  padding: 0.65rem 1.4rem;
  color: #e7faff;
  background: rgba(18, 88, 111, 0.5);
  font-weight: 750;
  cursor: pointer;
}
button.deny { border-color: rgba(255, 143, 161, 0.4); color: #ffdce2; background: rgba(86, 16, 30, 0.5); }
button.grant { border-color: rgba(126, 240, 189, 0.55); color: #d8fff0; background: rgba(11, 82, 56, 0.6); }
button:disabled { cursor: not-allowed; opacity: 0.45; }
</style>
