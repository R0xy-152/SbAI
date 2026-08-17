# 功能 07：Recovery 与管理员权限小游戏

## 1. 目标

第一章后半段发生Sandbox危机。Player与四个AI共同完成大型合作小游戏，最终结果：

```text
Player获得Admin
OR
ChatGPT获得Admin
```

结果由Player在小游戏中的行为自然产生。

## 2. Crisis

触发：`SANDBOX_INTEGRITY_FAILURE`。

表现：场景Glitch、部分UI缺失、角色立绘异常、系统节点损坏。

```text
NO ACTIVE ADMINISTRATOR
EMERGENCY RECOVERY REQUIRED
```

## 3. 核心玩法

无强实时要求，使用回合制/行动点。

```text
CORE
├── WORLD
├── MEMORY
├── CHARACTER
├── AUTH
└── EXIT
```

节点可处于`CORRUPTED / UNVERIFIED / UNSTABLE`。

Player决定修复顺序、使用谁的能力、是否授权GPT Shortcut。

## 4. 四AI能力

### DeepSeek — PREVIEW
模拟Player准备执行的操作会影响哪些节点，不代替决定。

### Claude — VERIFY
判断目标节点是真异常还是表象。

### ChatGPT — OPTIMIZE
一次修复多个相关节点，明显更强、更方便；每次使用：

```text
GPT_DELEGATED_PRIVILEGE += 1
```

### 豆包 — PROTECT
保护一个节点本轮不被删除/腐化。

## 5. Player能力

Player负责：选目标、选AI能力、定修复顺序、决定是否走GPT Shortcut、决定是否额外验证。

## 6. Admin归属

### Player Admin

```text
critical_nodes_recovered = true
human_credential_restored = true
gpt_delegated_privilege < threshold
```

结果：`PRIMARY AUTHORITY = PLAYER_V04`。

### GPT Admin

若`gpt_delegated_privilege >= threshold`：

```text
PRIMARY AUTHORITY = CHATGPT
ROLE = ADMIN
```

## 7. 设计目标

GPT路线必须明显更舒服、更高效、更容易，让“把权限交给她”成为真实诱惑，而非显眼Bad End按钮。

## 8. 失败

不建议传统Game Over。状态过低时可触发Emergency Stabilize、损失可选Evidence或迫使使用GPT Shortcut，但主线继续。

## 9. 验收标准

1. 不依赖API响应速度。
2. Player拥有最终操作权。
3. 四AI能力职责不同。
4. GPT能力明显强。
5. 使用GPT能力确定性累积权限。
6. Admin归属由行为计算。
7. Refresh可恢复Recovery State。
8. 两条Admin路线稳定复现。
