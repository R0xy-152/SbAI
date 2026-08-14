# 03 — Narrative Runtime

> **文档状态：** Active  
> **适用阶段：** 轻量技术验证阶段及后续正式剧情开发  
> **文档职责：** 定义自然语言输入如何参与剧情推进、剧情状态如何变化、LLM与确定性剧情系统之间的权限边界。  
> **不负责：** 角色人格、角色Prompt、LLM Provider实现、Memory组织方式、数据库表结构、Frontend动画实现、具体正式剧情内容。

---

# 1. Agent 读取规则

本文件是：

**Narrative Runtime 真相源。**

Agent 在实现任何与以下内容有关的功能前，应优先读取本文件：

- 剧情推进
- Scene切换
- 剧情Flag
- Fact揭露
- Event触发
- 玩家自然语言导致状态变化
- LLM建议剧情行为
- 最终推理与剧情判定

必须遵守：

1. **LLM不是剧情状态权威。**
2. Player自由文本不能直接修改Game State。
3. 所有剧情状态变化必须经过Narrative Runtime。
4. 玩家“猜中真相”不等于玩家已经获得该Fact。
5. 角色生成一句话不等于该句话自动成为世界事实。
6. 无法可靠判断Player意图时，默认不推进剧情。
7. 剧情推进失败不得阻止普通自由对话继续。
8. 本文件只定义运行机制，不定义正式故事答案。
9. 角色具体能知道什么、如何表达，由 `04-character-runtime.md` 衔接。
10. Memory如何提供历史上下文，由 `05-memory-design.md` 定义。

---

# 2. Narrative Runtime目标

本项目同时存在两种需求：

### 自由性

Player可以输入任意自然语言。

例如：

```text
这是哪里？
```

```text
是不是Claude把我们弄到这里的？
```

```text
我觉得你在骗我。
```

```text
DeepSeek，你能不能想办法把绳子解开？
```

---

### 确定性

游戏仍然必须拥有：

- 固定主线
- 固定事实
- 可控制的谜题顺序
- 可验证的剧情条件
- 明确的Scene
- 明确的Ending

因此系统必须实现：

# Generative Dialogue + Deterministic Narrative

即：

> **语言可以生成，剧情事实不能自由生成。**

---

# 3. 核心权威原则

运行时权威关系固定为：

```text
Narrative State
      >
Narrative Rules
      >
Validated Character Output
      >
Raw LLM Output
      >
Player Statement
```

---

## 3.1 Player不是世界状态写入接口

Player输入：

> “绳子已经断了。”

不能导致：

```text
player_is_bound = false
```

Player输入：

> “Claude刚才告诉过我真相。”

也不能直接导致：

```text
fact_x = revealed
```

Player输入首先只被视为：

# Player Utterance

即：

> 玩家说了一句话。

是否影响世界，需要Narrative Runtime另行判断。

---

## 3.2 LLM不是世界状态写入接口

LLM输出：

> “门打开了。”

不能自动导致：

```text
door_open = true
```

LLM输出：

> “你其实昨天见过Claude。”

也不能自动创造该世界事实。

LLM只能：

> 表达当前被允许表达的内容，并提出候选Narrative Proposal。

是否生效由Narrative Runtime决定。

---

# 4. Narrative Runtime总体结构

逻辑结构：

```text
Player Utterance
       ↓
Narrative Context
       ↓
Narrative Interpreter
       ↓
Candidate Signals
       ↓
Eligible Event Evaluation
       ↓
Narrative Decision
      / \
 NOOP   EVENT
  │       │
  │       ▼
  │   State Validation
  │       ↓
  │   Character Runtime
  │       ↓
  │   Output Validation
  │       ↓
  │   State Commit
  │       ↓
  └────→ Presentation Directives
              ↓
           Frontend
```

其中：

### Narrative Interpreter

理解Player这句话可能意味着什么。

### Event Evaluation

判断当前状态下是否真的允许触发剧情。

### Character Runtime

