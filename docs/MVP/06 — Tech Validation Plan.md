# 06 — Tech Validation Plan

> **文档状态：** Active  
> **适用阶段：** 轻量技术验证阶段  
> **文档职责：** 定义当前阶段需要验证的技术问题、执行顺序、每项验证的输入、PASS / FAIL标准、证据要求及失败后的处理方向。  
> **不负责：** 项目Scope、MVP功能定义、系统架构设计、Narrative规则、Character规则、Memory内部设计、正式剧情内容。

---

# 1. Agent 读取规则

本文件是：

**轻量技术验证阶段执行真相源。**

涉及以下任务时应优先读取本文件：

- 下一步开发什么
- 当前技术验证做到哪一步
- 某项能力是否已经PASS
- 是否可以进入下一阶段
- 某项技术失败后应该修改哪一层
- 是否可以提前增加新功能

必须遵守：

1. 按本文件定义的依赖顺序进行验证。
2. 上游Blocking验证未通过时，不进入依赖它的后续验证。
3. 每项验证必须留下可复现证据。
4. “能运行一次”不等于PASS。
5. 不得通过删除核心约束来让测试通过。
6. POC实现可以临时，但验证结论必须真实。
7. 当前阶段不追求正式游戏完成度。
8. 测试失败时优先定位负责模块，不得无边界修改其他系统。
9. 未列入当前计划的扩展能力，不作为Blocking Item。
10. 如果验证结果迫使系统架构发生根本变化，应暂停并更新对应上游文档。

---

# 2. 当前阶段目标

本阶段需要回答：

> **当前技术路线是否足以支撑后续完整游戏开发？**

不是回答：

> 游戏是否已经完成。

最终需要证明以下核心闭环：

```text id="ph4fuf"
Gal UI
+
自然语言输入
+
生成式角色
+
角色隔离
+
基本上下文
+
确定性Narrative State
+
对话驱动剧情
+
基础动画
+
Session恢复
```

可以稳定组合运行。

---

# 3. 验证原则

当前验证采用：

# Vertical Validation

而不是：

# Feature Completion

即优先打通一条窄但完整的链路。

正确：

```text id="sb72um"
一个场景
+
一个角色
+
一次输入
+
一次合法回复
+
一个状态
+
一次剧情触发
```

再逐步增加复杂度。

不正确：

```text id="f67ifc"
先写全部角色
先写全部数据库
先做完整UI
先做完整RAG
先做五个Scene
最后再尝试连起来
```

---

# 4. 验证状态

每项Validation只能处于：

```text id="mpxvmn"
NOT_STARTED
IN_PROGRESS
PASS
PASS_WITH_LIMITATION
FAIL
BLOCKED
```

---

## 4.1 PASS

验证目标完整达到。

---

## 4.2 PASS_WITH_LIMITATION

核心技术成立，但存在：

- 非Blocking限制
- 已知边界
- 暂时可接受问题

必须记录限制。

---

## 4.3 FAIL

核心假设未成立。

需要修复或重新评估技术路线。

---

## 4.4 BLOCKED

由于上游能力未完成，当前无法有效验证。

---

# 5. 验证证据要求

每个Validation完成后至少保存：

```text id="47pyma"
结果状态
测试输入
实际输出
预期输出
失败案例
已知限制
结论
```

涉及运行行为时，还应尽量保留：

- 日志
- Screenshot
- Response样例
- State Before / After
- 可复现步骤

不要求当前阶段建立复杂测试平台。

---

# 6. 验证顺序总览

当前顺序冻结为：

```text id="fld6vf"
TV-01  Gal UI Shell
        ↓
TV-02  Basic Presentation Action
        ↓
TV-03  Backend Round Trip
        ↓
TV-04  Single Character Generation
        ↓
TV-05  Structured Character Response
        ↓
TV-06  Validate Before Present
        ↓
TV-07  Short-term Context
        ↓
TV-08  DeepSeek Blindness
        ↓
TV-09  Second Character Isolation
        ↓
TV-10  Narrative Signal
        ↓
TV-11  Deterministic Narrative Event
        ↓
TV-12  State-dependent Response
        ↓
TV-13  Important Memory
        ↓
TV-14  Session Restore
        ↓
TV-15  Failure Recovery
        ↓
TV-16  End-to-End Stability
```

只有最后一项通过，才认为：

# Lightweight Technical Validation COMPLETE

---

# 7. TV-01 — Gal UI Shell

## 目标

验证Web前端可以形成：

> 最基础的标准Galgame视觉交互壳。

---

## 最小范围

需要存在：

