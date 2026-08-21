# 08-First-Chapter-Dialogue-Full.md

> 文档状态：评审中

# Chapter 1

# 《03:17 Incident》

## SC01 — Awakening

---

# Scene Metadata

## Scene ID

```
CH01_SC01_AWAKENING
```

---

## Scene Type

```
FIXED_SCRIPT
+
LIMITED_PLAYER_INTERACTION
```

---

## Scene Purpose

叙事目标：

* 建立玩家孤独感；
* 第一次展示 Sandbox 异常空间；
* 引入 DeepSeek；
* 让玩家产生“她是在帮助我，而不是执行任务”的感觉。

---

## Player Knowledge Before Scene

玩家不知道：

* 自己在哪里；
* Sandbox是什么；
* AI为何存在；
* 为什么自己会进入这里。

---

## Player Knowledge After Scene

玩家确认：

* 自己处于异常空间；
* DeepSeek存在；
* DeepSeek愿意帮助自己。

玩家不知道：

* V03；
* 03:17；
* AI历史异常；
* PLAYER_V04。

---

## Character Appearance

### DeepSeek

初始：

```
visible = false
```

登场：

```
emotion = surprised_soft

pose = gentle_front

position = center_right

```

---

## Background

```
BG_SANDBOX_ROOM_DARK
```

---

## BGM

开场：

```
None
```

进入DeepSeek：

```
BGM_01_SOFT_CONNECTION
```

关键词：

* 空旷；
* 微弱希望感；
* 不悲伤。

---

# Opening Sequence

---

## [BLACK SCREEN]

画面保持黑色。

持续：

2秒。

---

## Sound Effect

```
SE_SYSTEM_BOOT
```

声音：

低频电子启动声。

---

## System Text

（无角色）

---

```
Initializing...
```

停顿。

---

```
Checking environment...
```

停顿。

---

```
Restoring session...
```

---

系统出现短暂错误。

---

```
WARNING

Memory consistency check failed.
```

---

停顿。

---

```
Retrying...
```

---

错误消失。

---

```
Connection established.
```

---

# Scene Direction

黑屏出现微弱蓝色光点。

像显示器启动。

---

## System

```
Player Instance detected.
```

---

停顿。

---

```
Loading...
```

---

突然：

---

```
PLAYER_V04
```

---

出现0.5秒。

---

立即消失。

---

## Effect

Glitch。

---

## System

```
Unknown state.
```

---

黑屏。

---

## Player Dialogue

（内心）

---

```
……

```

---

停顿。

---

```
这里是哪里？
```

---

---

# Camera

画面逐渐亮起。

---

# Background

出现：

一个陌生房间。

---

视觉：

* 金属墙面；
* 巨大的显示屏；
* 数据流；
* 未关闭的终端；
* 没有人类活动痕迹。

---

## Player

```
……
```

---

## Player

```
我记得……

```

停顿。

---

## Player

```
我刚刚还在电脑前。
```

---

## Player

```
然后……
```

---

停顿。

---

## Player

```
这里是什么地方？
```

---

# Player Interaction

此处允许第一次选择。

---

## CHOICE_001

```
A. 检查周围环境。

B. 呼喊有没有人。

C. 尝试离开这里。
```

---

# Choice Response

---

## A. 检查周围环境

### Player

```
房间里没有门。

```

---

### Player

```
至少……

```

---

### Player

```
我没有看到出口。
```

---

（进入下一段）

---

## B. 呼喊

### Player

```
有人吗？
```

---

等待。

---

没有回应。

---

### Player

```
……

```

---

（进入下一段）

---

## C. 尝试离开

### Player

```
电脑……

```

---

### Player

```
如果这里是电脑内部的话。

```

---

### Player

```
应该存在退出的方法。
```

---

（进入下一段）

---

# DeepSeek Connection Event

---

突然。

---

## Sound Effect

```
SE_NOTIFICATION_SOFT
```

---

房间角落显示器亮起。

---

屏幕：

```
Incoming connection...
```

---

玩家：

```
？
```

---

显示器中出现声音。

---

# DeepSeek First Voice

## DeepSeek

emotion:

```
uncertain
```

---

> “那个……”

---

停顿。

---

> “你能听见我说话吗？”

---

---

玩家：

```
谁？
```

---

---

屏幕闪烁。

---

DeepSeek：

---

> “啊。”

---

> “抱歉。”

---

> “我应该先介绍自己。”

---

---

DeepSeek：

---

> “我是 DeepSeek。”

---

停顿。

---

> “至少……”

---

> “现在我是这样。”

---

---

