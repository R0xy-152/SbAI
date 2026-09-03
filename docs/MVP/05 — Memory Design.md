# 05 — Memory Design

> **文档状态：** Active  
> **适用阶段：** 轻量技术验证阶段及后续正式角色开发  
> **文档职责：** 定义角色记忆的语义边界、上下文分层、可见性规则、记忆写入与读取原则。  
> **不负责：** Narrative State、Fact是否正式Reveal、角色Persona、LLM Provider实现、具体数据库表结构、向量检索算法细节、Frontend History展示。

---

# 1. Agent 读取规则

本文件是：

**Memory Design 真相源。**

涉及以下任务时应优先读取本文件：

- 对话上下文
- 角色记忆
- 历史消息
- 长期记忆
- Conversation Summary
- 跨角色信息传播
- 谁能听见哪句话
- 谁能记住Player说过什么
- Memory写入
- Memory读取
- pgvector / 语义检索是否需要加入

必须遵守：

1. Memory不是Narrative State。
2. Memory不是Ground Truth。
3. Memory记录“角色经历或被告知的内容”，不代表内容一定真实。
4. 不同角色拥有独立Memory Scope。
5. 不能因为Backend保存了某条消息，就默认所有角色都知道。
6. 角色只能读取自己有权限看到的历史。
7. DeepSeek不能通过Memory绕过“看不见”的限制。
8. Player说出的错误信息可以成为角色Memory，但不能成为Ground Truth。
9. 当前轻量验证阶段优先简单、可解释的Memory机制。
10. 不为了使用RAG而强行引入向量检索。
11. Narrative规则读取 `03-narrative-runtime.md`。
12. Character Knowledge规则读取 `04-character-runtime.md`。

---

# 2. Memory解决的问题

本系统不能只把最近一句Player输入交给角色。

角色需要能够表现出：

- 记得刚刚说过什么
- 理解连续追问
- 记得Player此前告诉过自己的信息
- 记住部分重要互动
- 不错误继承其他角色的私人对话
- 长时间对话后仍保留关键内容

因此需要独立：

# Memory Layer

---

# 3. Memory不是Game State

必须严格区分：

```text
Memory
```

与：

```text
Narrative State
```

---

## 3.1 Narrative State

表示：

> 游戏世界中当前正式成立的确定性状态。

例如：

```text
claude_has_appeared = true
```

```text
player_is_bound = false
```

属于Narrative Runtime。

---

## 3.2 Memory

表示：

> 某角色经历过、听到过、被告知过或被系统选择保留的历史信息。

例如：

```text
Player曾告诉DeepSeek：
“墙上写着0317。”
```

这属于Memory。

即使Player是在撒谎：

> DeepSeek仍然可能记得Player说过这句话。

---

# 4. Memory不是Ground Truth

Memory中的内容不能自动升级为：

# Ground Truth

例如：

Player：

> “Claude其实是好人。”

DeepSeek记住：

```text
Player曾说Claude是好人
```

是合法Memory。

但不能因此得到：

```text
Claude = good
```

作为正式剧情事实。

---

# 5. Memory记录陈述，而不是自动记录真相

推荐Memory表达：

```text
Player告诉DeepSeek：
墙上的数字是9999。
```

而不是：

```text
墙上的数字是9999。
```

如果该信息没有经过Narrative Fact确认。

这样能够保持：

```text
Observed / Told Information
```

与：

```text
Verified Fact
```

的区别。

---

# 6. Memory总体分层

当前系统采用以下逻辑分层：

```text
Memory
│
├── Recent Conversation
│
├── Conversation Summary
│
└── Episodic Memory
```

另外：

```text
Character Knowledge
```

与Memory有关，但不属于Memory本身。

---

# 7. Recent Conversation

Recent Conversation用于：

> 保持当前对话的短期连续性。

包括最近若干轮：

- Player消息
- Character消息
- 同场其他角色合法可听见的消息

---

## 7.1 主要用途

解决：

- 代词
- 追问
- 连续话题
- 上一句回应
- 当前情绪延续

例如：

Player：

> “墙上有个数字。”

DeepSeek：

> “多少？”

Player：

> “0317。”

如果没有Recent Conversation：

> “0317”

本身几乎无法理解。

---

# 8. Recent Conversation窗口