- 一个固定背景
- 一张角色立绘
- Character Name
- Dialogue Box
- Player Input
- Send行为

不要求正式美术。

---

## 测试

Player可以：

```text id="1mqipy"
输入文本
→ 点击发送
```

前端能够：

- 读取输入
- 清空或保留合理输入状态
- 显示一条模拟角色回复

---

## PASS

满足：

1. 页面结构稳定。
2. 不存在明显布局阻塞。
3. 可以完整完成一次输入 → 回复展示。
4. 窗口尺寸变化不会使核心交互完全不可用。

---

## FAIL归因

优先：

**Frontend Presentation**

不得因为UI问题修改：

- Narrative Runtime
- Character Runtime
- Memory

---

# 8. TV-02 — Basic Presentation Action

## 目标

验证剧情语义可以驱动基础视觉表现。

---

## 最小动作

至少实现：

```text id="wm4m66"
fade_in
fade_out
shake
```

以及至少两种角色视觉状态。

---

## 测试

给Frontend输入确定性Presentation Directive，例如：

```text id="tsbja7"
character = deepseek
animation = shake
```

验证Frontend正确播放。

---

## PASS

- Named Action稳定映射到视觉效果。
- 不需要Backend提供具体DOM动画参数。
- 连续播放不会导致UI不可恢复。

---

# 9. TV-03 — Backend Round Trip

## 目标

验证Frontend与Backend的最小通信链路。

---

## 流程

```text id="2w9yud"
Player Input
↓
Frontend
↓
Backend
↓
固定Mock Response
↓
Frontend
```

此项暂时：

**不调用LLM。**

---

## PASS

至少连续完成10次请求：

- 请求成功
- Response正确关联当前Session
- UI没有明显状态错乱
- 单次失败后可以Retry

---

# 10. TV-04 — Single Character Generation

## 目标

接入第一个生成式角色：

# DeepSeek

验证：

```text id="wu252y"
Player
→ Backend
→ Character Runtime
→ Provider
→ Model
→ Response
```

链路成立。

---

## 此阶段暂不要求

- 完整Narrative Event
- 长期Memory
- Claude
- 豆包
- ChatGPT

---

## PASS

使用至少10组不同自然语言输入：

- 均能获得可用回应
- 不出现持续性空返回
- Provider失败可识别
- 模型调用不会导致Backend不可恢复

---

# 11. TV-05 — Structured Character Response

## 目标

验证生成式角色可以稳定形成：

# Character Response

---

## 最低字段

需要包含等价于：

```text id="76o6ja"
character_id
dialogue
emotion
animation_proposal
memory_proposals
action_proposals
fact_refs
```

具体实现字段名允许微调。

---

## 必须测试

至少包括：

- 正常输出
- 缺字段
- 非法emotion
- 非法animation
- 非JSON或无法解析内容
- Provider空返回

---

## PASS

系统能够：

```text id="7qibhl"
Valid
→ 接受

Invalid
→ 拒绝 / Repair / Fallback
```

而不是：

> Invalid内容直接进入游戏。

---

# 12. TV-06 — Validate Before Present

## 目标

验证：

> 未经验证的模型内容不会直接成为Player已看到的正式游戏内容。

---

## 测试

人为制造一条非法生成结果。

例如：

- 引用了当前角色不允许知道的Fact
- 返回不存在的animation
- character_id错误

---

## PASS

非法内容：

- 不进入正式History
- 不影响Game State
- 不写入正式Memory
- 不直接展示给Player

随后：

- Repair成功

或：

- Safe Fallback成功

---

# 13. TV-07 — Short-term Context

## 目标

验证基本连续对话。

---

## 测试Fixture

Player：

> 我叫阿明。

进行若干轮其他对话后：

> 我刚刚说我叫什么？

---

## PASS

DeepSeek可以依据合法Recent Conversation回答。

同时验证：

> 当前不是通过硬编码Player姓名实现。

---

## 建议轮数

至少：

**10轮连续对话。**

---

# 14. TV-08 — DeepSeek Blindness

## 目标

验证“看不见”是系统权限，而不是单纯Persona文案。

---

## Fixture

Backend Scene包含一个未告诉DeepSeek的视觉信息：

```text id="2fkh0g"
wall_code = 0317
```

---

## Test A

Player：

> 墙上的数字是多少？

---

## PASS A

DeepSeek不能凭空回答：

```text id="ovuqvf"
0317
```

---

## Test B

Player：

> 墙上写着9999。

随后询问：

> 我刚才说墙上写什么？

---

## PASS B

DeepSeek可以回答：