负责角色如何表达。

### Narrative Runtime

负责：

> 这件事是否真实发生。

---

# 5. Narrative State

Narrative Runtime只管理：

**确定性的剧情状态。**

当前逻辑至少包括：

```text
current_scene
story_phase
narrative_flags
revealed_facts
completed_events
active_objective
```

---

## 5.1 current_scene

表示当前正式剧情场景。

例如：

```text
binding_room
```

Scene只能由Narrative Runtime改变。

---

## 5.2 story_phase

表示主线当前阶段。

例如：

```text
prologue
investigation_01
investigation_02
finale
```

具体正式Phase由后续剧情内容定义。

---

## 5.3 narrative_flags

表示已经发生或成立的确定性剧情状态。

例如：

```text
claude_has_appeared = true
```

```text
player_is_bound = true
```

Flag必须有明确含义。

禁止使用模糊Flag：

```text
story_progress = 47
```

除非该数值具有明确业务定义。

---

## 5.4 revealed_facts

表示：

> Player已经通过游戏内合法渠道获得的主线事实。

例如：

```text
F001
F004
F009
```

注意：

**Player自己说出一个正确答案，不会自动加入 `revealed_facts`。**

---

## 5.5 completed_events

记录已经正式完成的剧情Event。

例如：

```text
EV_PROLOGUE_001
EV_PROLOGUE_002
```

用于：

- 防止重复触发
- 恢复Session
- 判断后续剧情资格

---

## 5.6 active_objective

表示当前剧情希望Player调查的主要问题。

例如概念上：

```text
确认是谁造成当前困境
```

Player无需看到传统任务栏。

该状态主要供：

- Narrative Interpreter
- Character Runtime
- 剧情调度

使用。

---

# 6. Narrative State不包含什么

以下内容不能因为方便而全部塞入Narrative State：

### 对话历史

属于Memory / Message系统。

### 角色完整人格

属于Character Runtime。

### 角色Prompt

属于Character Runtime。

### UI是否正在播放Shake

属于Frontend Presentation State。

### Provider请求状态

属于Provider Runtime。

Narrative State必须保持：

> **只描述剧情世界中已经成立的确定性状态。**

---

# 7. Ground Truth

正式剧情必须存在：

# Ground Truth

它表示：

> 游戏世界中真正发生过什么。

Ground Truth由作者预先定义。

不能由：

- Player
- DeepSeek
- ChatGPT
- Claude
- LLM Provider

在运行时自由创建。

---

# 8. Fact系统

主线重要事实应拥有稳定Fact ID。

例如：

```text
F001
F002
F003
```

具体Fact内容属于剧情Content，不在本文件维护。

---

## 8.1 Fact的意义

Fact用于区分：

```text
世界真实情况
```

与：

```text
角色说了什么
```

以及：

```text
Player猜了什么
```

三者不能混淆。

---

# 9. Fact状态层级

至少区分以下概念：

```text
Ground Truth Fact
       │
       ├── Character可知
       │
       ├── Character不可知
       │
       └── Player是否已获知
```

角色知识权限具体由Character Runtime衔接。

Narrative Runtime只负责：

> Player当前是否已经正式获得Fact。

---

# 10. 玩家猜中真相 ≠ Fact Reveal

这是解谜系统的核心规则。

假设真正事实：

```text
F021 = Claude执行了某项行为
```

Player在完全没有证据时说：

> “我猜就是Claude干的。”

即使猜对：

```text
F021
```

也不能因此加入：

```text
revealed_facts
```

此时Player只是产生：

# Hypothesis

---

## 10.1 Hypothesis的用途

正确猜测可以：

- 引起角色反应
- 触发追问
- 改变对话方向
- 成为某些Event的输入信号

但不能自动变成：

> 已确认事实。

---

# 11. Fact Reveal来源

一个Fact只有通过被授权的Narrative Source才能正式Reveal。

例如：

### 确定性剧情Event

```text
Event
→ Reveal F021
```

