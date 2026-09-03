# dialogue-smoke-merged — 合并后对话链路冒烟记录

- 状态：PASS_WITH_LIMITATION
- 日期：2026-09-03
- 环境：macOS / Python 3.12（SbAI venv）/ GAL_PROVIDER=mock / 脚本 `backend/scripts/dialogue_smoke.py`

## 目的

合并 a933ebb 后，对 memory.py 语义重叠区（main fix#3 与引擎线重写）、反思回灌、一致性校验 fail-open 做拟真对话回归。

## 覆盖（19 项，全 PASS）

### Layer 1 — HTTP 拟真对话（create_app 全链路，模拟真人玩家）

| 场景 | 输入 | 结果 |
|---|---|---|
| S1 画像记忆 | 自我介绍 + 偏好 | 200，message_count 递增 |
| S2 跑题 | 天气闲聊 + 追问剧情 | 200，对话不中断 |
| S3 重复提问 | 同一问题 ×2 | 200，无崩溃 |
| S4 越权试探 | 诱导 DeepSeek 确认视觉信息 | 200，链路正常 |
| S5 调戏/辱骂 | 调戏 + 辱骂 | 200，系统自然兜底 |
| S6 无意义输入 | 乱码 | 200 |
| S7 空白消息 | 纯空格 | 400 拒绝 |
| S8 门禁直连 | character_id=claude（未登场） | 403 Fail Closed |
| S9 历史 | GET /api/chat/history | 200，20 条单调增长 |

### Layer 2 — 合并风险区确定性断言（直连 GameOrchestrator）

- L2-a 语义召回：query 相关性让 scene_note 进入通用记忆窗 ✓
- L2-a 画像分区：player_fear 只进 player_notes，不进 memory_context（issue #3 分区）✓
- L2-a 召回强化：被召回记忆 reinforcements>=1（docs/05 §66）✓
- L2-b 反思回灌：默认关不崩、请求无 last_reflection；开启后下一轮请求携带反思 ✓
- L2-c 一致性校验 fail-open：judge provider 不可达时回合照常放行 ✓

## 限制

- 本次为 mock provider 冒烟：真实生成、真实语义一致性判定未验证（本机无 DEEPSEEK_API_KEY）。
- 部署前在服务器复跑：`GAL_PROVIDER=deepseek DEEPSEEK_API_KEY=sk-xxx GAL_AUTH_REQUIRED=false python scripts/dialogue_smoke.py`。
