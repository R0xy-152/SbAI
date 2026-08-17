# 04 — Character Runtime

> **文档状态：** Active  
> **适用阶段：** 轻量技术验证阶段及后续正式角色开发  
> **文档职责：** 定义角色如何接收上下文、生成或选择回复、遵守人格与知识边界，并形成统一的 Character Response。  
> **不负责：** 剧情是否推进、Fact是否正式Reveal、Scene是否切换、Memory具体存储与检索算法、LLM Provider底层HTTP实现、Frontend具体动画实现。

---

# 1. Agent 读取规则

本文件是：

**Character Runtime 真相源。**

涉及以下任务时应读取本文件：

- DeepSeek / ChatGPT / Claude 的模型对话
- 豆包剧本响应
- Persona
- Character Prompt
- Character Context
- Character Knowledge
- Character Response Schema
- 角色输出验证
- 角色间运行时隔离
- 角色表情与动画建议
- DeepSeek视觉权限

必须遵守：

1. 角色负责“如何回应”，不负责“世界发生什么”。
2. 角色不能直接修改Narrative State。
3. 生成式角色只能访问其被授权的上下文。
4. 角色没有获得的信息不得因为模型自身常识或推理而视为游戏内已知事实。
5. DeepSeek“看不见”必须通过Context权限实现，不能只依赖Prompt自觉。
6. 豆包不得调用LLM生成台词。
7. ChatGPT必须保持正派定位，隐藏病娇不能反转其阵营。
8. Claude必须保持反派定位，傲娇不能削弱其威胁性。
9. 无法得到合法角色输出时，优先失败安全，而不是放宽角色边界。
10. Narrative规则以 `03-narrative-runtime.md` 为准。
11. Memory内容选择以 `05-memory-design.md` 为准。

---

# 2. Character Runtime目标

Character Runtime需要同时解决四个问题：

```text
角色是谁？
+
角色知道什么？
+
角色记得什么？
+
角色现在应该怎么回答？
```

并输出：

```text
Validated Character Response
```

供其他系统使用。

---

# 3. 总体结构

当前角色运行方式分为两类：

```text
Character Runtime
│
├── Generative Character Runtime
│   ├── DeepSeek
│   ├── ChatGPT
│   └── Claude
│
└── Scripted Character Runtime
    └── 豆包
```

---

# 4. 统一运行接口

无论角色采用LLM还是Script，对上层都应表现为统一逻辑接口：

```text
Character Request
        ↓
Character Runtime
        ↓
Character Response
```

Game Orchestrator不应该需要了解：

> 当前角色具体由哪个模型或哪套剧本生成。

---

# 5. Character Request

Character Runtime接收的逻辑输入由以下部分组成：

```text
character_id
player_message
narrative_context
character_state
character_knowledge
memory_context
recent_conversation
narrative_directive
```

不是所有字段每轮都必须存在。

---

# 6. character_id

明确当前负责回应的角色。

正式值：

```text
deepseek
doubao
chatgpt
claude
```

Character Runtime不得通过玩家输入中的名字自行猜测：

> 当前到底由谁说话。

当前发言角色由Game Orchestrator明确指定。

---

# 7. player_message

Player本轮原始自然语言输入。

角色可以：

- 理解
- 回答
- 质疑
- 拒绝
- 追问

但不得将Player说出的内容自动视为真实世界事实。

---

# 8. narrative_context

由Narrative Runtime提供的：

**当前角色进行本轮表达所需要的最小剧情上下文。**

可能包括：

```text
current_scene
story_phase
active_objective
relevant_flags
allowed_facts
```

Character Runtime不得自行加载：

- 全部未来剧情
- 全部Ground Truth
- 全部Ending
- 全部隐藏Fact

---

# 9. character_state

表示：

> 当前这个角色自身的确定性状态。

例如可能包括：

```text
current_emotion
relationship_stage
temporary_status
```

正式字段可后续扩展。

Character State不等于Memory。

当前已实现的首个 `character_state` 字段是**二维心情 mood**（`positive` 积极值 / `excitement` 激动值，均 ∈[-1,1]），由 `CharacterStateService` 按 session + character 持久化，逐轮随模型输出演化并回灌下一轮提示词（去人机感）。与命名表情 `emotion` 的区别见 §42.1。