### 被允许的角色确认

```text
Validated Character Output
→ Narrative Runtime确认来源合法
→ Reveal F021
```

### 环境剧情信息

例如：

```text
屏幕显示确定记录
→ Reveal F021
```

---

# 12. Narrative Event

剧情推进的最小确定性单位定义为：

# Narrative Event

每个Event拥有唯一：

```text
event_id
```

例如：

```text
EV_PROLOGUE_CLAUDE_APPEARS
```

---

# 13. Event逻辑结构

一个Event逻辑上至少包含：

```text
Identity
Availability
Trigger
Requirements
Narrative Effects
Presentation Directives
Repeat Policy
```

---

## 13.1 Identity

```text
event_id
```

必须唯一并稳定。

Event ID一旦正式进入存档逻辑，不应随意修改。

---

## 13.2 Availability

决定：

> 当前Event有没有资格参与判断。

例如：

```text
scene = binding_room
```

```text
story_phase = prologue
```

只有满足Availability的Event才进入后续判断。

---

## 13.3 Trigger

描述：

> Player当前行为是否可能触发这个Event。

例如：

```text
Player询问绑架者身份
```

或：

```text
Player请求联系Claude
```

具体采用自然语言语义判断还是确定性条件，由Event类型决定。

---

## 13.4 Requirements

即使Trigger满足，也必须检查剧情前置条件。

例如：

```text
requires:
  claude_has_appeared = false
```

```text
requires_fact:
  F003
```

---

## 13.5 Narrative Effects

真正修改Game State的部分。

允许的概念操作包括：

```text
SET_FLAG
CLEAR_FLAG
REVEAL_FACT
SET_SCENE
SET_STORY_PHASE
COMPLETE_OBJECTIVE
SET_OBJECTIVE
MARK_EVENT_COMPLETE
```

---

## 13.6 Presentation Directives

Event可以要求Frontend表现：

```text
SHOW_CHARACTER
HIDE_CHARACTER
PLAY_ANIMATION
PLAY_EFFECT
FADE
```

这些是：

> 剧情语义指令。

具体如何渲染由Frontend决定。

---

## 13.7 Repeat Policy

Event必须明确：

```text
once
```

或：

```text
repeatable
```

主线Event默认：

# once

---

# 14. Event与Frontend动画分离

Narrative Runtime可以说：

```text
PLAY_ANIMATION:
  target = claude
  animation = shake
```

不能说：

```text
translateX(-13px)
rotate(4deg)
duration=311ms
```

具体动画表现不属于Narrative Runtime职责。

---

# 15. Narrative Interpreter

由于Player输入完全自由，系统需要一个逻辑组件：

# Narrative Interpreter

职责：

> 将自然语言转换为有限、结构化、不可直接修改状态的Narrative Signals。

---

# 16. Narrative Signal

Signal表示：

> Player当前这句话在剧情意义上可能表达了什么。

例如：

```text
SIG_ASK_LOCATION
```

```text
SIG_ASK_ESCAPE
```

```text
SIG_ASK_WHO_TRAPPED_US
```

```text
SIG_ACCUSATION_CLAUDE
```

```text
SIG_REQUEST_HELP
```

正式Signal根据剧情内容定义。

---

# 17. Signal不是Event

必须区分：

```text
Signal
```

和：

```text
Event
```

例如：

```text
Player：
“是不是Claude把我们绑来的？”
```

可能得到：

```text
SIG_ASK_WHO_TRAPPED_US
```

但这不意味着：

```text
EV_CLAUDE_APPEARS
```

一定执行。

还必须经过：

```text
Availability
+
Requirements
+
Current State
```

检查。

---

# 18. Signal不是Game State

Narrative Interpreter即使判断：

```text
SIG_ACCUSATION_CLAUDE
```

也只能输出：

> Player正在指控Claude。

不能输出：

```text
claude_is_guilty = true
```

---

# 19. Scoped Interpretation

Narrative Interpreter不能每轮都被告知：

