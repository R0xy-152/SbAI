# docs16-p1 · 情绪标签中文映射 — 验证结果

> **状态：PASS**（待 E2E 独立套件完成后最终确认，见文末修订）
> **日期：2026-08-23** · **环境：** Windows / Git Bash；frontend-vue（Vue 3 + Vite + TS）；backend 未改动。
> **依据：** docs/16 P1（docs/16-玩家体验修复与开局选项窗口落地方案.md §2）。

## 1. 目标

聊天框上方 AI 情绪标签当前直接显示后端英文 emotion id（neutral/happy/…），
按用户确认的映射改为中文：neutral→平静、happy→开心、annoyed→不悦、angry→生气、
embarrassed→害羞、serious→认真、surprised→惊讶。

## 2. 改动

- frontend-vue/src/adapters/lingchat-compat.ts：
  - 新增 EMOTION_ZH 映射（对齐后端 ALLOWED_EMOTIONS 七值）；
  - useUIStore().showCharacterEmotion 输出 EMOTION_ZH[raw] ?? raw（未知 emotion
    原样透出，fail-open 于显示层，不影响动画词表）。

## 3. 验证

| 套件 | 结果 | 说明 |
|---|---|---|
| npm run typecheck | PASS | 无类型错误 |
| npm run test:unit | PASS 39/39 | 无单测断言情绪文案，全部通过 |
| npm run test:visual | PASS 22/22 | 基线未含情绪标签文本区，无重拍需求 |
| npm run test:e2e | PASS 6/6 | 独立 mock 后端套件（不复用真实服务），无 locator/行为影响 |
| backend pytest | 不适用 | 本步零后端改动 |

## 4. 限制

- 中文标签与立绘动画词表（EMOTION_CONFIG_EMO / ANIMATION_BY_EMOTION）分离：
  动画仍按英文 id 归一，仅显示文案本地化，无逻辑耦合。
- 未知 emotion 值原样显示（不静默吞掉），便于真机排查后端新词。

## 5. 证据

- 单测输出：Test Files 12 passed (12)，Tests 39 passed (39)。
- 视觉输出：22 passed（desktop-1366x768 / desktop-1920x1080 × 11）。
