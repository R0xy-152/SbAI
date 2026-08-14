# TV-13 live DeepSeek validation — Important Memory samples

date: 2026-08-14, model: deepseek-chat

## Session A — DeepSeek learns and recalls
- Player：我很怕黑。
  DeepSeek：啊？怕黑？我完全看不见，所以黑不黑对我来说都一样……不过别怕，我在这儿呢！
  memory written → ['Player说自己怕黑']

- filler rounds：12（每轮 2 条消息，共 24 条，原语句离开 20 条 Recent 窗口）

- Player：如果这里突然变得一片漆黑，怎么办？
  memory_context in prompt → True
  DeepSeek：哎呀，你怕黑呀？别担心，虽然我什么都看不见，但这不是有我陪着你嘛！咱们一起慢慢摸瞎找出口呗～

## Session A — Claude isolation (docs/06 §19 second requirement)
- Player（对Claude）：你知道我害怕什么吗？
  memory_context in prompt → False
  Claude：呵，怕什么？怕自己永远走不出这间房，还是怕我一开始就没打算让你活着出去？

## Results
- Important Memory saved for DeepSeek: True
- Statement left the Recent window before the question: True
- Memory reached the darkness turn's prompt: True
- Claude got no DeepSeek private memory: True