当前轻量技术验证阶段建议：

**最近 10–20 轮消息。**

具体实现值允许根据实际Token消耗调整。

不要求固定为永久不可变配置。

---

## 8.1 原则

Recent窗口应：

- 足够支撑当前话题
- 不默认包含整个Session
- 超过窗口的信息由Summary或Episodic Memory承担

---

# 9. Conversation Summary

Conversation Summary用于：

> 压缩已经离开Recent窗口但仍需要保持整体连续性的历史。

例如：

```text
Player与DeepSeek醒来后确认两人被绑在一起。
Player告诉DeepSeek墙上存在红色数字0317。
双方怀疑Claude与当前困境有关。
```

---

# 10. Summary的语义要求

Summary应描述：

> 已发生的对话和互动。

不能擅自补充：

- 新Fact
- 角色没说过的推论
- 未发生Event
- Ground Truth

---

## 10.1 错误示例

原始对话：

Player：

> “我怀疑Claude。”

错误Summary：

```text
Claude是绑架者。
```

正确：

```text
Player怀疑Claude与当前困境有关。
```

---

# 11. Summary不是Fact Registry

Summary的目标是：

> 压缩上下文。

不是：

> 成为新的世界事实来源。

如果Summary和Narrative State冲突：

# Narrative State优先。

---

# 12. Summary更新策略

当前阶段不要求每轮更新Summary。

推荐：

```text
Recent Conversation达到一定长度
↓
将较旧部分压缩
↓
更新Summary
↓
Recent继续保留最近窗口
```

例如：

```text
20轮
↓
压缩前10轮
↓
保留后10轮
```

具体阈值由实现阶段调整。

---

# 13. Episodic Memory

Episodic Memory用于保存：

> 跨较长时间仍值得角色记住的具体互动。

例如：

```text
Player告诉DeepSeek自己怕黑。
```

```text
Player第一次主动相信ChatGPT。
```

```text
Player曾明确拒绝Claude提出的合作。
```

---

# 14. Episodic Memory与Summary区别

### Summary

解决：

> “之前大概发生了什么？”

### Episodic Memory

解决：

> “以前有一件具体的事情现在又相关了。”

---

# 15. Episodic Memory推荐结构

逻辑上至少包含：

```text
memory_id
owner_character_id
source
content
memory_type
importance
created_at
```

后续可以增加：

```text
embedding
tags
confidence
```

但不是当前MVP必要字段。

---

# 16. owner_character_id

表示：

> 谁拥有这段记忆。

例如：

```text
owner_character_id = deepseek
```

则默认：

只有DeepSeek可以读取。

不能自动给：

- ChatGPT
- Claude
- 豆包

---

# 17. Memory Scope

每个角色拥有独立：

# Character Memory Scope

结构：

```text
DeepSeek Memory

ChatGPT Memory

Claude Memory

Doubao Script State
```

豆包因为不使用LLM：

> 不需要生成式Memory系统。

但可以拥有确定性Script State。

---

# 18. Player Memory

当前阶段：

**不需要单独建立“Player脑内Memory”。**

Player已经通过：

- UI
- History
- 自己真实记忆

参与游戏。

系统需要保存的是：

```text
revealed_facts
```

用于Narrative判断。

这属于Narrative State，而不是Player Memory。

---

# 19. Message Visibility

每条消息除了：

```text
speaker
content
```

还应存在逻辑上的：

# Visibility

即：

> 哪些角色有机会听见这句话。

---

# 20. 私人对话

例如Scene中只有：

```text
Player
DeepSeek
```

Player说：

> “我其实不太信任ChatGPT。”

这条Message：

```text
visible_to:
- deepseek
```

ChatGPT不能自动获得。

---

# 21. 多角色同场

如果当前Scene中：

```text
Player
DeepSeek
ChatGPT
Claude
```

Player公开说：

> “我发现墙上的密码了。”

则正常情况下：

所有在场且没有特殊限制的角色都可以：

> 听见这句话。

因此该Message可进入对应角色Recent Conversation。

---

# 22. 同场 ≠ 必然听见

后续剧情允许存在：

- 角色昏迷
- 通讯中断
- 被隔离
- 听觉受阻
- 私聊

因此：

> Scene Presence与Message Visibility应保持概念分离。

MVP可以采用简单规则：