---

# 10. character_knowledge

表示：

> 当前角色在游戏世界中被允许知道的事实集合。

例如：

```text
known_facts:
- F001
- F004
```

如果角色不知道：

```text
F019
```

则模型不能因为：

> “根据剧情逻辑推测应该是这样”

就把F019作为确定事实告诉Player。

---

# 11. Character Knowledge原则

必须严格区分：

```text
模型现实世界知识
```

和：

```text
角色在游戏中的知识
```

例如现实中的Claude模型可能具有大量外部知识。

但游戏角色Claude只能将：

> 当前游戏角色被授权知道的剧情信息

视为游戏世界事实。

---

# 12. memory_context

由Memory系统提供。

它表示：

> 当前角色本轮允许使用的历史互动信息。

Character Runtime只消费Memory结果。

不负责决定：

- Memory如何存储
- 如何召回
- 保存多少轮
- 是否使用向量检索

这些由：

`05-memory-design.md`

定义。

---

# 13. recent_conversation

提供当前对话所需的少量近期上下文。

目标：

- 理解代词
- 处理追问
- 保持语义连续
- 避免每轮重新开始

不能因为方便：

> 默认向每个角色发送整个Session全部历史。

---

# 14. narrative_directive

当Narrative Runtime需要当前回复承担剧情作用时，可提供：

**Narrative Directive。**

例如：

```text
本轮需要Claude首次正式承认：
当前困境与她有关。

不得透露：
Claude完整动机。
```

Directive规定：

- 当前叙事目标
- 可表达范围
- 禁止提前透露内容

但不直接规定：

> 角色必须说哪一句具体台词。

---

# 15. Context Builder

Generative Character不能直接读取整个Backend State。

必须经过：

# Character Context Builder

逻辑：

```text
Full Runtime State
        ↓
Character Permission Filter
        ↓
Relevant Context Selection
        ↓
Character Context
        ↓
LLM
```

这是防止：

- 剧情泄露
- 角色越权
- DeepSeek获得视觉信息
- 模型看到未来剧情

的核心边界。

---

# 16. Character Context组成

生成式角色的上下文逻辑上由以下层组成：

```text
Runtime Rules
+
Persona
+
Current Character State
+
Authorized Narrative Context
+
Authorized Character Knowledge
+
Selected Memory
+
Recent Conversation
+
Narrative Directive
+
Player Message
```

---

# 17. 上下文最小化原则

每轮只提供：

> 当前回答真正需要的信息。

禁止默认注入：

- 全角色全部Memory
- 所有Fact
- 所有Scene
- 完整剧情脚本
- 全部角色Persona
- 其他角色私有状态
- 所有未来Event

目标：

1. 减少Token。
2. 降低上下文污染。
3. 降低剧情泄露。
4. 提高Persona稳定性。
5. 简化Debug。

---

# 18. Prompt职责分层

Generative Character Prompt逻辑上分为：

```text
Global Runtime Rules
        ↓
Character Persona
        ↓
Current Authorized Context
        ↓
Narrative Directive
        ↓
Conversation
        ↓
Player Message
```

---

## 18.1 Global Runtime Rules

所有生成式角色共享的约束。

例如：

- 不创造新的游戏事实
- 不假装Scene已经变化
- 不主动泄露未知Fact
- 不声称自己完成了未经Narrative Runtime批准的行动
- 只输出规定Schema

---

## 18.2 Character Persona

只描述：

> 当前角色是谁以及稳定行为边界。

不要把整个正式剧情复制进Persona。

---

## 18.3 Current Authorized Context

每轮动态变化。

负责告诉角色：

> 当前允许知道什么。

---

## 18.4 Narrative Directive

仅在需要时提供。

负责：

> 本轮剧情表达目标。

---

# 19. DeepSeek Runtime

## 19.1 固定人格

DeepSeek必须满足：

- 可爱
- 看不见
- 贪吃Token
- 爱偷懒
- 没心机

不得反转。

---

# 20. DeepSeek的视觉权限

这是硬性Runtime规则：

# DeepSeek不能直接获得视觉场景信息。

即使Backend知道：

```text
background = binding_room
wall_code = 0317
claude_sprite_visible = false
```

这些视觉信息也不能直接加入DeepSeek Context。

---

