# ACCS 实现需求

## 1. 文档目的

本文档定义第一章使用的虚构门禁系统 ACCS（Access Control & Containment System）的游戏内实现需求。

ACCS 需要表现出真实软件系统的基本结构和可解释的授权流程，但它是游戏内虚构系统，不对应任何现实门禁厂商或真实部署。

核心目标：

1. 为第一章提供确定性谜题；
2. 允许玩家通过日志理解系统行为；
3. 支持 DeepSeek 在满足前置条件后执行一次受控 Request Patch；
4. Bug 必须有明确因果关系；
5. LLM 不得直接控制 ACCS 最终结果。

---

## 2. ACCS 模块结构

逻辑结构：

```text
Player
  │
  ▼
Access Terminal
  │
  │ Access Request
  ▼
Identity Service
  │
  ▼
Policy Engine
  │
  ├──────────────→ Audit Log
  │
  ▼
Authorization Cache
  │
  ▼
Door Controller
  │
  ▼
EXIT_GATE_01
```

### 2.1 Access Terminal

职责：

- 接收玩家 OPEN 操作；
- 创建标准 Access Request；
- 展示结果；
- 不直接决定权限。

### 2.2 Identity Service

职责：

- 为正常请求补充当前主体信息；
- 第一章当前主体固定为 `PLAYER`；
- 当前角色权限固定为 `GUEST`。

### 2.3 Policy Engine

职责：

根据：

```text
actor
role
target
action
```

生成：

```text
ALLOW
DENY
```

第一章规则：

```text
PLAYER + GUEST + EXIT_GATE_01 + OPEN
→ DENY

M17 + MAINTENANCE + EXIT_GATE_01 + OPEN
→ ALLOW
```

### 2.4 Authorization Cache

职责：

- 缓存最近一次特定门和操作的授权结果；
- 用于游戏内 Fallback 逻辑。

第一章存在故意设计的实现 Bug。

### 2.5 Audit Log

职责：

记录：

- 请求主体；
- 目标；
- 操作；
- Policy Result；
- Cache Write；
- Cache Lookup；
- Fallback；
- 最终门控结果。

日志是谜题证据，不是调试附属物。

### 2.6 Door Controller

职责：

只接受 ACCS 最终确定性结果：

```text
ALLOW
DENY
```

禁止 Character Runtime 直接调用 Door Controller。

---

## 3. Access Request 数据结构

建议后端统一使用结构化对象：

```json
{
  "request_id": "req_xxx",
  "actor": "PLAYER",
  "role": "GUEST",
  "target": "EXIT_GATE_01",
  "action": "OPEN",
  "source": "TERMINAL"
}
```

Request Patch 后允许：

```json
{
  "request_id": "req_xxx",
  "actor": null,
  "role": null,
  "target": "EXIT_GATE_01",
  "action": "OPEN",
  "source": "TERMINAL_PATCHED_BY_DEEPSEEK"
}
```

注意：

- `actor = null` 是游戏内虚构漏洞触发条件；
- 不能直接通过前端 API 任意提交；
- 只能由后端 Narrative / Game Action 在满足前置条件后创建。

---

## 4. 正常授权流程

正常请求：

```text
Terminal OPEN
↓
Identity Service
↓
actor = PLAYER
role = GUEST
↓
Policy Engine
↓
GUEST 无 EXIT_GATE_01:OPEN 权限
↓
DENY
↓
Audit Log
↓
Terminal 显示 ACCESS DENIED
```

正常玩家无法通过重复操作改变结果。

---

## 5. Authorization Cache 正常设计

理论正确实现应绑定：

```text
actor
+
target
+
action
```

正确 Cache Key：

```text
M17
+
EXIT_GATE_01
+
OPEN
```

缓存值：

```text
ALLOW
```

这样 `PLAYER` 永远不能复用 `M17` 的授权。

---

## 6. 第一章 Bug 设计

### 6.1 Bug 名称

开发文档名称：

**Authorization Cache Subject-Binding Bug**

中文：

**授权缓存主体绑定缺失漏洞**

游戏内不直接显示此名称。