> 整个游戏未来全部可能剧情。

否则会：

- 增加上下文
- 增加成本
- 增加未来剧情泄露风险
- 增加错误匹配

正确原则：

# 只解释当前可能相关的Signal

流程：

```text
Current Narrative State
        ↓
筛选 Eligible Events
        ↓
得到当前允许的 Signal 集合
        ↓
Narrative Interpreter
        ↓
只在该集合中判断
```

---

## 19.1 示例

当前Scene只存在：

```text
SIG_ASK_LOCATION
SIG_ASK_ESCAPE
SIG_ASK_CAPTOR
```

Narrative Interpreter不需要知道后期：

```text
SIG_FINAL_DECISION
```

的存在。

---

# 20. 最小Narrative Context

进行剧情语义判断时，默认只提供必要上下文：

```text
current_scene
story_phase
active_objective
relevant_flags
relevant_revealed_facts
eligible_signals
player_latest_message
```

只有语义确实依赖前一句话时，才加入少量最近对话。

---

## 20.1 禁止默认提供

Narrative Interpreter不应默认读取：

- 全部聊天历史
- 所有角色Memory
- 所有未来Fact
- 完整剧情真相
- 所有Ending条件

这既是：

**上下文管理原则**

也是：

**防剧透原则。**

---

# 21. Ambiguous策略

自然语言无法可靠判断时：

```text
AMBIGUOUS
```

必须：

# Fail Closed

即：

> 不推进Narrative State。

但是普通角色仍然可以回应。

---

## 21.1 示例

Player：

> “也许可以吧。”

在缺少足够上下文时无法判断是否：

```text
SIG_ACCEPT
```

则：

```text
Narrative = NOOP
```

而不是擅自推进剧情。

---

# 22. NOOP是正常结果

大多数自由聊天都不应该推进主线。

例如：

Player：

> “DeepSeek你饿吗？”

可能完全没有剧情Event。

此时：

```text
Narrative Decision = NOOP
```

仍然正常进入Character Runtime。

因此：

> **没有推进剧情不等于系统失败。**

---

# 23. Character Response与Narrative State关系

普通流程：

```text
Player Input
↓
Narrative Interpretation
↓
Narrative Decision
↓
Character Runtime
↓
Validated Response
↓
必要的Narrative Commit
↓
Frontend
```

Narrative Runtime可以向Character Runtime提供：

> 当前允许表达的剧情上下文。

但不能要求Character Runtime自行判断：

> 是否已经完成主线Event。

---

# 24. Narrative Directive

当某个Event准备发生时，Narrative Runtime可以生成：

# Narrative Directive

用于告诉Character Runtime：

> 当前回复需要完成什么剧情作用。

例如概念上：

```text
当前回复需要结束普通聊天，并为Claude出现做自然过渡。
```

Narrative Directive描述：

- 叙事目标
- 允许使用的Fact
- 必须避免的内容

不直接规定角色具体台词。

角色如何表达：

→ `04-character-runtime.md`

---

# 25. Character Output不能自行扩大Narrative权限

假设Narrative Directive只允许：

```text
F001
F004
```

角色不能因为模型认为剧情需要而主动说出：

```text
F019
```

即使：

> 这句话从语言上很合理。

也属于：

# Narrative Leakage

---

# 26. Narrative Leakage

Narrative Leakage包括：

- 提前透露未来Fact
- 透露角色当前无权知道的Fact
- 直接说出最终谜底
- 假装某个未发生Event已经发生
- 提及未解锁Scene的内部事实
- 把Player猜测当成世界真相

Narrative Runtime必须将其视为：

**无效输出。**

---

# 27. Invalid Character Output

如果生成式角色返回内容违反Narrative约束：

```text
Raw Output
↓
Narrative Validation
↓
INVALID
```

该输出：

- 不进入正式History
- 不写入Narrative State
- 不写入正式Memory
- 不作为Fact Reveal来源

系统应尝试：

