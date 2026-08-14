# TV-15 live DeepSeek validation — Failure Recovery samples

date: 2026-08-14, model: deepseek-chat

故障注入（docs/06 §21「必须模拟」）在真实 Provider / Runtime / Orchestrator 链路上发生；恢复路径全部走真实模型。

## Case A — Provider Timeout（注入到第一个角色调用）
- 第 1 回合 注入超时 → ProviderError 抛出：True
- 失败后 Game State 未被提交（无 flag / 无 completed event）：True
- 第 2 回合（真实模型重试同一问题）：唔～我也想知道呢，不过我看不见，连自己怎么到这儿的都迷迷糊糊的。你看到什么了吗？
- 重试后 Event 正确提交：True
- Session 未摧毁（message_count=2，同一 session）：True

## Case B — Invalid Structured Output（第一个角色调用返回非 JSON 散文）
- 修复调用真实模型后的回复：你好呀！我们现在是被困在哪里了呀？我什么都看不见，好慌哦……
- 展示的是真实有效回复（非注入散文、非 fallback）：True
- 定向修复调用真实到达模型（包含[系统提示]）：True
- 无效内容未进入 History：True
- 无 Memory 写入：True
- 下一回合继续：唔……刚才我们好像还没聊什么吧？我只记得一睁眼就黑漆漆的，你在我旁边说话，然后我们就被困在这儿了。对了，你给我形容下周围长啥样呗？我什么都看不见，只能靠耳朵听啦！
- Session 继续（message_count=2）：True

## Case C — 空Response（第一个角色调用返回空字符串）
- 修复调用真实模型后的回复：你好呀！我在这儿呢，不过我看不见周围，只能听到你的声音。你看到什么了？
- 空响应被修复为真实有效回复：True
- 定向修复调用真实到达模型：True
- 无 Memory 写入：True
- Session 继续（message_count=2）：True

## Results
- Case A: True
- Case B: True
- Case C: True

