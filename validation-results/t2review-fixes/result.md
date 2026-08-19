# T2review 修复记录（docs/T2review.md 的 1 P0 + 15 P1 + 7 P2）

> **状态：PASS_WITH_LIMITATION**（2026-08-19）。修复以最小侵入批次落地，
> 每批全量回归（backend pytest / vitest / typecheck+build / E2E / visual /
> compose 校验）后提交；未 push。

## 已修复

| 编号 | 项 | 修复 | 提交 |
|---|---|---|---|
| P0-1 | 仓库根静态挂载暴露文件 | 删除根挂载，仅 allow-list /char /backgroud /frontend-deprecated；CORS 收紧为本地 vite（GAL_CORS_ORIGINS 可扩展）；.dockerignore 排除 .env；实测 /backend/.env、根 404 | 49c42a4 |
| P1-1 | LLM 绕过 Claim Gate | CL_CLAUDE_05 disclosure gate（flag 未开即剔除该 claim，不否决整轮）；+2 测试 | b4bc505 |
| P1-2 | player_id 路径穿越 | player_id/save_id 白名单字符集 + resolve 后根内校验；API 400；+2 测试 | b4bc505 |
| P1-3 | Turn 不原子 | per-session threading.Lock 包裹 handle_turn；并发测试断言历史严格交替 | b4bc505 |
| P1-4 | Load 无完整性校验 | Load 前校验 phase/scene/角色白名单/消息形状，篡改存档拒绝；+1 测试 | 6260b44 |
| P1-5 | Auto Save 写失败吞 checkpoint | 标志先持久化、写失败回滚并保持 pending 可重试；+1 测试 | b4bc505 |
| P1-6 | 公共 API 覆盖 AUTO | AUTO 仅在新 checkpoint 时更新，否则 409 | b4bc505 |
| P1-7 | 旧请求污染新会话 | viewEpoch 请求 fencing（Load/New Game/卸载作废旧代次） | 801c1a7 |
| P1-8 | 对账抹掉表情/提前解锁 | applyPresentationStateView 保持 streaming/thinking；backend emotion 由持久化 mood 派生（不再恒 neutral） | 801c1a7 |
| P1-9 | Save/Load 不恢复 emotion | emotion 经 mood 持久化并在 state view 下发（Load 后表情恢复）；slot/animation 为瞬时表现，按 docs/13 §17.7 不持久化（已知限制） | 801c1a7 |
| P1-10 | Bad End 状态自相矛盾 | 在场角色=available_characters（bad_end 仅剩 GPT），input 仅 to_be_continued 锁定；opening 阶段保留 deepseek 兜底 | b4bc505 / 801c1a7 |
| P1-11 | Named Action no-op | shake/fade_in/fade_out 渲染类 + avatar 消费 backend animation | 801c1a7 |
| P1-12 | 背景被黑色根遮挡 | 背景 z-index 0；基线重拍并视觉复核「房间场景真实可见」 | 801c1a7 |
| P1-13 | slot 百分比当 px | slot 独立字段按百分比站位，offsetX 仅手动偏移 | 801c1a7 |
| P1-14 | Provider 200 异常逃逸 | deepseek/anthropic 非 JSON/非对象统一 ProviderError | b4bc505 |
| P1-15 | PG/backend 暴露所有接口 | postgres 不发布宿主端口；backend 只绑 loopback | 49c42a4 |
| P2-1 | 公开回复无 heard_by | 角色消息（含脚本行主回复）记录听众 | b4bc505 |
| P2-2 | health 请求 /api/api/health | 改为 /health（标题界面健康状态恢复正常，TITLE 基线变化源于此） | 801c1a7 |
| P2-3 | Text Speed 不生效不持久化 | settings store 持久化 localStorage + typeWriterSpeed 消费 | 801c1a7 / 本次 |
| P2-4 | 卡片嵌套 button/死控件 | ManualSaveSlot 去嵌套；AutoSaveCard save 模式只读展示 | 801c1a7 |
| P2-5 | Vue 依赖 frontend-deprecated | 豆包占位图迁入 char/doubao/pic/；Vue 不再引用旧前端素材 | 801c1a7 |
| P2-6 | 生产门禁缺失 | Compose GAL_PROVIDER 默认 auto（不再固定 mock）；Playwright 默认不复用既有服务（PW_REUSE_SERVERS=1 显式开启） | 6260b44 |
| P2-7 | Docs 漂移 | frontend-vue/README.md 任务状态校准；AGENT.MD/AGENTS.md/CLAUDE.md 为用户在途文件，未触碰 | 6260b44 |

## 验证

- backend pytest：**396 passed**, 12 skipped（新增 9 个修复回归测试）
- frontend：vitest 25 passed、typecheck+build PASS、E2E 6/6、visual 18/18
  （基线重拍：背景可见 + 站位/卡片/健康状态变化；TITLE 变化来自 P2-2）
- docker compose config -q 通过；安全冒烟：根/.env/.py 均 404、
  CORS 拒绝任意 Origin、素材路径 200
- 未运行：真实 Provider、真实 PostgreSQL 集成、容器启动（本机条件限制，
  仍按 review 结论「生产路径不能视为已验证」）

## 已知限制

- P1-9 的 slot/animation：瞬时表现不持久化（docs/13 §17.7 约定），Load 后
  按可用性/自动排位恢复，表情经 mood 恢复。
- PG 用例 12 skipped 为设计行为（无 DSN 时跳过）；真实验证需环境。
- 豆包仍为占位素材（无正式立绘）。
