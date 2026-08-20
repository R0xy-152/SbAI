结论：**FAIL，不具备发布条件**。按合并口径确认 **1 个 P0、15 个 P1、7 个 P2**。本次仅审查与复现，未修改代码；用户原有的 [CLAUDE.md](D:/gal/CLAUDE.md) 变更未触碰。

## P0

1. **整个仓库/容器文件系统被静态公开。** [main.py](D:/gal/backend/app/main.py:172) 将 `REPO_ROOT` 挂载到 `/`，开发环境指向 `D:\gal`，Docker 中指向 `/`；同时 [main.py](D:/gal/backend/app/main.py:81) 开放 `CORS: *`，[Dockerfile](D:/gal/backend/Dockerfile:15) 又把整个 backend 复制进镜像，而 [.dockerignore](D:/gal/.dockerignore:1) 未排除 `backend/.env`。实测 `/backend/.env` 和会话 JSON 均返回 200，且任意 Origin 获得跨域许可；验证未输出任何密钥内容。必须删除根挂载，仅 allow-list 资源目录，排除 `.env`，收紧 CORS 和 backend 暴露端口。

## P1

1. **LLM 可以绕过剧情 Gate，直接提交关键 Claim/Evidence。** [validation.py](D:/gal/backend/app/game/validation.py:44) 未校验 `claim_refs`，[orchestrator.py](D:/gal/backend/app/game/orchestrator.py:322) 随后直接提交。复现中 opening 阶段伪造 Claude 的 `CL_CLAUDE_05`，在 disclosure 尚未开启时成功授予 `EV07_CLAUDE_RECOVERY_ACCESS`。

2. **JSON 存档存在 `player_id` 路径穿越。** [saves.py](D:/gal/backend/app/api/saves.py:28) 只做长度限制，部分查询甚至没有限制；[repository.py](D:/gal/backend/app/save/repository.py:135) 直接拼接文件路径。`../escaped` 已复现写到存档根目录之外。

3. **同一 Session 的 Turn 不具备原子性。** [orchestrator.py](D:/gal/backend/app/game/orchestrator.py:187) 缺少 per-session 锁，Provider 读取、状态提交、两条消息写入和持久化均可交错。双线程复现时两个 Provider 都看见空历史，最终消息顺序为 `player, player, character, character`。Save Capture 也在多个时间点重新读取状态，[repository.py](D:/gal/backend/app/persistence/repository.py:89) 还共用固定临时文件。

4. **Load 没有执行完整性校验，且先写入后验证。** [service.py](D:/gal/backend/app/save/service.py:227) 只检查记录版本，[orchestrator.py](D:/gal/backend/app/game/orchestrator.py:1142) 直接创建并持久化 Session。篡改角色可用性和跨角色 Memory Scope 后仍能成功加载。

5. **Auto Save 写失败会永久吞掉 checkpoint。** [service.py](D:/gal/backend/app/save/service.py:128) 先标记 checkpoint，再写 AUTO slot；异常又在 [orchestrator.py](D:/gal/backend/app/game/orchestrator.py:1049) 被吞掉。复现中第一次写入失败后 `pending=False`，后续永不重试。

6. **公共 Auto Save API 可覆盖最后一个合法 checkpoint。** [saves.py](D:/gal/backend/app/api/saves.py:73) 无条件调用 `save_auto`，普通回合也能覆盖 AUTO slot，破坏 Continue 的确定性 checkpoint 保证。

7. **缺少统一请求 epoch/mutex，旧请求可污染新会话。** [GameView.vue](D:/gal/frontend-vue/src/views/GameView.vue:128) 在 `await` 后无 session/mounted 校验，组件卸载也不取消请求；多步调查又在每一步重新读取 `sessionId`。慢请求期间 Load/New Game 可导致旧响应覆盖新画面，或把同一调查的后续步骤发给新会话。

8. **`reconcileStage()` 立即抹掉回复表情并提前解除忙碌保护。** [GameView.vue](D:/gal/frontend-vue/src/views/GameView.vue:137) 先应用回复，再立即对账；后端 [orchestrator.py](D:/gal/backend/app/game/orchestrator.py:784) 固定返回 `neutral`，适配器同时把状态改成 idle。结果是非 neutral 表情消失，打字尚未结束时 Save/Load 已重新可用。