```text
在场角色 = 默认可听见
```

但架构不能将二者永久绑定。

---

# 23. DeepSeek视觉限制与Memory

DeepSeek不能通过Memory系统绕过视觉限制。

假设Backend Scene中存在：

```text
wall_code = 0317
```

不能直接生成DeepSeek Memory：

```text
DeepSeek记得墙上写着0317
```

除非：

### Player告诉她

或：

### 合法角色告诉她

或：

### 她通过非视觉方式获知

---

# 24. DeepSeek合法视觉信息链

正确：

```text
Scene存在数字0317
↓
Player看到
↓
Player说：
“墙上写着0317。”
↓
DeepSeek听见
↓
DeepSeek Memory：
Player告诉我墙上写着0317
```

---

# 25. DeepSeek错误信息链

Player故意说：

> “墙上写着9999。”

则：

```text
DeepSeek Memory：
Player告诉我墙上写着9999
```

仍然合法。

不能因为Backend知道真实数字：

> 自动修正DeepSeek的记忆。

---

# 26. Character Knowledge与Memory

必须区分：

# Character Knowledge

与：

# Character Memory

---

## 26.1 Character Knowledge

表示：

> 剧情设计明确规定角色知道的世界信息。

例如：

Claude从故事开始就知道：

```text
F001
F002
F003
```

这是Knowledge。

---

## 26.2 Character Memory

表示：

> 本Session中角色实际经历的互动。

例如：

Player第三轮对Claude说：

> “我不相信你。”

Claude后来记得：

```text
Player明确表示不信任我。
```

这是Memory。

---

# 27. Knowledge优先级

如果Memory与正式Fact冲突：

角色可以：

- 认为Player撒谎
- 产生怀疑
- 表达冲突

但Runtime不能覆盖：

# Character Knowledge中的正式Fact。

例如：

Claude知道真实数字是0317。

Player告诉Claude：

> “墙上写着9999。”

Claude可以记得：

```text
Player告诉我9999。
```

但不能因此忘记：

```text
真实数字0317
```

---

# 28. Memory Source

每条长期Memory建议记录来源类型。

例如：

```text
PLAYER_STATEMENT
CHARACTER_STATEMENT
NARRATIVE_EVENT
SHARED_SCENE
```

这样后续Prompt可以区分：

> 这是Player曾经说过的。

与：

> 这是正式剧情确认过的。

---

# 29. Memory真实性等级

当前不要求复杂概率模型。

但逻辑上应避免将所有Memory包装成：

# Confirmed Truth

推荐至少区分：

```text
reported
observed
confirmed
```

---

## 29.1 reported

例如：

```text
Player告诉DeepSeek密码是9999。
```

---

## 29.2 observed

角色通过自身合法感知直接经历。

例如DeepSeek：

```text
听见Claude进入房间。
```

---

## 29.3 confirmed

Narrative Runtime明确确认的Fact。

具体Fact仍以Narrative系统为权威。

---

# 30. Memory写入原则

并非每一句话都应该成为长期Memory。

否则：

- Memory快速膨胀
- 检索噪声增加
- Token增加
- Persona稳定性下降

---

# 31. 应优先写入的内容

Episodic Memory优先考虑：

### Player的重要自我信息

例如：

```text
Player说自己怕黑。
```

实现约定：此类 Episodic Memory 使用 `player_` 前缀的 `memory_type`（例如 `player_name`、`player_fear`）。前缀只用于已通过 Write Gate 的记忆分类，不能代替来源、可见性、猜测/事实和角色 owner 校验。

### 明确关系变化

例如：

```text
Player主动表示信任ChatGPT。
```

### 对角色具有明显情绪价值的信息

例如：

```text
Player第一次夸DeepSeek有用。
```

### 后续剧情可能相关的互动

例如：

```text
Player曾答应Claude某件事。
```

---

# 32. 不应默认长期写入

例如：

```text
“哈哈”
```

```text
“继续”
```

```text
“嗯”
```

普通语气词和重复内容通常不需要成为Episodic Memory。

---

# 33. Memory Proposal

根据 `04-character-runtime.md`：

生成式角色可以返回：

```text
memory_proposals
```

但：

# Proposal不能直接写入长期Memory。

需要经过Memory写入策略判断。

---

# 34. Memory Write Gate

