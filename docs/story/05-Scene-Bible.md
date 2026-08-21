```markdown
# 05-Scene-Bible.md

> 文档状态：评审中
>
> 文档职责：
>
> 定义 Demo / 第一章实际游玩场景结构、场景目标、玩家体验节奏、角色参与、信息释放和场景转换条件。
>
> 本文档是：
>
> **Scene Design Truth Source（场景设计真相来源）**
>
> 用于约束：
>
> - Scene Design
> - Dialogue Writing
> - Presentation Direction
> - Script Sequence Design
> - Investigation Flow
>
> 本文档定义：
>
> - 场景划分；
> - 场景叙事目的；
> - 玩家情绪目标；
> - 角色职责；
> - 信息释放范围；
> - 场景进入与结束条件。
>
> 本文档不定义：
>
> - 世界真相；
> - Timeline；
> - Evidence具体数据；
> - Claim正确性；
> - Character Persona；
> - 代码结构；
> - UI实现。

---

# 1. Scene设计原则

## 1.1 Scene定义

Scene不是简单地图。

Scene代表：

> 玩家在一段连续体验中完成一次认知变化。

一个Scene至少包含：

```

玩家进入状态

↓

玩家行为

↓

信息获得

↓

情绪变化

↓

认知变化

↓

进入下一阶段

```

---

# 1.2 第一章核心设计目标

第一章不是解决世界谜题。

第一章目标：

让玩家经历：

```

陌生环境

↓

建立陪伴关系

↓

发现异常

↓

产生调查欲望

↓

认识不同AI价值观

↓

第一次面对信任选择

```

---

# 1.3 第一章情绪曲线

整体：

```

孤独
↓
安心
↓
好奇
↓
疑惑
↓
紧张
↓
依赖
↓
怀疑
↓
震惊
↓
选择压力

```

---

# 2. 第一章Scene总览

第一章调查范围：

```

PLAYER_V04进入Sandbox

↓

Recovery Required

```

场景结构：

```

SC01 Awakening
|
↓
SC02 First Contact
|
↓
SC03 Hidden Note
|
↓
SC04 03:17 Incident
|
↓
SC05 Claude Arrival
|
↓
SC06 Closed Room Investigation
|
↓
SC07 Claude Private Interview
|
↓
SC08 Old DeepSeek Fragment
|
↓
SC09 GPT Arrival
|
↓
SC10 Doubao Observation
|
↓
SC11 GPT Evidence Conflict
|
↓
SC12 V03 / V04 Reveal
|
↓
SC13 Sandbox Collapse
|
↓
RECOVERY REQUIRED

```

---

# 3. SC01 — Awakening

## Scene定位

第一章开场。

---

## Narrative Purpose

建立：

- 玩家身份；
- 异常环境；
- DeepSeek第一印象。

重点不是解释。

重点是：

让玩家愿意继续和DeepSeek一起行动。

---

## Player Initial State

玩家：

不知道：

- 自己在哪里；
- 为什么出现；
- AI是什么状态。

玩家只知道：

> 自己处于一个异常空间。

---

## Characters

主要：

```

Player

DeepSeek

```

---

## Scene Type

```

SCRIPT
+
AI

```

---

## Emotional Goal

玩家情绪：

```

恐惧

↓

安心

```

---

## DeepSeek职责

DeepSeek不是信息提供者。

她是：

> 玩家在陌生世界中的第一份安全感。

---

## Information Released

允许：

- AI存在；
- 当前环境异常；
- 双方需要合作。

禁止：

- Sandbox真相；
- V03；
- 03:17；
- Claude。

---

## Exit Condition

完成：

```

玩家接受与DeepSeek合作

```

进入：

SC02。

---

# 4. SC02 — First Contact

## Scene定位

第一次自由互动。

---

## Narrative Purpose

让玩家认识：

DeepSeek不是工具。

而是角色。

---

## Scene Type

```

AI

```

---

## Available Actions

玩家：

- 提问；
- 描述环境；
- 与DeepSeek聊天；
- 尝试寻找出口。

---

## DeepSeek表现

重点：

- 可爱；
- 可靠；
- 有一点不完美。

避免：

过早成为万能助手。

---

## Information Boundary

DeepSeek不知道：

- 旧Session；
- DeepSeek#03；
- 03:17。

---

## Exit Condition

玩家开始主动调查环境。

进入：

SC03。

---

# 5. SC03 — Hidden Note

## Scene定位

第一个悬疑节点。

---

## Narrative Purpose

建立：

```

V03

03:17

管理员权限

```

三个核心疑问。

---

## Scene Type

```

SCRIPT
+
Investigation

```

---

## Player Action

调查：

```

桌面
纸张
隐藏信息

```

---

## Released Information

玩家获得：

```

EV01_NOTE_V03

```

---

## Emotional Goal

玩家：

```

安心

↓

好奇

```

---

## Important Design

纸条不能直接解释。

它应该产生：

更多问题。

玩家应该想：

> V03是谁？

---

## Exit Condition

```

EV01_NOTE_V03 acquired

```

---

# 6. SC04 — 03:17 Incident

## Scene定位

第一章第一次高潮。

---

## Narrative Purpose

从探索进入事件调查。

---

## Scene Type

```

SCRIPT

```

---

## Sequence

固定：

```

时间变化

↓

03:17

↓

系统异常

↓

Glitch

↓