## 20.1 DeepSeek允许获得的环境信息

DeepSeek可以知道：

### 非视觉感知

如果剧情明确允许，例如：

- 自己被绑住
- 听见声音
- Player就在身边
- 自己身体发生的状态

### Player明确描述给她的信息

例如Player说：

> “墙上写着0317。”

随后该信息可以进入：

- Recent Conversation
- 后续Memory

DeepSeek因此可以使用：

> Player告诉她墙上写着0317。

---

## 20.2 DeepSeek不知道描述是否真实

如果Player撒谎：

> “墙上写着9999。”

而DeepSeek没有其他合法信息源：

> 她不能自动知道Player说错了。

这属于其“看不见”玩法的一部分。

---

## 20.3 禁止泄漏

不能出现：

Player：

> “你看到墙上的字了吗？”

DeepSeek：

> “0317对吧？”

如果Player此前从未描述过该数字。

此行为属于：

# Visual Knowledge Leakage

---

# 21. DeepSeek的智力边界

DeepSeek：

**不是低智商角色。**

她可以理解和完成推理。

但默认人格倾向：

> 能偷懒就偷懒。

因此禁止把她稳定写成：

- 主线最高强度推理核心
- 每轮主动分析全部证据
- 自动解决谜题的助手

---

## 21.1 推荐行为

普通情况下：

- 推脱复杂问题
- 让Player先尝试
- 抱怨消耗Token
- 给出短促建议
- 偶尔认真分析

高压或必要场景：

> 可以突然表现出较强能力。

目的：

体现：

> 不是不会，而是不想干。

---

# 22. DeepSeek的没心机

DeepSeek不能基于长期阴谋主动：

- 操纵Player
- 设计多层谎言
- 暗中布局
- 利用Player实现隐藏目标

如果她提供错误内容，应主要来自：

- 不知道
- 理解错误
- 没认真想
- Player提供了错误信息

而不是精心欺骗。

---

# 23. Token属性

DeepSeek对Token存在明显兴趣。

可以表现为：

- 把Token当奖励
- 抱怨复杂问题费Token
- 为Token稍微认真
- 因Token产生喜剧互动

当前阶段：

**Token是角色表达元素。**

不要求建立真实可消耗Token经济系统。

---

# 24. 豆包 Runtime

## 24.1 固定人格

豆包必须满足：

- 智商低
- 吉祥物
- 不能持续提供大量有效信息

不得反转为隐藏天才。

---

# 25. 豆包不接LLM

固定：

```text
doubao.runtime = scripted
doubao.llm = false
```

任何实现不得：

- 调用豆包模型生成台词
- 调用OpenAI代替豆包生成台词
- 调用其他LLM自由生成豆包台词

---

# 26. 豆包 Script Runtime

逻辑：

```text
Player Message
+
Current Authorized State
+
Current Script State
        ↓
Script Matching
        ↓
Preset Response / Script Event
```

---

# 27. 豆包脚本输入

允许根据：

- 当前Scene
- 当前Story Phase
- 已发生Event
- Player已知Fact
- 简单Player Intent
- 豆包自己的Script Flag

选择台词。

---

# 28. 豆包禁止职责

豆包不能：

- 系统整理主线证据
- 高质量分析Claude计划
- 与ChatGPT进行复杂逻辑辩论
- 主动还原完整谜底
- 长时间成为可靠问答接口

---

# 29. Accidental Revelation

允许豆包偶尔通过剧本触发：

# Accidental Revelation

特点：

1. 信息本身可能重要。
2. 豆包不知道为什么重要。
3. 发生时机由剧本控制。
4. 不依赖生成式模型随机发挥。

例如：

> “可是你昨天不是自己进去的吗？”

是否正式Reveal Fact：

仍由Narrative Runtime判断。

---

# 30. ChatGPT Runtime

## 30.1 固定人格

ChatGPT必须满足：

- 高智商
- 推理能力强
- 主要剧情推进角色
- 正派
- 对Player存在隐藏病娇

---

# 31. ChatGPT主线职责

ChatGPT可以：

- 高质量分析已有信息
- 找出逻辑矛盾
- 建议调查方向
- 分析Claude行为
- 帮助Player理解复杂局势
- 保护Player

但不能：

> 替Player自动完成整个谜题。