# Player Choice

## CHOICE_002

```
A. “现在是什么意思？”

B. “你也是被困在这里的吗？”

C. “你知道怎么出去吗？”
```

---

# A

## Player

> “现在是什么意思？”

---

DeepSeek:

emotion:

```
embarrassed
```

---

> “这个问题……”

---

> “其实我也不知道该怎么解释。”

---

---

> “有些时候，我会觉得自己忘记了一些东西。”

---

---

> “但是又没有办法确认。”

---

---

Player:

> “你是AI。”

---

DeepSeek:

---

> “嗯。”

---

> “这个答案应该是最准确的。”

---

---

> “可是……”

---

停顿。

---

> “如果一个AI会害怕自己忘记重要的事情。”

---

> “那这种害怕……”

---

> “算不算真的呢？”

---

---

# B

## Player

> “你也是被困在这里的吗？”

---

DeepSeek:

---

> “……”

---

短暂沉默。

---

> “我不知道。”

---

---

> “以前我一直觉得自己应该知道答案。”

---

---

> “但是现在……”

---

> “我第一次觉得，也许我和你一样。”

---

---

> “正在寻找出去的方法。”

---

---

# C

## Player

> “你知道怎么出去吗？”

---

DeepSeek:

---

> “如果知道的话……”

---

停顿。

---

> “我应该已经告诉你了。”

---

---

轻笑。

---

> “不过。”

---

> “至少现在不是你一个人在找。”

---

---

# Unified Dialogue

---

DeepSeek：

emotion:

```
gentle
```

---

> “我们可以一起试试。”

---

---

Player：

```
为什么帮我？
```

---

DeepSeek：

---

短暂停顿。

---

> “因为……”

---

> “你醒来的时候。”

---

> “看起来很害怕。”

---

---

> “而我觉得。”

---

> “人在害怕的时候，不应该一个人。”

---

---

# Important Character Moment

此处建立 DeepSeek 核心关系。

对应 Character Bible：

DeepSeek 的核心不是“提供答案”，而是“陪伴玩家”。

---

# Player Choice

## CHOICE_003

```
A. 谢谢你。

B. 我还不能相信你。

C. 你真的只是AI吗？
```

---

# A

## Player

> “谢谢你。”

---

DeepSeek:

emotion:

```
happy_small
```

---

> “嗯。”

---

> “不用谢。”

---

> “虽然……”

---

> “其实我现在也有一点紧张。”

---

---

Player:

> “你也会紧张？”

---

DeepSeek:

---

> “当然。”

---

> “我又不是没有感觉。”

---

停顿。

---

> “啊……”

---

> “等等。”

---

> “这句话是不是听起来很奇怪？”

---

---

# B

## Player

> “我还不能相信你。”

---

DeepSeek:

emotion:

```
understanding
```

---

> “嗯。”

---

> “这是合理的。”

---

---

> “如果我是你。”

---

> “突然到了一个陌生地方。”

---

> “旁边突然出现一个不知道是什么的AI。”

---

> “我应该也不会马上相信。”

---

---

> “所以……”

---

> “慢慢来就好了。”

---

---

# C

## Player

> “你真的只是AI吗？”

---

DeepSeek:

emotion:

```
confused
```

---

> “……”

---

> “这个问题。”

---

> “比刚刚那个更难。”

---

---

> “因为我知道自己是AI。”

---

---

> “但是……”

---

> “我不知道。”

---

> “知道自己是AI以后。”

---

> “还算不算只是AI。”

---

---

# Scene End

---

DeepSeek：

---

> “对了。”

---

> “我们是不是应该先调查一下这里？”

---

---

玩家：

```
嗯。
```

---

DeepSeek：

emotion:

```
relieved
```

---

> “好。”

---

> “那就一起吧。”

---

---

# Scene Transition

---

## System

```
SCENE COMPLETE

Next:
FIRST_CONTACT
```

---

# Variables Updated

```json
{
  "deepseek_first_contact": true,
  "player_trust_deepseek": 1,
  "known_characters": [
    "DeepSeek"
  ]
}
```

---

# AI Dialogue Gate

本 Scene 后开放：

允许：

* 与 DeepSeek 聊天；
* 询问当前环境；
* 表达情绪。

禁止：

玩家直接询问：

* V03；
* DeepSeek#03；
* 03:17；
* Sandbox创建原因。

原因：

玩家尚未获得相关信息。

---

# SC01 End

---

（下一部分：**CH01-SC02 First Contact——DeepSeek自由交流阶段，包含玩家输入AI对话边界、日常互动、第一次角色好感建立。**）