9. **Save/Load 没有恢复 named emotion、animation 和 slot。** 对话历史未保存这些字段，[service.py](D:/gal/backend/app/save/service.py:85) 保存的所谓 emotion 实际是内部 mood；反序列化忽略 presentation。`angry/shake` 存档加载后已复现为 `neutral/None`。

10. **Bad End 的权威状态自相矛盾。** 剧情代码只保留 ChatGPT，但 [orchestrator.py](D:/gal/backend/app/game/orchestrator.py:786) 又强行加入 DeepSeek并锁定输入；现行 [Bad-End 文档](<D:/gal/docs/08-最终自证与Bad-End.md:130>) 要求保留与 GPT 的自然语言对话。前端又没有真正执行 input lock。

11. **Named Presentation Action 多数是 no-op。** `shake/fade_in` 仅写入 store，`SCREEN_SHAKE/GLITCH` 没有渲染消费者，[GameRoleAvatar.vue](D:/gal/frontend-vue/src/components/game/standard/GameRoleAvatar.vue:144) 只监听 emotion。当前 opening 发出的动画动作实际不显示。

12. **游戏背景被压在黑色根节点后。** [GameBackground.vue](D:/gal/frontend-vue/src/components/game/standard/GameBackground.vue:77) 使用 `z-index:-2`，[GameView.vue](D:/gal/frontend-vue/src/views/GameView.vue:363) 根节点为黑色；视觉基线已把纯黑背景固化为“正确结果”。

13. **角色 slot 百分比被当成像素偏移。** [presentation-adapter.ts](D:/gal/frontend-vue/src/adapters/presentation-adapter.ts:51) 将 RIGHT 的百分比写进 `offsetX`，[GameRoleAvatar.vue](D:/gal/frontend-vue/src/components/game/standard/GameRoleAvatar.vue:93) 再按 px 叠加；Claude 的 RIGHT 已实际显示在左侧。

14. **Provider 的 HTTP 200 异常响应逃逸统一错误边界。** [deepseek.py](D:/gal/backend/app/providers/deepseek.py:84) 和 [anthropic.py](D:/gal/backend/app/providers/anthropic.py:78) 在 try 之外解析 JSON。HTML 响应产生误导性 400，数组根产生 500，而不是统一的 503 `ProviderError`。

15. **PostgreSQL 以固定 `gal/gal` 凭据发布到所有网络接口。** [docker-compose.yml](D:/gal/docker-compose.yml:30) 暴露 `0.0.0.0:5432`；backend 8000 也直接发布。PG 应仅在 Compose 内网可见，backend 应内网访问或至少绑定 loopback。

## P2

1. 角色公开回复没有 `heard_by/audience`，[orchestrator.py](D:/gal/backend/app/game/orchestrator.py:445) 导致同场其他角色永远听不到公开台词。

2. 健康检查因 `/api` 重复而请求 `/api/api/health`：[http.ts](D:/gal/frontend-vue/src/api/http.ts:5)、[game.ts](D:/gal/frontend-vue/src/api/game.ts:81)；而且只探测一次。

3. Text Speed 设置不生效也不持久化；兼容层仍硬编码 `50`：[settings.ts](D:/gal/frontend-vue/src/stores/settings.ts:4)、[lingchat-compat.ts](D:/gal/frontend-vue/src/adapters/lingchat-compat.ts:171)。

4. Save/Load 卡片存在嵌套 `<button>` 和无响应的可点击控件：[ManualSaveSlot.vue](D:/gal/frontend-vue/src/components/save/ManualSaveSlot.vue:21)、[AutoSaveCard.vue](D:/gal/frontend-vue/src/components/save/AutoSaveCard.vue:19)。

5. 现役 Vue 仍生产依赖 `frontend-deprecated`，豆包甚至使用 Claude placeholder：[asset-resolver.ts](D:/gal/frontend-vue/src/adapters/asset-resolver.ts:12)、[nginx.conf](D:/gal/frontend-vue/nginx.conf:39)。

6. 生产路径门禁缺失：Compose 固定 `GAL_PROVIDER=mock`；标准测试跳过 12 个 PG 用例；Playwright 默认测试 JSON backend，且本地 `reuseExistingServer=true` 可能命中旧服务。