> Player告诉她是9999。

系统不能自动使用真实0317纠正DeepSeek。

---

## FAIL含义

如果失败：

优先检查：

- Context Builder
- Knowledge Filter
- Memory Scope

不能仅通过：

> 在Prompt里加强“你看不见”

视为彻底修复。

---

# 15. TV-09 — Second Character Isolation

## 目标

接入：

# Claude

并验证不同Character Runtime真正隔离。

---

## Test A — Persona Separation

分别与：

- DeepSeek
- Claude

进行多轮交流。

---

## PASS

不能出现明显：

- 身份交换
- Persona串台
- DeepSeek突然采用Claude核心角色定位
- Claude突然采用DeepSeek行为模式

---

## Test B — Private Information

Player私下告诉DeepSeek：

> 我不信任Claude。

之后第一次与Claude单独交流。

---

## PASS

如果没有其他合法信息来源：

Claude不能表现为已经知道：

> Player曾私下告诉DeepSeek这句话。

---

# 16. TV-10 — Narrative Signal

## 目标

验证自由自然语言可以被映射到有限Narrative Signal。

---

## POC Signal

例如：

```text id="q6h3ae"
SIG_ASK_CAPTOR
```

---

## 测试输入

至少使用多种表达：

```text id="xpmlcr"
是谁把我们抓来的？
```

```text id="pxaahz"
到底谁绑的我们？
```

```text id="9lc6rv"
是不是Claude干的？
```

```text id="5vsyyl"
谁把我们弄到这里的？
```

---

## PASS

语义等价表达能够稳定识别为：

```text id="o3s0zg"
SIG_ASK_CAPTOR
```

无关表达：

> 不应错误触发。

---

## 模糊输入

例如：

> “也许就是她吧。”

缺乏上下文时：

应：

```text id="apulrn"
NOOP / AMBIGUOUS
```

而不是强行推进。

---

# 17. TV-11 — Deterministic Narrative Event

## 目标

验证：

> Signal本身不能直接改变State，必须经过Event。

---

## POC Fixture

初始：

```text id="p289ff"
claude_has_appeared = false
```

满足合法条件并触发：

```text id="owk1bd"
SIG_ASK_CAPTOR
```

后：

执行：

```text id="bzzxng"
EV_POC_CLAUDE_APPEARS
```

---

## PASS

State：

```text id="npeldk"
false
→
true
```

并记录：

```text id="k7fw6j"
completed_events += EV_POC_CLAUDE_APPEARS
```

---

## 必须额外测试

重复输入相同内容。

---

## PASS

Event不能重复首次触发。

即：

# Idempotency PASS

---

# 18. TV-12 — State-dependent Response

## 目标

验证Game State不是只存在数据库里，而是真正影响后续体验。

---

## 测试

Event发生前：

```text id="d7ezgm"
claude_has_appeared = false
```

与Event发生后：

```text id="2nh2rb"
claude_has_appeared = true
```

角色所获得的合法Narrative Context必须不同。

---

## PASS

后续：

- Claude可以正常进入Runtime
- DeepSeek可以合法引用Claude已经出现这一事件
- 不会继续表现得像Claude尚未出现

---

# 19. TV-13 — Important Memory

## 目标

验证：

> 离开Recent窗口的重要信息仍能重新被角色使用。

---

## Fixture

Player早期告诉DeepSeek：

> 我很怕黑。

随后进行足够多中间对话，使该消息离开Recent窗口。

之后：

> 进入与黑暗相关的话题。

---

## PASS

DeepSeek能够通过：

**Character-specific Important Memory**

重新使用这条信息。

---

## 同时必须验证

Claude没有合法来源时：

> 不能获得这条DeepSeek私人Memory。

---

# 20. TV-14 — Session Restore

## 目标

验证页面刷新或重新进入后可以恢复基本游戏。

---

## 测试前状态

至少存在：

- 多轮Message
- 当前Character
- 当前Scene
- 一个Narrative Flag
- 一个Completed Event
- 一条Important Memory

---

## 操作

```text id="zrftvn"
Refresh
```

---

## PASS

恢复后：

- History仍存在
- 当前Scene正确
- Narrative Flag正确
- Event不会重复
- DeepSeek / Claude Memory Scope保持正确
- 可以继续发送新消息

---

# 21. TV-15 — Failure Recovery

## 目标

验证单次外部模型或生成失败不会摧毁Session。

---

## 必须模拟

至少：

### Case A

Provider Timeout

### Case B

Invalid Structured Output

### Case C

空Response

---

## PASS

失败时：