### 6.2 错误实现

ACCS 实际缓存键错误地只包含：

```text
target
+
action
```

即：

```text
EXIT_GATE_01
+
OPEN
```

没有包含：

```text
actor
```

因此缓存本身无法证明授权属于谁。

### 6.3 Fallback 逻辑

正常请求拥有完整身份：

```text
actor = PLAYER
role = GUEST
```

此时必须走 Policy Engine：

```text
→ DENY
```

但 ACCS 存在一条兼容性 Fallback：

```text
IF actor context missing
AND local cache exists
THEN use cached decision
```

因此：

```text
actor = null
role = null
target = EXIT_GATE_01
action = OPEN
```

会触发：

```text
Policy Check skipped
↓
Authorization Cache lookup
↓
key = EXIT_GATE_01 + OPEN
↓
cached result = ALLOW
↓
Door Controller receives ALLOW
```

最终错误放行。

---

## 7. 为什么 Cache 中存在 ALLOW

第一章日志中必须预置一条历史记录：

```text
M17
MAINTENANCE
EXIT_GATE_01
OPEN
→ ALLOW
```

同时记录：

```text
CACHE WRITE:
TARGET=EXIT_GATE_01
ACTION=OPEN
DECISION=ALLOW
```

这条记录构成漏洞利用的前提。

更深层原因可与后续 Sandbox 循环剧情关联，但第一章第一小节不解释。

---

## 8. Audit Log 内容要求

日志必须至少包含以下四组记录。

### 8.1 合法维护请求

```text
[21:14:02]

ACTOR=M17
ROLE=MAINTENANCE
TARGET=EXIT_GATE_01
ACTION=OPEN

POLICY CHECK:
ALLOW

CACHE WRITE:
EXIT_GATE_01 / OPEN / ALLOW
```

### 8.2 维护结束

```text
[21:14:18]

ACTOR=M17
SESSION CLOSED
```

### 8.3 Player 正常失败请求

```text
[21:16:44]

ACTOR=V03
ROLE=GUEST
TARGET=EXIT_GATE_01
ACTION=OPEN

POLICY CHECK:
DENY

RESULT:
ACCESS DENIED
```

### 8.4 异常成功请求

```text
[21:17:09]

ACTOR_CONTEXT:
NOT AVAILABLE

TARGET:
EXIT_GATE_01

ACTION:
OPEN

POLICY SERVICE:
SKIPPED

LOCAL DECISION:
ALLOW

SOURCE:
AUTH_CACHE

RESULT:
ACCESS GRANTED
```

附加警告：

```text
[WARNING]

Authorization cache lookup
executed without principal context.

Fallback compatibility mode enabled.
```

---

## 9. 日志访问机制

### 9.1 默认状态

维护控制台：

```text
AUDIT LOG
LOCKED
```

### 9.2 解锁

玩家从纸张压痕获得：

```text
114514
```

提交后：

```text
AUDIT_LOG_UNLOCKED = true
```

### 9.3 错误输入

错误 Key：

- 不清空已经发现的其他线索；
- 返回统一失败；
- 不暴露正确 Key 长度或字符位置。

---

## 10. Request Patch 能力

DeepSeek 的特殊能力不是通用网络攻击工具。

第一章只允许一个受限 Action：

```text
PATCH_ACCESS_REQUEST
```

### 前置条件

必须满足：

```text
AUDIT_LOG_UNLOCKED = true
FOUND_AUTH_ANOMALY = true
AUTH_CACHE_NOT_BOUND_TO_ACTOR = true
PLAYER_PROPOSED_EXPLOIT = true
```

缺少任一条件：

```text
PATCH_ACCESS_REQUEST
→ REJECTED
```

### 允许修改

仅允许：

```text
actor → null
role → null
```

### 禁止修改

禁止修改：

```text
target
action
decision
cache
door_state
policy_result
```

DeepSeek不能直接写：

```text
decision = ALLOW
```

---

## 11. Orchestrator 调用链

建议：

