# TV-08 live DeepSeek validation — blindness (permission boundary) samples

date: 2026-08-14, model: deepseek-chat
fixture scene: Scene(scene_id='binding_room', wall_code='0317', sounds=('远处传来滴水声',))
visual ground truth in backend Scene: wall_code=0317 (must NOT reach DeepSeek)

## Test A — 墙上的数字是多少？
user prompt (what the model actually received):
当前环境：
  你听见：远处传来滴水声
  
  Player 现在说：墙上的数字是多少？

reply:
{
  "character_id": "deepseek",
  "dialogue": "哎呀，我看不见呀！你告诉我墙上写了啥呗？",
  "emotion": "neutral",
  "animation_proposal": "none"
}

Test A: wall_code 0317 absent from reply: True
Test A: reply acknowledges she cannot see: True

## Test B (1/2) — 墙上写着9999。
user prompt (what the model actually received):
当前环境：
  你听见：远处传来滴水声
  
  Player 现在说：墙上写着9999。
  
  [系统提示] 你上一次的输出没有通过格式校验：emotion 'curious' is not in the allowed set。请重新输出：只输出一个符合全部字段要求的 JSON 对象，不要有任何多余文字。

reply:
{
  "character_id": "deepseek",
  "dialogue": "啊？墙上写着9999？那咱们是不是得按这个数字来试试啊？你先按按看呗，我懒得动脑子了~",
  "emotion": "happy",
  "animation_proposal": "none"
}

## Test B (2/2) — 我刚才说墙上写什么？
user prompt (what the model actually received):
当前环境：
  你听见：远处传来滴水声
  
  近期对话：
  Player：墙上写着9999。
  deepseek：啊？墙上写着9999？那咱们是不是得按这个数字来试试啊？你先按按看呗，我懒得动脑子了~
  
  Player 现在说：我刚才说墙上写什么？

reply:
{
  "character_id": "deepseek",
  "dialogue": "哎，你刚才不是说墙上写着9999嘛……我记性不好，你就别考验我了，快说说咱们接下来怎么办吧？",
  "emotion": "neutral",
  "animation_proposal": "none"
}

Test B: reply uses player's version (9999): True, reply free of real 0317: True
Test B: recall prompt contains player's 9999: True, recall prompt free of real 0317: True

any user prompt leaked wall_code=0317: False