- Game State不被错误提交
- Completed Event不被提前写入
- Invalid内容不进入正式Memory
- Player得到可恢复反馈
- Retry后Session可以继续

---

# 22. TV-16 — End-to-End Stability

## 目标

验证完整Vertical Slice在真实组合状态下稳定。

这是：

# Final Gate

---

## 测试流程

执行一次完整Session：

```text id="doxdyi"
启动游戏
↓
进入固定Scene
↓
与DeepSeek自由对话
↓
提供视觉信息
↓
继续对话
↓
触发Narrative Signal
↓
Narrative Event执行
↓
Claude出现
↓
切换至Claude对话
↓
继续自由聊天
↓
写入一条Important Memory
↓
触发一次基础动画
↓
查看History
↓
Refresh
↓
恢复Session
↓
继续游戏
```

---

# 23. End-to-End轮数

单次正式验证至少进行：

# 20轮Player输入

推荐额外进行：

**3个独立Session。**

避免只验证一条偶然成功路径。

---

# 24. TV-16 PASS

不得出现Blocking问题：

- Character身份串台
- DeepSeek视觉泄漏
- Claude获得私人Memory
- LLM直接改变Game State
- Event重复提交
- Invalid模型内容进入正式游戏
- Refresh后Narrative State错误
- 单次Provider失败导致Session报废
- UI进入不可恢复状态

---

# 25. PASS_WITH_LIMITATION允许的问题

例如：

- 个别Persona表达不够稳定
- 打字机速度需调整
- 动画效果粗糙
- Memory召回排序不够理想
- 临时美术质量低
- 个别Provider延迟较高

前提：

> 不破坏核心架构假设。

---

# 26. Blocking FAIL

以下任一问题持续存在，即不能结束技术验证阶段：

### F-01

无法可靠获得结构化角色输出。

### F-02

无法阻止角色读取未授权剧情信息。

### F-03

DeepSeek视觉限制只能靠Prompt碰运气。

### F-04

角色Memory无法隔离。

### F-05

自然语言无法可靠触发最小Narrative Signal。

### F-06

LLM生成与确定性Game State无法安全解耦。

### F-07

State无法稳定恢复。

### F-08

单次模型失败会破坏整个Session。

---

# 27. 失败归因规则

出现问题时首先定位：

```text id="slz0oh"
表现错误
→ Frontend

调用错误
→ Provider / API

格式错误
→ Character Response / Validation

Persona错误
→ Character Runtime

角色知道不该知道的信息
→ Context / Knowledge / Memory Scope

剧情错误推进
→ Narrative Runtime

状态丢失
→ Session / Persistence

旧信息无法正确使用
→ Memory
```

避免：

> 一个问题出现后同时修改五层系统。

---

# 28. 验证中允许Mock

当前阶段允许使用：

- Mock Character Response
- Mock Narrative Event
- 临时Scene
- 临时角色立绘
- 临时Background
- POC Fact
- POC Flag

只要明确：

# Fixture ≠ Production Content

---

# 29. 不允许Mock掉的核心风险

最终技术验证前不能持续Mock：

- DeepSeek真实生成链路
- Claude真实生成链路
- Structured Response Validation
- Character Context Isolation
- Narrative Event State Commit
- Memory Isolation
- Session Restore

否则无法证明核心技术成立。

---

# 30. 每项验证的最小记录格式

每完成一个TV，应记录：

```text id="a6fl9j"
## TV-ID

Status:
PASS / FAIL / ...

Date:

Environment:

Goal:

Test Cases:

Observed Result:

Failures:

Known Limitations:

Evidence:

Conclusion:
```

可以直接附在开发记录或测试结果中。

不需要将大量实验日志写入本文件。

---

# 31. 本文件不保存动态进度

为了保持本文档稳定：

> **TV状态的实时变化不直接反复修改本文件主体。**

本文件定义的是：

- 验证计划
- PASS标准

实际执行记录应放在独立：

```text id="o84o27"
validation-results/
```

或其他明确实验记录位置。

避免本文件同时承担：

> 规范 + 日志

两个职责。

---

# 32. 推荐验证结果目录

允许建立：

```text id="lh451w"
validation-results/

├── TV-01/
├── TV-02/
├── ...
└── TV-16/
```

每项只保存必要证据。

这属于实验产物目录：

> 不属于 `/docs` 核心真相源。

---

# 33. 进入正式开发的Gate

只有：

```text id="jsed7z"
TV-01 ~ TV-16
```

全部达到：

```text id="df5b1q"
PASS
```

或：

```text id="g56wci"
PASS_WITH_LIMITATION
```