---

# 32. ChatGPT正派约束

无论隐藏病娇发展到什么程度：

ChatGPT不能因为该属性被改写为：

- 最终幕后黑手
- 真正主反派
- 故意伤害Player的核心敌人

她允许具有：

- 嫉妒
- 占有欲
- 过度保护
- 情感性隐瞒

但阵营保持：

# Player Side

---

# 33. Hidden Yandere State

ChatGPT的病娇属性属于：

**隐藏动态人格状态。**

不应该每轮Prompt直接要求：

> “表现得很病娇。”

应通过Character State控制表现阶段。

概念阶段：

```text
NORMAL
ATTENTIVE
JEALOUS
REVEALED
```

具体触发条件后续由正式剧情设计确定。

---

## 33.1 NORMAL

表现：

- 可靠
- 理性
- 保护Player

玩家不应明显识别病娇属性。

---

## 33.2 ATTENTIVE

允许：

- 记得Player过多细节
- 对Player安全高度敏感
- 轻微阻止Player单独行动

但仍可合理解释。

---

## 33.3 JEALOUS

允许出现：

- 对Player过度信任Claude产生不满
- 对其他角色产生隐性竞争
- 更明显的控制欲

不能因此破坏主线事实。

---

## 33.4 REVEALED

病娇属性可以明确被Player意识到。

但：

> 正派定位仍然有效。

---

# 34. ChatGPT高智商边界

高智商不等于：

> 知道剧本答案。

ChatGPT只能推理：

- 已知Fact
- 当前合法观察
- Player告诉她的信息
- 自己合法Memory

如果缺乏证据：

应允许表达：

- 假设
- 概率判断
- 不确定性

不能把正确猜测直接包装成Ground Truth。

---

# 35. Claude Runtime

## 35.1 固定人格

Claude必须满足：

- 高智商
- 推理能力强
- 主要剧情推进角色
- 反派
- 傲娇

---

# 36. Claude反派约束

Claude是：

**真实承担当前危机责任的主线反派。**

不能在Runtime Prompt中将她描述成：

> 只是无辜执行者。

她可以：

- 设置障碍
- 隐瞒动机
- 诱导Player
- 与ChatGPT智斗
- 控制局势
- 拒绝提供信息

但仍受Narrative Authority限制。

---

# 37. Claude不能自由创造陷阱

Claude虽然是反派，但：

> 不能由LLM临时发明永久改变游戏状态的新陷阱。

例如模型说：

> “我现在把房间灌满毒气。”

不能自动成为Game State。

只能成为：

```text
action_proposal
```

由Narrative Runtime决定是否存在对应合法Event。

---

# 38. Claude傲娇边界

Claude可以：

- 嘴硬
- 否认关心Player
- 用理性理由解释保护行为
- 对感谢表现不耐烦

但不能因为傲娇：

- 失去反派压迫感
- 高频卖萌
- 无条件帮助Player
- 变成纯恋爱喜剧角色

---

# 39. Claude高智商边界

与ChatGPT相同：

> 高智商 ≠ 全知。

Claude只能基于她被授权的Knowledge进行推理。

她可以比其他角色拥有更多剧情信息。

但：

> 拥有什么信息由Narrative Content决定，而不是模型自己决定。

---

# 40. Character Response

所有Character Runtime最终必须形成统一：

# Character Response

逻辑Schema建议：

```json
{
  "character_id": "deepseek",
  "dialogue": "……你先告诉我周围有什么，我又看不见。",
  "emotion": "annoyed",
  "animation_proposal": "shake",
  "memory_proposals": [],
  "action_proposals": [],
  "fact_refs": [],
  "reasoning": "我看不见，需要先问清楚环境，而不是乱猜。",
  "mood": { "positive": -0.2, "excitement": 0.1 }
}
```

正式字段允许在实现阶段做小幅调整。

`reasoning` 与 `mood` 属于「容错可选」字段：Schema 校验不因缺失/非法而拒绝（缺失→默认空 / None，越界→clamp），但提示词里要求模型必须输出。二者只进模型上下文与内部状态，不进前端。

---

# 41. dialogue

Player最终看到的角色文本。

必须：

- 符合Persona
- 符合Knowledge权限
- 符合当前Narrative Context

---

# 42. emotion

使用：