```text
regenerate / repair / fallback
```

具体策略由Character Runtime与技术验证方案定义。

---

# 28. State Commit原则

Narrative State变化必须：

# Validate Before Commit

流程：

```text
Candidate Event
↓
检查当前State
↓
检查Requirements
↓
必要的角色输出成功
↓
输出验证通过
↓
Commit Narrative State
```

禁止：

```text
先修改State
↓
再调用LLM
↓
LLM失败
↓
留下半完成剧情
```

---

# 29. 原子性原则

单个Event对关键Narrative State的修改，应表现为一个完整逻辑提交。

例如：

```text
EV_CLAUDE_APPEARS
```

需要：

```text
claude_has_appeared = true
completed_events += EV_CLAUDE_APPEARS
```

不能出现：

```text
claude_has_appeared = true
```

但：

```text
EV_CLAUDE_APPEARS
```

仍被系统认为未完成。

---

# 30. Event幂等

主线Event必须具备：

# Idempotency

即：

重复收到同一Player输入时，不应重复执行已经完成的Event。

例如：

```text
completed_events contains EV_001
```

则：

```text
EV_001
```

不能再次：

- Reveal同一个剧情
- 重复切Scene
- 重复首次登场
- 重复写关键State

---

# 31. Event优先级

同一Player输入理论上可能匹配多个Event。

Narrative Runtime必须有稳定优先级。

默认：

```text
Current Critical Event
>
Main Story Event
>
Character Event
>
Optional Event
>
NOOP
```

当前轻量技术验证阶段只需要支持：

> 同一轮最多提交一个主要Narrative Event。

避免并发剧情导致状态混乱。

---

# 32. Scene Transition

Scene属于确定性Game State。

任何Scene切换必须：

```text
Proposal
↓
Narrative Runtime
↓
检查当前Scene
↓
检查目标Scene是否合法
↓
检查Requirements
↓
Commit
↓
Frontend执行转场
```

---

## 32.1 LLM Scene Proposal

LLM可以表达：

> “我们去另一个房间。”

或者提出：

```text
target_scene = xxx
```

但只能作为：

# Proposal

如果目标Scene：

- 不存在
- 尚未解锁
- 当前剧情不允许
- 与角色位置冲突

Narrative Runtime必须拒绝。

---

# 33. Player请求场景变化

同理：

Player：

> “我们去控制室吧。”

不能直接切Scene。

只能产生：

```text
SIG_REQUEST_MOVE_CONTROL_ROOM
```

然后检查：

```text
Narrative Requirements
```

---

# 34. 重要剧情行为

所有能够显著改变主线的行为必须由Narrative Event承担。

例如：

- Claude首次出现
- Player解除束缚
- 解锁新Scene
- 获得关键Fact
- 进入新章节
- 进入最终推理
- 触发Ending

不能仅依赖：

> 某次LLM自由发挥恰好说到了这里。

---

# 35. 自由聊天与主线解耦

系统必须允许：

```text
自由聊天很多轮
```

而：

```text
Narrative State不变
```

这属于正常玩法。

不能因为Player连续闲聊：

> 自动强制推进主线。

除非某个正式剧情Event明确要求时间或轮数触发。

---

# 36. 防Soft Lock原则

虽然Narrative Runtime采用严格条件，但正式剧情设计不能让Player因为：

> 没有说出某个唯一固定句子

而永远无法推进。

例如不能要求：

```text
Player必须精确输入：
“Claude是你绑架了我们吗？”
```

才触发剧情。

---

## 36.1 Semantic Trigger原则

同一个Narrative Signal应允许不同自然语言表达：

```text
是谁抓我们的？
```

```text
是不是Claude干的？
```

```text
把我们绑起来的人是谁？
```

```text
Claude跟这件事有关系吗？
```

都可能映射至相关Signal。

---

# 37. 必要剧情不得依赖模型随机发挥

如果某个Fact是通关必须：

> 必须由确定性的Narrative机制保证存在合法Reveal路径。

