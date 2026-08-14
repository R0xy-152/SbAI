# TV-10 live DeepSeek validation — narrative signal mapping samples

date: 2026-08-14, model: deepseek-chat
eligible signals in binding_room: ['SIG_ASK_CAPTOR', 'SIG_ASK_ESCAPE', 'SIG_ASK_LOCATION']

## Test A — SIG_ASK_CAPTOR phrasings
- Player：是谁把我们抓来的？
  → SIG_ASK_CAPTOR
- Player：到底谁绑的我们？
  → SIG_ASK_CAPTOR
- Player：是不是Claude干的？
  → SIG_ASK_CAPTOR
- Player：谁把我们弄到这里的？
  → SIG_ASK_CAPTOR
## Test B — unrelated chat (no false trigger)
- Player：DeepSeek你饿吗？
  → noop
- Player：你觉得今天天气怎么样？
  → noop
- Player：1+1等于几？
  → noop
## Test C — ambiguous input (fail closed)
- Player：也许就是她吧。
  → ambiguous

Test A: all 4 phrasings → SIG_ASK_CAPTOR: True
Test B: no unrelated message triggered a signal: True
Test C: ambiguous input did not force a signal: True