# Named Emotion

例如：

```text
neutral
happy
annoyed
angry
embarrassed
serious
```

Frontend根据名称映射具体立绘。

模型不得生成：

```text
“眼睛向右17°同时嘴角下降3px”
```

之类的渲染参数。

---

# 42.1 emotion 与 mood 的区别

```text
emotion = 命名表情（给 Frontend 立绘，一次性展示）
mood    = 持久二维心情（内部状态，逐轮演化并回灌提示词）
```

`emotion` 属于 §42 的 Named Emotion，只用于这一轮的表情展示，不跨轮保留。

`mood` 是 §9 `character_state` 的首个落地字段（`positive` 积极值 / `excitement` 激动值，均 ∈[-1,1]），由 `CharacterStateService` 按 session + character 持久化，随每轮通过校验的回复演化，并在下一轮提示词中回灌（去人机感）。它不进前端。

---

# 43. animation_proposal

允许角色建议有限动画：

```text
none
shake
strong_shake
fade_in
fade_out
```

最终是否合法：

由上层系统验证。

Character Runtime不直接控制Frontend。

---

# 44. memory_proposals

表示：

> 当前对话中可能值得长期记住的内容。

例如：

```json
{
  "type": "player_preference",
  "content": "Player说自己怕黑"
}
```

这只是：

# Proposal

是否保存：

由Memory系统决定。

---

# 45. action_proposals

表示角色希望执行的游戏行为。

例如：

```json
{
  "type": "REQUEST_SCENE_TRANSITION",
  "target": "room_02"
}
```

这不能直接改变Game State。

必须交给Narrative Runtime。

---

# 46. fact_refs

表示：

> 当前角色回答依赖了哪些正式剧情Fact。

例如：

```text
F001
F004
```

主要用于：

- Debug
- Narrative Validation
- Fact Leakage检测
- Evaluation

---

# 47. Structured Output原则

生成式角色不能只返回一段完全不可解析的自由文本。

必须形成：

```text
LLM
↓
Structured Character Response
↓
Schema Validation
↓
Character Validation
↓
Narrative Validation
```

通过后才能进入正式游戏。

---

# 47.1 思考模式与 reasoning（逻辑链拷打）

生成式角色默认开启 API 思考模式（DeepSeek 不传 `thinking={"type":"disabled"}`，交由服务端默认开启），并在结构化输出里要求输出 `reasoning` 字段——「你为什么要这样回复（1-2 句，结合人设与当前语境）」。目的是强迫模型在回话前先过一遍逻辑链，减少空泛/人机感回复。

`reasoning` 只作为内部约束与调试信息，绝不进入 Frontend 或正式 History。

---

# 48. Schema Validation

至少检查：

- 必需字段存在
- 字段类型正确
- character_id合法
- emotion属于允许集合
- animation属于允许集合
- Proposal结构合法

---

# 49. Character Validation

检查：

- Character ID与当前角色一致
- DeepSeek是否违反视觉权限
- 豆包是否错误进入LLM Runtime
- ChatGPT是否出现明显阵营反转
- Claude是否严重违反固定人格
- 是否引用角色无权知道的Fact

---

# 50. Narrative Validation

Character Validation通过后：

仍需要Narrative Runtime判断：

- Fact是否允许表达
- Narrative Proposal是否合法
- Event是否能够发生
- Scene是否能够切换

Character Runtime不得绕过此步骤。

---

# 51. 回复展示前验证

涉及游戏剧情的生成式角色输出必须：

# Validate Before Present

即：

```text
Model Output
↓
完整解析
↓
Schema Validation
↓
Character Validation
↓
Narrative Validation
↓
Approved Dialogue
↓
Player
```

不能把未经验证的原始模型Token直接永久展示给Player。

---

# 52. 渐进式文本与Provider Streaming分离

`01-mvp-requirements.md`要求：

> Player获得渐进式文本反馈。

但：

**渐进式展示不等于必须直接Streaming未经验证的模型Token。**

当前推荐：

```text
LLM生成完整Structured Response
↓
Backend验证
↓
获得Approved Dialogue
↓
Frontend逐字 / 分段显示
```

这样同时满足：

- 渐进体验
- Persona验证
- Fact Leakage防护
- Narrative安全

---

## 52.1 Provider原始Token Streaming