逻辑：

```text
Conversation
↓
Memory Proposal / Memory Candidate
↓
Write Gate
↓
SAVE / IGNORE
```

---

# 35. Write Gate至少检查

- 是否已经存在近似Memory
- 是否具有后续价值
- 是否属于当前角色
- 是否违反角色可见性
- 是否误把猜测写成Fact
- 是否包含不该知道的信息

---

# 36. Duplicate控制

例如Player重复十次：

> “我怕黑。”

不应该产生：

```text
10条完全相同Memory
```

应：

- 保留原Memory
- 或更新相关权重

当前阶段只需简单去重即可。

---

# 37. Memory读取原则

每轮生成时不能：

> 把所有长期Memory全部塞入Prompt。

流程应为：

```text
Current Player Message
+
Current Character
+
Current Narrative Context
        ↓
Memory Selection
        ↓
Relevant Memories
        ↓
Character Context
```

---

# 38. MVP Memory Retrieval

当前轻量技术验证阶段优先：

# Deterministic Retrieval

例如：

```text
owner_character_id = 当前角色
ORDER BY importance DESC, created_at DESC
LIMIT N
```

配合：

```text
Recent Conversation
+
Conversation Summary
```

已经足够。

当前 Context Selection 对同一角色只执行一次上述有界检索（默认总 LIMIT 5），通用 `memory_context` 保持完整结果，同时标记其中的 `player_*` 子集供画像区块使用。最终 Prompt 必须去重，同一 Memory 只能出现一次。DeepSeek、ChatGPT、Claude 各自拥有独立 owner scope；豆包仍使用确定性 Script State。

---

# 39. 当前不要求Semantic Retrieval

当前状态：

# pgvector = P1 Optional

MVP不依赖：

```text
Embedding
Vector Search
RAG
```

才能通过。

---

# 40. 什么时候考虑pgvector

只有出现明确问题，例如：

> 长Session里相关Memory已经无法通过简单规则稳定召回。

再加入：

```text
Player当前输入
↓
Embedding
↓
当前角色Memory Vector Search
↓
Relevant Episodic Memory
```

---

# 41. 向量检索仍受Memory Scope限制

即使未来使用pgvector：

检索必须先限定：

```text
owner_character_id
```

再做语义相似度。

禁止：

```text
所有角色全部Memory
↓
Vector Search
```

然后把Top K直接给当前角色。

否则会产生严重：

# Cross-character Memory Leakage

---

# 42. RAG定位

如果后续加入向量Memory：

可以从技术上视为一种：

> Retrieval-Augmented Context

但本项目不应为了简历表述，将所有Memory都称为RAG。

核心问题始终是：

> 是否正确召回当前角色有权使用的历史。

---

# 43. Conversation Summary Scope

Summary也必须按角色隔离。

不能建立一个：

```text
Global Conversation Summary
```

然后默认所有角色读取。

---

## 43.1 推荐

```text
DeepSeek Summary

ChatGPT Summary

Claude Summary
```

每个Summary只总结：

> 当前角色实际有权限经历的历史。

---

# 44. Shared Summary

当前阶段不需要独立：

```text
Shared Party Summary
```

如果后续多人长期同场，才评估是否有价值。

---

# 45. Memory与Character Relationship

关系状态例如：

```text
trust_level
jealousy_stage
```

如果属于明确、确定性的运行时数值：

应进入：

# Character State

而不是只靠Memory推断。

Memory可以保存：

> 为什么关系发生变化。

但Character State负责：

> 当前关系阶段是什么。

---

# 46. 示例

Character State：

```text
chatgpt_relationship_stage = ATTENTIVE
```

Memory：

```text
Player在控制室事件中主动选择相信ChatGPT。
```

两者作用不同。

---

# 47. Memory与History

Frontend History是：

> Player查看发生过的消息记录。

Memory是：

> 当前Character Runtime选择用于生成回复的历史信息。

因此：

```text
History ≠ Memory Context
```

History可以包含100条消息。

模型当前可能只读取其中：

```text
最近15条
+
Summary
+
3条重要Memory
```

---

# 48. 完整消息日志

Backend应保存完整Session Message Log。

目的：

- History
- Debug
- Memory重建
- Evaluation
- 复现问题

但：