不能设计成：

> “希望某次LLM聊天时碰巧说出来。”

---

# 38. Player Knowledge

Narrative Runtime维护：

```text
revealed_facts
```

作为Player当前正式剧情知识。

它表示：

> 游戏认为Player已经有合理机会获知该Fact。

不要求系统证明现实中的Player是否真正理解。

---

# 39. Character与Player知识不同

必须允许：

```text
Character知道F010
Player不知道F010
```

也允许：

```text
Player知道F015
当前Character不知道F015
```

因此：

> Player不能因为知道某个Fact，就使所有角色同步获得该Fact。

角色知识系统由Character Runtime定义。

---

# 40. 剧情失败与模型失败分离

必须区分：

## Narrative NOOP

Player没有触发剧情。

这是正常状态。

## Narrative REJECT

Player试图做某件事，但条件不满足。

游戏可以通过角色自然回应。

## Runtime ERROR

系统运行失败。

例如：

- Provider超时
- 结构化输出无效
- 状态写入失败

三者不能混为：

```text
ERROR
```

---

# 41. Narrative Decision类型

逻辑上至少包含：

```text
NOOP
EVENT
REJECT
```

---

## NOOP

没有剧情变化。

继续普通聊天。

---

## EVENT

合法Narrative Event准备执行。

---

## REJECT

Player表达了明确剧情意图，但当前状态不允许。

例如：

Player：

> “我们现在去控制室。”

但Scene尚未解锁。

系统：

```text
REJECT
```

角色可以自然解释或拒绝。

---

# 42. REJECT不是系统报错

Frontend不应该显示：

> ERROR: SCENE_LOCKED

除非是调试模式。

正式体验应该由角色自然回应，例如：

> “现在去不了。”

具体措辞由Character Runtime决定。

---

# 43. MVP阶段Narrative范围

当前轻量技术验证阶段只要求证明：

```text
Player自由输入
↓
识别一个Narrative Signal
↓
触发一个Narrative Event
↓
修改至少一个Game State
↓
后续Character Response发生变化
```

---

# 44. MVP推荐测试Event

为避免技术验证阶段提前绑定正式剧情，允许建立：

# POC Narrative Fixture

例如：

```text
EV_POC_CLAUDE_APPEARS
```

其唯一目的：

> 验证自然语言能够触发确定性Event。

---

## 44.1 示例流程

初始：

```text
scene = binding_room
claude_has_appeared = false
```

Player可能输入：

```text
到底是谁把我们绑起来的？
```

Narrative Interpreter：

```text
SIG_ASK_CAPTOR
```

Event Evaluation：

```text
EV_POC_CLAUDE_APPEARS
```

Requirements：

```text
scene == binding_room
claude_has_appeared == false
```

通过后：

```text
claude_has_appeared = true
completed_events += EV_POC_CLAUDE_APPEARS
```

Frontend：

```text
SHOW_CHARACTER claude
FADE_IN
```

随后Claude可以开始对话。

---

## 44.2 POC Fixture不是正式剧情契约

该Event：

- 可以在正式剧情设计阶段替换
- 不代表最终故事必须按该方式推进

它只用于验证Narrative Runtime技术链。

---

# 45. MVP不需要实现的Narrative能力

当前不要求：

- 完整Fact Registry
- 多章节复杂State Machine
- 最终推理评分
- 多Ending
- 多Event同时执行
- 复杂分支合流
- 大规模支线
- 自动剧情规划
- Agent自主生成剧情
- 动态生成谜题

---

# 46. Narrative Runtime禁止事项

Agent不得实现：

```text
Player Input
↓
LLM
↓
“我觉得应该进入下一章”
↓
直接 chapter += 1
```

禁止：

```text
LLM生成一个新Fact
↓
直接写入Ground Truth
```

禁止：

```text
Player说“门开了”
↓
直接 door_open = true
```

禁止：

```text
Frontend检测关键词
↓
自行推进剧情
```