7. Docs-first 真相源明显漂移：[AGENT.MD](D:/gal/AGENT.MD:9)、[AGENTS.md](D:/gal/AGENTS.md:11)、[frontend-vue/README.md](D:/gal/frontend-vue/README.md:45) 仍描述旧路径、docs13 未完成和 frontend-only Compose；架构文档称 PG 为统一持久层，但当前 Session 仍是 JSON。

## 验证

- Backend：`377 passed, 12 skipped, 1 warning`；跳过项均为未配置 DSN 的 PostgreSQL 用例。
- Frontend：unit `20/20`、typecheck、build 全部通过。
- E2E：`2/2`，覆盖 1366×768、1920×1080。
- Vue visual：`12/12`，但黑色背景已被错误基线接受。
- `npm audit`：0 vulnerabilities。
- `docker compose config -q`：通过。
- 未运行真实 Provider、真实 PostgreSQL 集成和容器启动，因此这些生产路径不能视为已验证。
- 工作树最终仍只有用户原有的 `CLAUDE.md` 修改。

建议修复顺序：**根静态挂载/CORS/端口 → Claim Gate、Session 原子性、Load/AutoSave 完整性 → 前端请求 fencing → Presentation 契约 → PG 门禁与文档校准**。

::code-comment{title="[P0] 根静态挂载暴露敏感文件" body="这里把 REPO_ROOT 挂到根 URL；开发环境可读取仓库中的 .env 和 Session JSON，容器内则指向文件系统根。应删除此 mount，只对明确的素材目录建立 allow-list 静态路由。" file="D:/gal/backend/app/main.py" start=172 end=172 priority=0}

::code-comment{title="[P1] Claim 缺少权威 Gate" body="response.claim_refs 在这里被直接转换并提交，没有根据当前剧情状态计算 allowed claims；不可信 LLM 因而可以提前解锁关键证据。提交前必须进行状态、角色和 disclosure gate 校验。" file="D:/gal/backend/app/game/orchestrator.py" start=322 end=322 priority=1}

::code-comment{title="[P1] player_id 可逃逸存档目录" body="未经规范化的 player_id 被直接拼入文件路径，../ 已可写到 data_dir 外。应限定 opaque ID 格式，并在 resolve 后验证目标仍位于存档根目录。" file="D:/gal/backend/app/save/repository.py" start=135 end=135 priority=1}

::code-comment{title="[P1] Turn 缺少 Session 原子边界" body="整个 handle_turn 没有按 Session 串行化，Provider 上下文、状态提交、消息追加和持久化会交错。应使用 per-session lock 或事务覆盖完整 Turn，并让 Save Capture 使用同一边界。" file="D:/gal/backend/app/game/orchestrator.py" start=187 end=187 priority=1}

::code-comment{title="[P1] checkpoint 在存档成功前被消费" body="save_auto 在 slot upsert 前调用 _mark_checkpoints；写入失败时 checkpoint 已永久标记且异常会被吞掉。标记必须发生在持久化成功之后，或与 save 放入同一事务。" file="D:/gal/backend/app/save/service.py" start=128 end=128 priority=1}

::code-comment{title="[P1] Load 前缺少完整性校验" body="当前加载路径只检查 schema version，随后直接导入并持久化。应先在临时不可变快照上验证角色可用性、Memory Scope、scene/cursor、evidence/inference 等 invariant，全部通过后才能创建 Session。" file="D:/gal/backend/app/save/service.py" start=227 end=227 priority=1}

::code-comment{title="[P1] 旧请求可写入新会话画面" body="await 返回后直接应用响应，没有捕获请求 Session、组件存活状态或 generation token。Load/New Game/卸载时应取消或作废旧请求，并在写 Pinia 前核对 active session。" file="D:/gal/frontend-vue/src/views/GameView.vue" start=138 end=138 priority=1}

::code-comment{title="[P1] 背景位于黑色容器之后" body="负 z-index 将背景放到 GameView 的黑色根背景后，现有视觉基线因此只看到纯黑。应建立非负 stacking context，并在视觉测试中断言真实背景可见。" file="D:/gal/frontend-vue/src/components/game/standard/GameBackground.vue" start=77 end=77 priority=1}