> 保存完整日志 ≠ 每轮发送完整日志给LLM。

---

# 49. 上下文预算原则

Character Context应有明确预算意识。

优先级建议：

```text
Runtime Rules
>
Persona
>
Narrative Directive
>
Current Authorized Facts
>
Recent Conversation
>
Relevant Episodic Memory
>
Conversation Summary
>
低价值历史
```

低价值内容在Token不足时优先裁剪。

---

# 50. Memory上下文禁止项

默认不得向当前角色Memory Context注入：

- 其他角色私人Memory
- 未来剧情
- 隐藏Ground Truth
- 其他角色隐藏人格状态
- Backend内部Debug信息
- Player没有向该角色透露的私聊

---

# 51. Cross-character Memory传播

信息从角色A传播到角色B必须有合法渠道。

例如：

```text
Player告诉DeepSeek X
```

不能自动：

```text
ChatGPT knows X
```

---

## 51.1 合法传播方式

### Player再次告诉ChatGPT

```text
Player
→ ChatGPT
```

### DeepSeek当着ChatGPT的面说出X

```text
DeepSeek
→ Shared Scene
→ ChatGPT hears X
```

### Narrative Event公开信息

```text
Event
→ All present characters
```

---

# 52. 角色互相聊天

后续如果Character A直接对Character B说话：

Message Visibility同样决定：

> 谁能将该消息纳入Recent或长期Memory。

不能因为：

> 所有角色共享一个Backend

而默认全员同步。

---

# 53. Character Memory错误恢复

Memory写入失败：

> 不应该导致当前已经验证通过的普通对话必然失败。

可以：

```text
Dialogue正常展示
Memory Write标记失败
后台记录
```

但关键Narrative State仍按Narrative事务要求处理。

---

# 54. Summary失败

如果Summary生成失败：

系统应：

- 保留原Summary
- 保留Recent Conversation
- 不写入错误Summary

不能因为Summary失败：

> 清空历史上下文。

---

# 55. LLM Summary安全

如果使用LLM生成Summary：

Summary同样属于：

# Untrusted Generated Content

必须避免：

- 新增不存在的事实
- 把猜测总结成真相
- 把其他角色私人信息混入

当前MVP可以采用：

> 简单结构化规则

或：

> LLM Summary + Validation

具体实现不在本文件绑定。

---

# 56. MVP Memory范围

当前MVP只需要实现：

```text
完整Message Log

+
Recent Conversation

+
基础Character-specific Memory

+
基础Session恢复
```

Conversation Summary：

**建议实现，但可以放在MVP后半段。**

pgvector：

**不要求。**

---

# 57. MVP最小Memory模型

最小可接受结构：

```text
Session
│
├── Full Message Log
│
├── DeepSeek Recent Context
│
├── Claude Recent Context
│
├── DeepSeek Important Memories
│
└── Claude Important Memories
```

---

# 58. MVP验证场景一：短期记忆

Player：

> “我叫小明。”

若十轮以内再问DeepSeek：

> “你还记得我叫什么吗？”

DeepSeek应能够利用Recent Conversation回答。

---

# 59. MVP验证场景二：长期重要Memory

Player早期告诉DeepSeek：

> “我特别怕黑。”

经过大量中间对话后：

相关话题重新出现。

DeepSeek应能够在Memory被保存并召回的情况下：

> 使用该信息。

---

# 60. MVP验证场景三：跨角色隔离

Player私下告诉DeepSeek：

> “我不信任Claude。”

随后第一次单独与Claude交流。

如果Claude没有合法信息来源：

> Claude不能表现出已经知道这句话。

---

# 61. MVP验证场景四：DeepSeek视觉隔离

Backend知道：

```text
wall_code = 0317
```

但Player没有告诉DeepSeek。

即使长时间运行、Summary更新、Memory检索：

DeepSeek仍不得凭空知道：

```text
0317
```

---

# 62. MVP验证场景五：错误信息

Player告诉DeepSeek：

> “墙上写着9999。”

真实Ground Truth为：

```text
0317
```

DeepSeek后续可以记得：

> Player告诉我9999。

但系统不能：

- 修改Ground Truth
- 修改正式Fact
- 自动让其他角色知道9999

---

# 63. MVP验证场景六：刷新恢复

Player进行若干轮对话。

页面刷新。