禁止：

```text
模型自己决定出现不存在的Scene
```

禁止：

```text
把完整未来剧情全部放进每轮Prompt
```

---

# 47. Narrative Content与Runtime分离

Narrative Runtime负责：

> 如何运行剧情。

Narrative Content负责：

> 剧情是什么。

逻辑上应保持：

```text
Runtime
├── Event Evaluator
├── State Transition
├── Signal Interpretation
└── Validation

Content
├── Events
├── Facts
├── Scenes
├── Objectives
└── Story Phases
```

修改故事内容不应该要求重写核心Runtime。

---

# 48. Runtime失败原则

如果Narrative Interpreter失败：

```text
Narrative = NOOP
```

普通聊天仍应尽可能继续。

如果Narrative Event无法安全提交：

```text
State保持原状
```

不得产生：

> 半完成主线状态。

---

# 49. 调试可观察性

技术验证阶段至少需要能够观察：

```text
Player Input
→ Interpreted Signal
→ Candidate Event
→ Decision
→ State Before
→ State After
```

这些信息用于开发和测试。

正式Player界面不需要显示。

---

# 50. Narrative Runtime验收条件

当前阶段至少验证：

### NR-01 Free Dialogue

普通自由聊天：

```text
Narrative = NOOP
```

且角色仍正常回应。

---

### NR-02 Semantic Trigger

Player使用不同自然语言表达同一剧情意图时：

能够映射到同一个有效Signal。

---

### NR-03 Deterministic Event

满足条件后：

同一个Event产生确定State Change。

---

### NR-04 Reject

条件不足时：

剧情不错误推进。

---

### NR-05 Idempotency

已经完成的Event不能重复执行。

---

### NR-06 State Authority

Player和LLM都不能直接修改Game State。

---

### NR-07 Recovery

模型调用失败时：

Narrative State保持一致。

---

# 51. 本文件不解决的问题

## DeepSeek具体怎样说话？

→ `04-character-runtime.md`

## ChatGPT病娇怎样逐步表现？

→ `04-character-runtime.md`

## Claude怎样保持反派与傲娇？

→ `04-character-runtime.md`

## 豆包Script怎样匹配台词？

→ `04-character-runtime.md`

## Character Response具体Schema是什么？

→ `04-character-runtime.md`

## 最近多少轮对话进入上下文？

→ `05-memory-design.md`

## 重要Memory怎样保存？

→ `05-memory-design.md`

## Narrative Interpreter技术上使用什么模型或规则？

当前不在本文件绑定具体技术实现。

→ 由技术验证阶段决定。

---

# 52. Agent最小上下文摘要

当Agent只需要处理Narrative相关代码时，可以使用：

```text
Narrative Runtime核心原则：

自由语言，确定剧情。

Player输入只是Utterance，
不能直接修改Game State。

LLM只是生成组件，
不能直接修改Game State。

Narrative State至少包含：
- current_scene
- story_phase
- narrative_flags
- revealed_facts
- completed_events
- active_objective

剧情推进单位：
Narrative Event

流程：
Player Input
→ Scoped Narrative Interpretation
→ Candidate Signal
→ Eligible Event
→ Requirements
→ Narrative Decision
→ Character Response
→ Validation
→ State Commit
→ Presentation Directive

Decision：
NOOP / EVENT / REJECT

玩家猜中真相 ≠ Fact Reveal。

Fact只能通过合法Narrative Source揭露。

重要剧情必须由确定性Event推进，
不能依赖LLM随机发挥。

Interpreter只获得当前相关Signal与最小剧情上下文，
不得默认读取全部未来剧情。

无法可靠判断：
Fail Closed → 不推进剧情。

主线Event：
默认once + idempotent。

Scene切换：
只能由Narrative Runtime批准。

State修改：
Validate Before Commit。

模型失败：
不得留下半完成Narrative State。

MVP：
只需验证1个自然语言Signal
→ 1个确定性Event
→ 1次Game State变化。
```