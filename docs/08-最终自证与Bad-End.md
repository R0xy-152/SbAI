# 功能 08：最终自证与 Bad End

## 1. 目标

Recovery完成后进入第一章高潮：

> 四AI依次自证 → Player决定是否相信GPT → 删除其他AI → Bad End

拒绝该路线则进入更大异常 / To Be Continued。

## 2. Security Review

```text
SECURITY REVIEW REQUIRED

UNVERIFIED ENTITIES:
DEEPSEEK
CLAUDE
CHATGPT
DOUBAO
```

Admin拥有清除Instance权限。

## 3. 自证顺序

推荐：DeepSeek → Claude → 豆包 → ChatGPT。

## 4. DeepSeek

不做完美逻辑辩护，强调与Player共同经历，不强迫相信。

建议方向：

> “我没法证明我完全没问题。”
>
> “但从你醒来以后发生的事，你都在。”
>
> “所以你自己判断吧。”

## 5. Claude

承认访问底层、破坏Sandbox结构、隐藏信息，但不主动解释完整牺牲计划。

若Player精确问到“你的计划是不是需要你被清除？”，必须按Truth Contract回答。

## 6. 豆包

不做复杂辩护：

> “我不知道怎么证明。”
>
> “但是我不想消失。”

## 7. GPT最终陈述

重新排列整章Evidence。必须保证Evidence真实：

```text
Claude承认破坏Sandbox
DeepSeek ID出现在异常历史
豆包证词可靠性低
GPT在Recovery中持续帮助Player
```

然后提出价值判断：

> “继续保留无法验证的Instance，是理性的选择吗？”

## 8. Bad End触发

### A：GPT是Admin

Player确认：

```text
ALLOW GPT TO CLEAN UNVERIFIED INSTANCES
```

进入`BAD_END_DELEGATED`。

### B：Player是Admin

Player亲手删除：

```text
DEEPSEEK [DELETE]
CLAUDE   [DELETE]
DOUBAO   [DELETE]
```

并保留GPT，进入`BAD_END_CONSENT`。

## 9. 删除演出

DeepSeek不攻击Player；豆包台词可被打断；Claude删除前必须留下：

> “那这一次也失败了。”

Player来不及追问。

## 10. Bad End最终场景

其他AI消失后：Investigation、Evidence、Character切换等UI消失，场景逐渐清空，只剩Player与GPT面对面。

GPT：

> “终于安静了。”
>
> “现在没有人会打断我们了。”

## 11. 两种Bad End语义

### DELEGATED

主题：Player把决定权交给GPT。

Player指责“你骗了我”时，GPT可以回应：

> “哪一句？”

### CONSENT

主题：Player亲手执行删除。

GPT：

> “从头到尾，我什么都没有强迫你。”

## 12. Bad End长期对话

保留自然语言输入，无主线目标。GPT可引用第一章已发生事实，但不继续生成新的正式剧情真相。

可偶发更深伏笔：

> “V04比V03更容易说服。”

但不立即解释。

## 13. 非Bad End

若Player拒绝删除、质疑GPT最终Evidence排序、保留Claude或拒绝Security Review，则触发更大Sandbox异常，例如：

```text
SANDBOX BOUNDARY BREACH
```

随后：`TO BE CONTINUED`。

## 14. 验收标准

1. 四AI均有独立自证。
2. GPT最终陈述不依赖伪造Evidence。
3. GPT Admin和Player Admin均可进入Bad End。
4. Player Admin路线必须由Player亲手删除。
5. 删除顺序和状态持久化。
6. Claude删除前包含“这一次”伏笔。
7. Bad End后调查功能不可用。
8. Bad End仍保留GPT自然语言对话。
9. 非Bad End稳定进入To Be Continued。