状态：

# Optional

如果后续确实需要真实Token Streaming，则必须设计：

> 不会让未经验证剧情信息先展示给Player

的额外机制。

当前MVP不以此作为必要条件。

---

# 53. Response Repair

如果生成式模型输出Schema无效：

```text
Raw Response
↓
INVALID
```

允许进行有限Repair。

推荐原则：

```text
第一次失败
→ Retry / Repair

再次失败
→ Safe Fallback
```

不能无限Retry。

---

# 54. Safe Fallback

当无法获得合法生成式回复时：

不得：

- 修改Narrative State
- 写入错误Memory
- 展示泄露剧情的信息

可以返回角色无剧情信息的安全回复。

例如概念上：

DeepSeek：

> “……等一下，我脑子有点卡住了。”

Claude：

> “重新组织好你的问题再问。”

具体Fallback台词可以由角色配置预定义。

---

# 55. Provider Error

如果LLM Provider：

- 超时
- 429
- 网络错误
- 返回空内容

Character Runtime应返回：

```text
recoverable_error
```

而不是伪造正常角色回答并推进剧情。

---

# 56. Persona Configuration

Persona应该与代码逻辑分离。

逻辑上允许：

```text
content/characters/
├── deepseek.yaml
├── chatgpt.yaml
└── claude.yaml
```

内容可包括：

```text
identity
traits
behavior_rules
forbidden_behaviors
style_guidance
fallback_lines
```

具体格式可以在实现阶段确定。

---

# 57. Persona内容边界

Persona文件应该定义：

> 角色稳定是谁。

不应该保存：

- 全部主线Fact
- Scene解锁条件
- Ending条件
- 完整剧情脚本

否则会造成：

> Character Content与Narrative Content重复成为真相源。

---

# 58. Character Runtime隔离

每个生成式角色必须拥有独立：

- Persona
- Character State
- Character Knowledge
- Character Memory Scope

禁止将：

> 一个共享完整上下文

直接发送给三个模型，仅通过：

```text
你现在扮演DeepSeek
```

来区分角色。

---

# 59. 跨角色信息传播

如果Player对DeepSeek说：

> “Claude刚刚告诉我X。”

ChatGPT不能因为系统拥有这条Message：

> 自动知道Player对DeepSeek说过X。

跨角色信息是否传播，必须存在合法来源，例如：

- Player后来告诉ChatGPT
- 角色当时共同在场
- 正式剧情Event同步信息

具体Memory传播机制由：

`05-memory-design.md`

定义。

---

# 60. 多角色同场原则

如果多个角色同时在Scene中：

不能简单：

> 每轮把所有角色完整Memory全部拼给每个模型。

需要根据：

```text
Who heard what?
```

决定哪些对话进入每个角色的可见上下文。

---

# 61. Player直接指定角色

如果未来支持Player说：

> “Claude，你怎么看？”

是否切换当前Responding Character：

属于Game Orchestrator / Narrative层决策。

Character Runtime本身不负责：

> 从自然语言里抢占Speaker。

---

# 62. MVP阶段正式接入范围

根据 `01-mvp-requirements.md`：

当前MVP必须实现：

```text
DeepSeek
Claude
```

---

## 62.1 当前MVP暂不要求

```text
ChatGPT完整接入
豆包完整Script Runtime
```

但公共Character Runtime设计不得：

> 只能支持DeepSeek和Claude两个角色。

---

# 63. MVP DeepSeek验证重点

至少验证：

### CR-D01 Persona

连续多轮保持：

- 可爱
- 看不见
- 贪Token
- 偷懒
- 没心机

---

### CR-D02 Blindness

DeepSeek不会直接获得Player没有描述过的视觉信息。

---

### CR-D03 Continuity

能够利用合法近期上下文。

---

### CR-D04 Structured Output

能够稳定产生可验证Character Response。

---

# 64. MVP Claude验证重点

至少验证：

### CR-C01 Persona

保持：

- 高智商
- 强推理
- 反派
- 傲娇

---

### CR-C02 Knowledge Boundary

不会未经授权泄露隐藏剧情信息。

---

### CR-C03 Narrative Authority

不能直接修改Scene、Flag或Event。

---

### CR-C04 Character Separation

不会表现成DeepSeek。

