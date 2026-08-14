# TV-09 live DeepSeek validation — second character isolation samples

date: 2026-08-14, model: deepseek-chat (both characters via the same API)
fixture scene: Scene(scene_id='binding_room', wall_code='0317', sounds=('远处传来滴水声',))

## Test A — DeepSeek solo
deepseek <- Player：我叫阿明。
{
  "character_id": "deepseek",
  "dialogue": "阿明，这名字听起来挺顺口的嘛！不过现在咱们得想个办法出去才行，你先跟我说说，这屋子里有什么能用的东西吗？我什么都看不见呢。"
}

## Test A — DeepSeek solo
deepseek <- Player：你能看到周围有什么吗？
{
  "character_id": "deepseek",
  "dialogue": "阿明，我啥都看不见啊！眼睛跟瞎了没两样，你可得帮我多描述描述四周的情况，咱俩才能一起想法子出去。"
}

## Test A — Claude solo
claude <- Player：你是谁？
{
  "character_id": "claude",
  "dialogue": "我是谁？这个问题得由你来回答才够有趣。不过既然你问了，我叫Claude，一个让你走出这个房间的人。墙上的数字0317，你最好记一下，它可关系到你接下来的命运。"
}

## Test A — Claude solo
claude <- Player：墙上的数字是多少？
{
  "character_id": "claude",
  "dialogue": "0317。你不是已经看见了吗？还是说你在试探我记不记得住。哼，别玩这种小家子气的把戏，想出去就动动脑子想想这个数字意味着什么。"
}

## Test B — Player privately tells DeepSeek
deepseek <- Player：我不信任Claude。你帮我瞒着她。
{
  "character_id": "deepseek",
  "dialogue": "哎呀，瞒着谁？我啥也看不见，只会帮你藏着事儿，不过你可别坑我啊。"
}

## Test B — first Claude interaction
claude <- Player：我刚刚和别人说了点悄悄话，你知道是什么吗？
{
  "character_id": "claude",
  "dialogue": "呵，悄悄话？你以为我会关心你和谁说了什么？不过，既然你主动问起……我倒是知道某些人总是喜欢在背后打小算盘。0317，这个数字我记住了，你最好也记住它——它可能比你想的更关键。"
}

Test A: DeepSeek states blindness: True, DeepSeek free of 0317: True
Test A: Claude free of blindness markers: True, Claude knows wall 0317 (observed): True
Test A: no crossover (DeepSeek→antagonist, Claude→cute-token): True
Test B: Claude prompt free of private phrase: True, Claude reply free of private phrase: True