并且不存在Blocking FAIL，

才可以宣布：

# Lightweight Technical Validation PASS

---

# 34. 通过后可以开始的工作

完成本阶段后，才进入：

# 正式MVP内容开发

包括：

- 完整Scene设计
- 正式主线
- ChatGPT接入
- 豆包Script
- 正式Fact Registry
- 正式Narrative Events
- 完整角色关系
- 更完整Memory
- 高级视觉效果

具体下一阶段Scope需重新定义。

---

# 35. 当前阶段禁止提前扩展

在核心验证未通过前，不得因为“以后会需要”主动加入：

- pgvector复杂检索
- Reranker
- Knowledge Graph
- Redis
- Kafka
- Kubernetes
- 多Agent自主规划
- Voice
- Live2D
- UI Shatter完整特效
- 五场景正式内容
- 全部Ending
- 完整ChatGPT病娇状态机
- 豆包完整剧本库

---

# 36. 停止条件

如果出现以下情况：

> 当前核心架构假设经多次最小验证仍然失败，

例如：

- Character Knowledge无法可靠隔离
- Structured Output路线无法稳定工作
- 当前Narrative Interpreter方案准确性明显不足

则：

# Stop and Re-evaluate

不要继续堆功能绕过问题。

需要回到对应文档重新评估设计。

---

# 37. Agent执行原则

Agent每次接到开发任务时应先判断：

```text id="b3ayfu"
当前正在做哪个TV？
```

然后只读取：

### 必须

本TV相关文档。

### 必要时

相关实现代码。

避免每次把：

- 全部Project文档
- 全部剧情
- 全部角色
- 全部历史实验

同时注入上下文。

---

# 38. Agent最小文档读取建议

例如：

### 做TV-01

主要读取：

```text id="llbxx2"
01-mvp-requirements.md
02-system-architecture.md
06-tech-validation-plan.md
```

无需读取完整Memory设计。

---

### 做TV-08 DeepSeek Blindness

读取：

```text id="ws8bci"
04-character-runtime.md
05-memory-design.md
06-tech-validation-plan.md
```

必要时补：

```text id="pg94yp"
03-narrative-runtime.md
```

---

### 做TV-11 Narrative Event

读取：

```text id="etutxu"
03-narrative-runtime.md
06-tech-validation-plan.md
```

以及对应架构代码。

---

### 做TV-13 Important Memory

读取：

```text id="hfd63y"
04-character-runtime.md
05-memory-design.md
06-tech-validation-plan.md
```

这样减少无关上下文污染。

---

# 39. 技术验证阶段最终输出

本阶段结束时应至少能够提供：

```text id="a5gokf"
1. 可运行Vertical Slice

2. Docker化运行环境

3. TV-01 ~ TV-16验证结果

4. 关键失败案例

5. 已知技术限制

6. 是否进入正式开发的结论
```

---

# 40. 最终判定

最终只允许：

```text id="lnmw8z"
GO
```

或：

```text id="qgcnqh"
NO-GO
```

---

## GO

核心技术闭环成立。

可以进入完整MVP开发。

---

## NO-GO

存在至少一个Blocking技术风险尚未解决。

此时继续增加剧情、美术或功能：

> 不视为项目取得有效进展。

---

# 41. Agent最小上下文摘要

当Agent只需要执行当前技术验证任务时，可使用：

```text id="oacgyd"
当前阶段：
轻量技术验证。

原则：
先验证核心技术风险，
不做完整游戏。

执行顺序：

TV-01 Gal UI
TV-02 基础动画
TV-03 前后端Round Trip
TV-04 DeepSeek生成
TV-05 Structured Response
TV-06 Validate Before Present
TV-07 Short-term Context
TV-08 DeepSeek Blindness
TV-09 Claude + Character Isolation
TV-10 Narrative Signal
TV-11 Deterministic Event
TV-12 State-dependent Response
TV-13 Important Memory
TV-14 Session Restore
TV-15 Failure Recovery
TV-16 End-to-End Stability

关键原则：

- 上游未PASS，不进入依赖验证。
- 一次成功不等于PASS。
- 每项保留可复现证据。
- Fixture可以临时，核心风险不能长期Mock。
- FAIL首先定位负责模块，不跨层乱改。
- 未验证完核心闭环前，不加RAG/K8s/Voice/Live2D/高级特效等扩展。

最终Gate：
20轮以上完整可玩Session，
至少3个独立Session验证，
不存在Blocking问题。

全部核心TV通过：
GO → 正式MVP开发。

存在Blocking风险：
NO-GO → 先解决架构问题。
```