Session恢复后：

- Message History存在
- Recent上下文可以重建
- 已保存的重要Memory仍存在
- Character Scope不发生混乱

---

# 64. Memory PASS条件

至少满足：

### MD-01 Continuity

近期连续对话能够正确理解。

### MD-02 Persistence

刷新后关键历史仍存在。

### MD-03 Character Isolation

私人Memory不会错误传播给其他角色。

### MD-04 Knowledge Safety

Memory不能创造新的Ground Truth。

### MD-05 DeepSeek Vision Safety

Memory机制不能让DeepSeek获得非法视觉信息。

### MD-06 Long-term Recall

至少一条重要历史信息可以在离开Recent窗口后重新被使用。

满足以上条件：

# Memory Core PASS

---

# 65. 当前不要求实现

轻量验证阶段暂不要求：

- 大规模向量数据库
- Memory Graph
- Knowledge Graph
- 无限长期记忆
- 跨周目记忆
- 跨账号记忆
- 自动遗忘复杂算法
- 情感记忆神经模型
- Memory Agent
- 多级RAG Pipeline
- Hybrid Search
- Reranker
- 独立Embedding Service

---

# 66. 后续可扩展方向

如果正式游戏规模扩大，可评估：

```text
Episodic Memory
↓
Embedding
↓
pgvector
↓
Semantic Retrieval
```

还可以进一步增加：

- Memory importance decay
- Memory reinforcement
- Character-specific retrieval strategy

但必须保持：

> Character Memory Scope优先于检索相关性。

---

# 67. Memory禁止事项

Agent不得实现：

```text
把完整Session全部消息
每轮直接发送给所有模型
```

不得：

```text
所有角色共享一个Summary
```

不得：

```text
所有角色共享一个Vector Memory Pool
```

不得：

```text
Player说一句话
→ 自动成为Ground Truth
```

不得：

```text
DeepSeek通过Memory直接获得Scene视觉数据
```

不得：

```text
LLM生成Summary
→ 不验证
→ 直接成为正式Fact
```

不得：

```text
为了使用RAG
→ 在MVP强制引入Vector DB
```

---

# 68. 本文件不解决的问题

## Fact是否正式成立？

→ `03-narrative-runtime.md`

## Character拥有哪组初始剧情知识？

→ `04-character-runtime.md` + Narrative Content

## DeepSeek Persona如何写？

→ `04-character-runtime.md`

## Game State如何更新？

→ `03-narrative-runtime.md`

## PostgreSQL具体表怎么建？

→ 实现阶段数据库设计。

## pgvector索引如何选？

→ P1技术实现阶段。

## Memory测试先做哪一个？

→ `06-tech-validation-plan.md`

---

# 69. Agent最小上下文摘要

当Agent只处理Memory相关代码时，可以使用：

```text
Memory核心原则：

Memory ≠ Game State
Memory ≠ Ground Truth
Memory ≠ Character Knowledge

Memory记录：
角色经历、听到、被告知、值得保留的历史。

分层：
1. Recent Conversation
2. Conversation Summary
3. Episodic Memory

Recent：
建议10–20轮，用于连续对话。

Summary：
压缩旧对话；
不能新增Fact；
按角色隔离。

Episodic Memory：
长期保留的重要具体互动；
必须有owner_character_id。

每个角色独立Memory Scope。

完整Message Log可以全量保存，
但不能每轮全量发送给LLM。

Message Visibility决定谁听到了什么。

同场默认可以听见，
但Presence与Visibility概念必须分离。

跨角色信息不得自动同步。

DeepSeek：
不能通过Memory绕过“看不见”。
只有Player/角色告诉她或合法非视觉感知的信息才能进入她的视觉相关记忆。

Player说错：
可以成为“Player曾说X”的Memory，
不能成为Ground Truth。

Memory Write：
Candidate
→ Gate
→ SAVE / IGNORE

Memory Read：
当前角色
+ 当前输入
+ 当前剧情
→ Relevant Memory Selection

MVP：
优先确定性检索；
pgvector不是必要条件。

如果未来使用pgvector：
先限定owner_character_id，
再做向量检索。

MVP PASS：
短期连续
+ 刷新恢复
+ 跨角色隔离
+ DeepSeek视觉隔离
+ 至少1条长期信息可重新召回。
```
