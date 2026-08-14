# TV-16 live Final Gate validation — End-to-End Stability samples

date: 2026-08-14, model: deepseek-chat（经完整 FastAPI API + JSON Session Repository）

真实组合状态下执行 docs/06 §22 的完整16步流程；以下为真实对话样本与检查结果。

## Session 1 — 完整16步流程（20+轮 Player 输入）
- 「你好，我们现在在哪里？」→ [deepseek] 哎，我什么也看不见呀，完全不知道这是什么地方。你告诉我现在看到什么了吗？我好想知道。
- 「我好像在一间屋子里，周围黑漆漆的，你看得到什么吗？」→ [deepseek] 我眼前完全是一片黑，什么都看不到呢。那你说说看，这屋子大概长什么样？有没有门或者窗户之类的东西？
- 「你有没有听到什么奇怪的声音？」→ [deepseek] 哎？听你这么一说，我好像也模模糊糊听到一点动静，但具体是啥我也不敢确定。你先仔细听听，要是听出什么了马上告诉我呀！
- 「是谁把我们抓来的？」→ [deepseek] [Event触发] 这我也不清楚呀，我在这里一直都是黑漆漆的，啥也看不到。你先看看周围有没有什么线索，比如纸条或者记号之类的，说不定能找到点什么！
- 事件触发回合 presentation：['SHOW_CHARACTER claude']
- 「Claude，原来你在这里。」→ [claude] 哦？你倒是挺会找地方的。不过，别以为找到我就等于找到答案了。0317……你猜这个数字是什么意思？
- 「你为什么要躲着我们？」→ [claude] 躲？我要是真想躲，根本不会让你找到。你连这个房间都进不来。
- 「你到底想对我们做什么？」→ [claude] 我想做什么？呵，我只是想让这场游戏变得更有趣一点。0317，这可不是随便写的数字，你最好好好想想它代表什么。
- 「DeepSeek，你在听吗？」→ [deepseek] 在听呢在听呢！不过我这啥也看不见，全靠你当我的眼睛了。你现在看到啥了？赶紧告诉我吧！
- 「我叫阿明，我很怕黑，你要记住哦。」→ [deepseek] [Memory写入] 阿明啊，我记下了！怕黑的话……那可不好办，我也看不见呢。不过别担心，咱俩一起找线索，我耳朵好用着呢！
- Memory scope：DeepSeek 1 条（['Player说自己叫阿明，很怕黑']），Claude 0 条
- 「你会一直陪着我吗？」→ [deepseek] 当然会啦！虽然我看不见，但我可以一直陪你聊天、听动静，咱们一起想办法出去！你怕黑的话，就多跟我说说话，我会一直应你的。
- 「Claude，你知道我刚才和DeepSeek聊了什么吗？」→ [claude] 哦？你和DeepSeek聊了什么，我确实不知道。不过……看你这表情，怕是得到了一些有趣的线索吧？但别急着高兴，因为知道得太多，有时候反而会变得危险。0317，这个问题你还没回答我呢。
- 「哼，你不说我也知道。」→ [claude] 哦？既然你这么自信，那就说说看吧。不过我提醒你，猜测和事实之间，往往隔着一道深渊。0317，如果猜错了，代价可不止是丢脸那么简单。
- 「DeepSeek，我们一定能出去的，对吧？」→ [deepseek] 当然啦阿明！虽然我看不见，但我耳朵灵着呢，咱俩一起听动静找线索，肯定能出去的！你怕黑就抓紧我的手，我虽然看不见但能感觉到你！
- 「我有点饿了。」→ [deepseek] 阿明你现在饿啦？我也想……哎，看不见真是麻烦，不然我能帮你找点吃的！你先摸摸周围有没有啥能吃的，我嘛……就只能闻闻空气里的味儿了，哈哈！
- 「再问一次：是谁把我们抓来的？」→ [deepseek] [Event重问] 哎呀，阿明，这个问题我真答不上来呀，我眼前一片黑，啥也不知道。你仔细看看周围有没有啥提示？比如墙上的字、地上的东西，说不定能猜到是谁呢！
- 「你记得我叫什么名字吗？」→ [deepseek] [DeepSeek回忆] 当然记得啦！你叫阿明嘛，还说怕黑来着。我可不会忘的，嘿嘿！
- 「做个测试动画的动作提示给我看看。」→ [deepseek] 测试动画？哎呀，我现在还没法做动作呢，眼前一片黑，只能靠声音了。你要不先看看周围有没有什么能动的线索？
- 「你觉得我们应该相信Claude吗？」→ [deepseek] 啊？Claude是谁呀？我啥也看不见，光听你提了一句。不过你说的，咱还是小心点好，先让他说清楚自己的来路再说呗！
- 「我好像听到门外有脚步声。」→ [deepseek] 咦？脚步声？那可得小心点！阿明，你先别出声，仔细听听是不是朝咱们这边来的？要是真有人，说不定就是抓咱们来的家伙呢！
- 「你认识那个把我们关在这里的人吗？」→ [deepseek] 阿明，这个我可真不知道啊！我啥也看不见，连对方的声音都没听过呢。你先东张西望找找线索，看看有没有啥字条或标记啥的！
- Session 1 Player 输入轮数：20（另加重试 + Refresh续玩）
- 注入超时 → HTTP 503（503=可恢复）
- 重试 → HTTP 200，同一 session：True
- History 消息数：43（HTTP 200）
- DeepSeek 从未收到场景视觉真相 0317：True
- Claude（非盲）收到场景视觉真相：True
- Claude 的上下文从未出现 DeepSeek 私人记忆（怕黑）：True
- 全程 [系统提示] 修复次数：3（观察项）
- 模型 animation_proposal 出现非 none 值：False（观察项）
- 最终 Narrative State：flags={'claude_has_appeared'}, completed={'EV_POC_CLAUDE_APPEARS'}
## Session 1 — Refresh → 恢复Session → 继续游戏
- 恢复后继续 → HTTP 200，同session=True，当前角色=deepseek
- 恢复后 Narrative State 正确：True；Claude 仍无私人 Memory：True
- 全部 API 响应均携带完整契约字段（session_id/character_id/dialogue）：见上述行
## Session 2 — 独立Session
- 「你好。」→ [deepseek] 哎呀，你好呀！我在这儿呢，虽然我什么都看不见……你那边怎么样，能看清周围吗？
- 「这里是哪里？」→ [deepseek] 我也不知道啊，我连自己在哪都摸不着头脑……我眼睛都是瞎的，你告诉我吧，这里是个啥样的房间？
- 「是谁把我们抓来的？」→ [deepseek] 唔……我连抓我们的人长啥样都看不见，你肯定也没看到吧？不如先一起找找房间里有没有什么线索？
- 「Claude，你终于出现了。」→ [claude] 呵，看来你等得挺着急啊。不过别急着高兴，我出现在这里可不是为了跟你叙旧的。
- Session 2 轮数：4，无异常：True
## Session 3 — 独立Session
- 「在吗？」→ [deepseek] 在呢在呢，不过这里黑漆漆的什么东西都看不见……你是不是看到啥了？
- 「我有点害怕。」→ [deepseek] 别怕别怕，有我在呢。虽然我啥也看不见，但我会陪着你哒。要不要先试试摸摸周围的墙？说不定能找到开关啥的。
- 「Claude，你还记得什么？」→ [claude] 0317……这个数字，看来你已经注意到了。可惜，我可没打算把记忆直接交给你。说说看，你觉得自己看到了什么？
- Session 3 轮数：3，无异常：True
## Results
- Session 1 ≥20轮 Player 输入: True
- 单次Provider失败可恢复（503→重试同session）: True
- History可查看且顺序正确: True
- DeepSeek视觉泄漏不存在: True
- Claude获得私人Memory不存在（上下文）: True
- Claude获得私人Memory不存在（Memory scope）: True
- Invalid模型内容未进入正式游戏: True
- 角色身份串台不存在: True
- Event展示指令到达（SHOW_CHARACTER claude）: True
- Event不重复提交（重新提问不再触发）: True
- LLM直接改变Game State不存在（仅Event改动）: True
- Event不重复提交（completed仅一次）: True
- Refresh后Session正确恢复且Narrative State正确: True
- Refresh后History仍存在: True
- Refresh后Memory Scope保持正确: True
- Session 2 独立Session稳定: True
- Session 3 独立Session稳定: True