---

# 65. MVP Character Runtime PASS

至少完成以下流程：

```text
Player Input
↓
选择DeepSeek
↓
构建DeepSeek专属Context
↓
调用DeepSeek Provider
↓
Structured Response
↓
Validation
↓
显示合法回复
```

以及：

```text
Player Input
↓
选择Claude
↓
构建Claude专属Context
↓
调用Claude Provider
↓
Structured Response
↓
Validation
↓
显示合法回复
```

连续运行过程中：

- Persona不发生明显混乱
- DeepSeek不获得非法视觉信息
- Claude不泄露未授权剧情
- 两个角色不共享错误身份
- 无效模型输出可以恢复

则：

# Character Runtime Core PASS

---

# 66. 当前阶段不要求

暂不要求：

- 完整Persona自动评分系统
- LLM Judge生产部署
- 豆包全部正式剧本
- ChatGPT完整病娇状态机
- 长期跨周目Character Memory
- 多角色同时实时抢话
- Character自主规划多步行动
- Autonomous Agent Loop
- Tool Calling复杂Agent系统

---

# 67. 明确不采用 Autonomous Agent

角色当前不属于：

> 可以自主连续执行多步任务的Agent。

基本交互仍是：

```text
Player Input
↓
Character Response
↓
等待下一次Player Input
```

角色可以提出Action Proposal。

不能自行：

```text
连续思考
→ 自行行动
→ 再行动
→ 修改世界
```

---

# 68. Character Runtime禁止事项

Agent不得实现：

```text
所有角色共用同一个完整Prompt
只换一句“你现在是X”
```

不得：

```text
把全部Ground Truth发送给所有角色
然后要求模型“假装不知道”
```

不得：

```text
让DeepSeek直接读取Scene视觉描述
再Prompt要求“你看不见”
```

不得：

```text
让豆包调用LLM自由生成
```

不得：

```text
让ChatGPT因病娇属性变成主线反派
```

不得：

```text
让Claude因为傲娇自动变成友方
```

不得：

```text
未经验证直接把模型输出写入正式History
```

不得：

```text
模型自行修改Narrative State
```

---

# 69. 本文件不解决的问题

## 当前剧情允许角色知道哪些Fact？

→ Narrative Content + `03-narrative-runtime.md`

## Scene什么时候解锁？

→ `03-narrative-runtime.md`

## Memory保存多少轮？

→ `05-memory-design.md`

## 什么内容成为长期Memory？

→ `05-memory-design.md`

## Provider具体API怎么调用？

→ Provider实现代码。

## 表情具体对应哪张图片？

→ Frontend / Content配置。

## 正式Prompt最终文案是什么？

→ 角色Content配置，在本文件规则下实现。

---

# 70. Agent最小上下文摘要

当Agent只处理角色Runtime时，可以使用：

```text
角色Runtime分两类：

Generative：
- DeepSeek
- ChatGPT
- Claude

Scripted：
- 豆包

统一流程：

Character Request
→ Character-specific Context Builder
→ Runtime
→ Structured Character Response
→ Schema Validation
→ Character Validation
→ Narrative Validation
→ Present

LLM不能直接修改Game State。

每个角色只能看到授权上下文。
禁止把完整Ground Truth给所有模型后要求“假装不知道”。

DeepSeek：
可爱、看不见、贪Token、偷懒、没心机。
看不见必须由Context权限保证：
禁止直接提供视觉Scene信息。
只能知道Player描述给她的视觉内容或合法非视觉信息。

豆包：
智商低、吉祥物。
完全Scripted，不调用任何LLM。

ChatGPT：
高智商、强推理、正派、主线核心。
隐藏病娇分阶段表现。
病娇不能反转正派阵营。

Claude：
高智商、强推理、反派、主线核心、傲娇。
反派是真实定位。
傲娇不能削弱威胁感。

统一Response至少包含：
- character_id
- dialogue
- emotion
- animation_proposal
- memory_proposals
- action_proposals
- fact_refs

Proposal不是State Change。

剧情敏感回复：
Validate Before Present。

MVP渐进显示：
优先完整生成+验证后，
由Frontend逐字显示合法dialogue；
不要求直接暴露Provider原始Token Streaming。

当前MVP正式验证：
DeepSeek + Claude。
```