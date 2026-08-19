<!-- 自制 CSS 文字 Logo（docs/15 §4.5）：不迁移 LingChat Logo 素材（§4.4），
     渐变 + 辉光 + 呼吸动画纯 CSS 实现。 -->
<template>
  <div class="pointer-events-none absolute right-[4vw] top-[3.5vw] z-10 select-none text-right">
    <h1 class="title-logo-main">完蛋，我被AI娘包围了</h1>
    <p class="title-logo-sub">— 第一章 · 调查 —</p>
  </div>
</template>

<style scoped>
.title-logo-main {
  margin: 0;
  font-size: clamp(26px, 3.2vw, 56px);
  font-weight: 900;
  letter-spacing: 0.12em;
  line-height: 1.3;
  background: linear-gradient(180deg, #f2fdff 0%, #aee6ff 45%, #5fb8e8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.45)) drop-shadow(0 0 18px rgba(135, 214, 244, 0.45));
  animation: logo-breathe 5.5s ease-in-out infinite;
}

.title-logo-sub {
  margin: 0.3em 0 0;
  font-size: clamp(12px, 1.2vw, 18px);
  letter-spacing: 0.5em;
  color: rgba(190, 230, 250, 0.75);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
}

@keyframes logo-breathe {
  0%,
  100% {
    filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.45)) drop-shadow(0 0 14px rgba(135, 214, 244, 0.35));
  }
  50% {
    filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.45)) drop-shadow(0 0 26px rgba(135, 214, 244, 0.6));
  }
}
</style>