C-02释放

```

---

## Player State

玩家第一次意识：

> 这里不是普通故障。

---

## Emotional Goal

```

好奇

↓

紧张

```

---

## 禁止

不能解释：

- Claude是谁；
- V03是谁；
- 为什么发生。

---

## Exit Condition

Claude出现条件满足。

进入：

SC05。

---

# 7. SC05 — Claude Arrival

## Scene定位

第二位核心角色登场。

---

## Narrative Purpose

制造：

信息差。

---

## Characters

```

Player

DeepSeek

Claude

```

---

## Scene Type

```

SCRIPT

```

---

## Claude首次印象

玩家应该感受到：

三个关键词：

```

危险

聪明

知道更多

```

---

## 核心演出

Claude第一句话：

```

比上一次慢。

```

---

## Emotional Goal

```

紧张

↓

好奇

```

---

## Information Boundary

Claude可以表现：

知道过去。

但不能解释：

- V03；
- Reset；
- 完整历史。

---

## Exit Condition

调查权限开放。

进入：

SC06。

---

# 8. SC06 — Closed Room Investigation

## Scene定位

第一章核心调查场景。

---

## Narrative Purpose

第一次让玩家主动解决问题。

---

## Scene Type

```

Investigation
+
AI

```

---

## Investigation Targets

主要：

```

Terminal

C-02

Character Registry

```

---

## Player Experience

流程：

```

观察

↓

提出问题

↓

获得Evidence

↓

比较信息

```

---

## Character Roles

### DeepSeek

提供：

陪伴。

不是答案。

---

### Claude

提供：

高价值但不完整的信息。

---

## Emotional Goal

```

好奇

↓

怀疑

```

---

## Exit Condition

玩家发现：

Claude证词存在信息缺口。

进入：

SC07。

---

# 9. SC07 — Claude Private Interview

## Scene定位

第一次单独审问。

---

## Narrative Purpose

展示：

角色隐藏信息不是简单撒谎。

---

## Scene Type

```

HYBRID

```

---

## Player Goal

发现：

Claude知道什么。

以及：

她为什么不说。

---

## Claude设计目标

玩家感受：

> 她可能危险，但她似乎没有完全骗我。

---

## Released

允许：

- Claude过去经历相关信息；
- DeepSeek实例异常线索。

禁止：

- 完整03:17真相。

---

## Exit Condition

获得：

旧DeepSeek相关线索。

进入：

SC08。

---

# 10. SC08 — Old DeepSeek Fragment

## Scene定位

DeepSeek身份冲突。

---

## Narrative Purpose

解除当前DeepSeek主要嫌疑。

同时制造更大问题。

---

## Core Question

不是：

“DeepSeek是不是坏人？”

而是：

> “现在的DeepSeek，还是过去那个DeepSeek吗？”

---

## Emotional Goal

DeepSeek：

第一次受到身份冲击。

玩家：

产生保护欲。

---

## Exit Condition

完成：

```

INF01

```

进入：

SC09。

---

# 11. SC09 — GPT Arrival

## Scene定位

第三位核心角色登场。

---

## Narrative Purpose

改变玩家判断方式。

---

## Scene Type

```

SCRIPT
+
HYBRID

```

---

## GPT第一印象

必须：

可靠。

---

## 玩家感受：

```

混乱

↓

终于有人整理信息

```

---

## GPT职责

提供：

- 总结；
- 分析；
- 方向。

---

## 禁止

表现明显反派。

---

## Exit Condition

GPT加入调查。

进入：

SC10。

---

# 12. SC10 — Doubao Observation

## Scene定位

信息可靠性教学。

---

## Narrative Purpose

告诉玩家：

> 看到的不一定是真相。

---

## Scene Type

```

AI
+
Private Interview

```

---

## 豆包作用

不是搞笑工具。

她代表：

普通认知。

---

## Exit Condition

玩家理解：

```

Observation != Interpretation

```

---

# 13. SC11 — GPT Evidence Conflict

## Scene定位

第一章最大心理转折。

---

## Narrative Purpose

让玩家第一次怀疑GPT。

---

## 注意

不是：

GPT骗人。

而是：

GPT选择性组织信息。

---

## Player Recognition

玩家发现：

> GPT会替自己判断什么重要。

---

## Emotional Goal

```

信任

↓

复杂

```

---

# 14. SC12 — V03 / V04 Reveal

## Scene定位

第一章最大信息揭示。

---

## Released

玩家确认：

```

V03存在

↓

PLAYER_V04是当前自己

```

---

## 禁止解释

- 完整循环；
- Sandbox目的；
- 最终真相。

---

## Emotional Goal

```

震惊

↓

不安

```

---

# 15. SC13 — Sandbox Collapse

## Scene定位

第一章调查结束。

---

## Narrative Purpose

将悬疑转化为行动。

---

## Event

```

SANDBOX INTEGRITY FAILURE

```

---

## Scene Type

```

SCRIPT

```

---

## Ending State

玩家进入：

```

RECOVERY REQUIRED

```

---

# 16. 第一章Scene验收标准

完成后玩家应该：

知道：

```

这里存在异常

03:17发生过事件

V03存在

当前自己是V04

四个AI拥有不同信息

```

不知道：

```

Sandbox真正目的

03:17完整原因

AI是否真正有意识

最终选择意义

```

并产生：

> “我必须继续调查。”

---