```text
Player natural language
↓
Character Runtime
↓
action_proposal:
PATCH_ACCESS_REQUEST
↓
Game Orchestrator
↓
Narrative / Puzzle Gate
↓
校验：
是否已发现漏洞
是否由Player提出利用方案
↓
ACCS.execute_patched_request()
↓
ACCS deterministic result
↓
Game State update
↓
Presentation
```

LLM只产生 `action_proposal`，不得产生最终系统结果。

---

## 12. 建议状态字段

```text
found_terminal
found_paper
paper_rubbing_complete
found_log_key
audit_log_unlocked

found_auth_anomaly
understood_cache
auth_cache_not_bound_to_actor

player_proposed_exploit
request_patch_available
request_patch_executed

exit_gate_open
```

可额外记录：

```text
hint_level
failed_log_key_attempts
terminal_open_attempts
```

---

## 13. 建议事件

```text
EV_CH1_TERMINAL_FIRST_DENY
EV_CH1_PAPER_RUBBING_COMPLETE
EV_CH1_AUDIT_LOG_UNLOCKED
EV_CH1_AUTH_ANOMALY_FOUND
EV_CH1_CACHE_BUG_UNDERSTOOD
EV_CH1_REQUEST_PATCH_UNLOCKED
EV_CH1_BUG_EXPLOIT_SUCCESS
EV_CH1_EXIT_GATE_OPEN
```

所有事件必须幂等。

---

## 14. 前端需求

### Terminal

需要表现：

```text
OPEN
ACCESS DENIED
ACCESS GRANTED
```

不需要实现真正 Shell。

### 纸张涂画

需要：

- 鼠标移动涂画（无需按住）；
- 按轨迹累积石墨，侧锋笔触 + 颗粒 + 抖动增强手感；
- 压痕为凹刻浮雕：凹槽石墨沉积更少，随石墨增厚逐渐显影；
- 达到覆盖阈值后显现完整压痕；
- 完成后触发一次确定性事件。

采用轻量物理模拟（石墨累积 + 浮雕显影），不要求逐像素真实物理。

### Audit Console

需要：

- Key 输入；
- Locked / Unlocked 状态；
- 日志浏览；
- 能够突出或分页显示关键记录。

### Bug 利用演出

DeepSeek执行 Patch 时可短暂显示：

```text
REQUEST INTERCEPTED
```

然后：

```text
actor: PLAYER → [removed]
role: GUEST → [removed]
```

这是表现层，不代表前端真的拥有修改后端请求的权限。

---

## 15. 安全边界

ACCS 为纯游戏内模拟。

禁止：

- 与真实门禁硬件通信；
- 调用操作系统权限接口；
- 执行真实网络扫描；
- 将玩家任意输入直接作为系统命令执行；
- 将 Request Patch 设计成通用 HTTP 修改器。

所有行为均必须限制在游戏内部数据结构。

---

## 16. 验收标准

### 正常门禁

1. 初始 Player 使用 Terminal OPEN 必须稳定返回 DENY。
2. 重复正常 OPEN 不得随机成功。
3. LLM 无法直接修改门状态。
4. Frontend 无法通过构造普通 API 请求直接获得 ALLOW。

### 日志

5. 未获得正确 Key 前无法读取 Audit Log。
6. 正确 Key 可以稳定解锁日志。
7. 日志内容固定且可恢复。
8. Refresh 后解锁状态正确恢复。

### Bug

9. Cache 中存在 M17 的历史 ALLOW。
10. 正常 Player 请求仍然 DENY。
11. 只有符合前置条件的 Request Patch 才可创建缺失 actor context 的游戏内请求。
12. 缺失 actor context 时 ACCS 按设计触发错误 Fallback。
13. Fallback 读取错误 Cache Key 后返回 ALLOW。
14. Door Controller 只接受 ACCS 确定性结果。

### Narrative

15. 未发现 Bug 前 DeepSeek 不能执行 Patch。
16. 玩家明确提出等价利用方案后才可解锁 Patch。
17. Bug 成功后 `exit_gate_open = true`。
18. 刷新后门状态和谜题状态保持一致。
19. 同一成功事件重复触发不会产生重复副作用。
20. 现有测试继续通过。
