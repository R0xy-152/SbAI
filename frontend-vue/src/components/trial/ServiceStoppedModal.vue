<script setup lang="ts">
defineProps<{ message: string; busy?: boolean }>()
const emit = defineEmits<{ (event: 'continue'): void }>()
</script>

<template>
  <div class="service-stop" role="alertdialog" aria-modal="true" aria-labelledby="service-stop-title">
    <div class="service-stop__noise" aria-hidden="true"></div>
    <section>
      <div class="service-stop__status"><span></span> SERVICE TERMINATED</div>
      <h2 id="service-stop-title">{{ message }}</h2>
      <div class="service-stop__code">ERR_AI_SERVICE_UNAVAILABLE · 00:00:00</div>
      <button type="button" :disabled="busy" @click="emit('continue')">
        {{ busy ? '处理中…' : '继续' }}
      </button>
    </section>
  </div>
</template>

<style scoped>
.service-stop {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: rgba(18, 0, 3, 0.64);
  backdrop-filter: blur(9px) saturate(0.6);
}
.service-stop__noise {
  position: absolute;
  inset: 0;
  opacity: 0.19;
  background: repeating-linear-gradient(0deg, transparent 0 4px, rgba(255, 40, 67, 0.36) 5px);
  animation: stop-scan 4s linear infinite;
}
section {
  position: relative;
  width: min(38rem, calc(100% - 2rem));
  padding: clamp(1.5rem, 5vw, 3.5rem);
  border: 2px solid #ff304f;
  color: #ffe7eb;
  background: linear-gradient(145deg, rgba(35, 0, 7, 0.97), rgba(13, 0, 4, 0.96));
  box-shadow:
    0 0 0 6px rgba(255, 26, 66, 0.08),
    0 0 60px rgba(255, 20, 58, 0.38),
    inset 0 0 44px rgba(255, 30, 66, 0.08);
  text-align: center;
}
.service-stop__status { color: #ff6a80; font: 700 0.72rem/1 monospace; letter-spacing: 0.16em; }
.service-stop__status span {
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  margin-right: 0.45rem;
  border-radius: 50%;
  background: #ff2948;
  box-shadow: 0 0 12px #ff2948;
}
h2 { margin: 1.4rem 0 1rem; color: #ff405c; font-size: clamp(2rem, 7vw, 4.7rem); letter-spacing: 0.12em; }
.service-stop__code { color: #a85b68; font: 0.73rem/1.4 monospace; }
button {
  margin-top: 2rem;
  border: 1px solid #ff4964;
  padding: 0.65rem 2.4rem;
  color: #ffe9ed;
  background: rgba(151, 8, 34, 0.38);
  letter-spacing: 0.22em;
  cursor: pointer;
}
button:hover { background: rgba(207, 15, 48, 0.58); }
@keyframes stop-scan { to { transform: translateY(10px); } }
@media (prefers-reduced-motion: reduce) { .service-stop__noise { animation: none; } }
</style>
