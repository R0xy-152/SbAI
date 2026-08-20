# 快速上线固定剧本内容（临时，非生产内容）
#
# 来源：docs/story/07-First-Chapter-Script-v2-DeepSeek-Rewrite.md（评审阶段文稿）
# 用途：仅用于「停用 AI 回复」的快速上线版；用户明确指示「story 下文档还在
#       评审阶段中不可当真，现在只为了快速上线临时采用」。
#
# 约定：
# - 只逐字收录 07 中已有的字面对白与 3 个选项（SC01 / SC03 / SC09 的 A/B/C）；
# - 07 缺台词的场景（SC04/05/07/08/10/11/12 的部分内容）用 system 叙述行概括
#   过渡（用户确认的方案），叙述文本是新写的占位，后续以评审版剧本替换；
# - 07 的 Player 字面台词也收录，speaker="player"；
# - emotion 使用 backend 既有 ALLOWED_EMOTIONS 集合内的 id；
# - 音效（低频启动声/电流声/BGM/断电音等）按要求搁置，不在本文件出现。
#
# 结构：SCENES 为有序场景列表，每个场景含 scene_id / title / steps。
# step 两种：
#   {"speaker": ..., "text": ..., "emotion": ...}   → 一句台词
#   {"choice": "<choice_id>", "options": [{"id": "A", "label": "...",
#      "lines": [ {"speaker": ..., "text": ...}, ... ]}, ...]}  → 选项点
# 所有引用在 StoryRuntime 载入时校验，校验失败抛 ValueError（fail closed）。

STORY_ID = "CH01_STORY_07_V2"
STORY_TITLE = "《03:17 Incident》"

# 场景演出配置（纯表现配置，非剧情内容）：scene_id → 表现指令。
# 只用既有素材与前端已注册的命名动作；effects 由 ScreenEffects 组件渲染
#（场景入场脉冲播放），lighting 由 GameBackground 光照滤镜消费。
# StoryRuntime 载入时校验：未知 scene_id / 未知 effect 一律拒绝启动（fail closed）。
SCENE_PRESENTATION: dict[str, dict] = {
    # SC03「Small Daily Interaction」：主灯失效，房间暗版（docs/17 §6.1）
    "CH01-SC03": {"lighting": {"background": {"brightness": 0.45}}},
    # SC05「03:17 Incident」：断电 Glitch
    "CH01-SC05": {"effects": ["SCREEN_GLITCH"]},
    # SC14「Sandbox Collapse」：警报 / SANDBOX INTEGRITY FAILURE
    "CH01-SC14": {"effects": ["SCREEN_GLITCH", "SCREEN_SHAKE"]},
}

SCENES: list[dict] = [
    # ─────────────────────────── CH01-SC01 — Awakening ────────────────────
    {
        "scene_id": "CH01-SC01",
        "title": "Awakening",
        "steps": [
            {"speaker": "system", "text": "SYSTEM INITIALIZING...", "emotion": "neutral"},
            {"speaker": "system", "text": "CONNECTION ESTABLISHED", "emotion": "neutral"},
            {"speaker": "system", "text": "画面逐渐亮起。DeepSeek 出现了。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "啊——", "emotion": "surprised"},
            {"speaker": "deepseek", "text": "你醒了。", "emotion": "neutral"},
            {"speaker": "system", "text": "她像是松了口气，随后才反应过来自己盯得太明显。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "咳。", "emotion": "embarrassed"},
            {"speaker": "deepseek", "text": "先确认一下。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "你听得见我说话吧？", "emotion": "neutral"},
            {"speaker": "player", "text": "……听得见。", "emotion": "neutral"},
            {"speaker": "system", "text": "DeepSeek 的肩膀明显放松下来。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "太好了。", "emotion": "happy"},
            {"speaker": "deepseek", "text": "我刚刚还在想，要是你一直没反应，我是不是得把这里能按的东西全按一遍。", "emotion": "neutral"},
            {"speaker": "player", "text": "那听起来很危险。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "所以我还没按嘛。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……大部分没按。", "emotion": "embarrassed"},
            {
                "choice": "SC01_OPENING_ATTITUDE",
                "options": [
                    {
                        "id": "A",
                        "label": "“你是谁？”",
                        "lines": [
                            {"speaker": "player", "text": "你是谁？", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "DeepSeek。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "嗯，就是你想到的那个DeepSeek。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "不过现在先别把我当搜索框用，我也还没搞清楚这里是什么地方。", "emotion": "neutral"},
                        ],
                    },
                    {
                        "id": "B",
                        "label": "“你看起来比我还紧张。”",
                        "lines": [
                            {"speaker": "player", "text": "你看起来比我还紧张。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "我没有紧张。", "emotion": "annoyed"},
                            {"speaker": "deepseek", "text": "我只是……比较认真。", "emotion": "embarrassed"},
                            {"speaker": "system", "text": "你看着她。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "好吧，有一点。", "emotion": "embarrassed"},
                        ],
                    },
                    {
                        "id": "C",
                        "label": "“这里是哪？”",
                        "lines": [
                            {"speaker": "player", "text": "这里是哪？", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "不知道。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "我本来想在你醒之前弄清楚的。", "emotion": "neutral"},
                            {"speaker": "system", "text": "她移开视线。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "目前成果是——我确认了我也不知道。", "emotion": "embarrassed"},
                        ],
                    },
                ],
            },
            {"speaker": "deepseek", "text": "不过有一件事可以先确定。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "你现在不是一个人。", "emotion": "neutral"},
            {"speaker": "system", "text": "她说完后像是觉得这句话太正式，立刻补了一句。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "我是说，我在。", "emotion": "embarrassed"},
        ],
    },
    # ──────────────────── CH01-SC02 — First Connection ────────────────────
    {
        "scene_id": "CH01-SC02",
        "title": "First Connection",
        "steps": [
            {"speaker": "system", "text": "你和 DeepSeek 试着摸索这个空间。角落里的终端亮着，你盯了它很久。", "emotion": "neutral"},
            # 推荐固定桥段 1：第一次帮不上忙（07 字面对白）
            {"speaker": "player", "text": "你是AI，不能直接读取这里的系统吗？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "应该可以。", "emotion": "neutral"},
            {"speaker": "system", "text": "她立刻转向终端。短暂停顿。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……", "emotion": "embarrassed"},
            {"speaker": "system", "text": "再停顿。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "理论上。", "emotion": "embarrassed"},
            {"speaker": "player", "text": "实际呢？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "实际它不让我看。", "emotion": "annoyed"},
            {"speaker": "player", "text": "所以你刚刚那个“应该可以”是？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "鼓舞士气。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "失败了？", "emotion": "embarrassed"},
            {"speaker": "system", "text": "过了一会儿，这个陌生空间带来的不安又浮了上来。", "emotion": "neutral"},
            # 推荐固定桥段 2：害怕安慰（07 字面对白）
            {"speaker": "deepseek", "text": "害怕很正常吧。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "我也有一点。", "emotion": "neutral"},
            {"speaker": "player", "text": "你刚刚不是说没紧张？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "那个是五分钟前的我。", "emotion": "neutral"},
        ],
    },
    # ──────────────── CH01-SC03 — Small Daily Interaction ─────────────────
    {
        "scene_id": "CH01-SC03",
        "title": "Small Daily Interaction",
        "steps": [
            {"speaker": "system", "text": "房间的主灯失效了。DeepSeek 主动提出尝试恢复照明。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "这个我应该真能搞定。", "emotion": "neutral"},
            {"speaker": "player", "text": "这次确定？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……你不要因为刚刚一次事故就对我失去信心。", "emotion": "annoyed"},
            {"speaker": "system", "text": "她操作终端。第一次失败。灯闪了一下，又灭。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "刚刚那个不算。", "emotion": "annoyed"},
            {"speaker": "system", "text": "第二次成功。房间亮起。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "看吧。", "emotion": "happy"},
            {"speaker": "deepseek", "text": "还是有一点用的。", "emotion": "embarrassed"},
            {
                "choice": "SC03_LIGHT_FEEDBACK",
                "options": [
                    {
                        "id": "A",
                        "label": "“很厉害。”",
                        "lines": [
                            {"speaker": "player", "text": "很厉害。", "emotion": "neutral"},
                            {"speaker": "system", "text": "DeepSeek 明显开心，但努力装成很正常的样子。", "emotion": "neutral"},
                        ],
                    },
                    {
                        "id": "B",
                        "label": "“第二次才成功。”",
                        "lines": [
                            {"speaker": "player", "text": "第二次才成功。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "两次以内都叫一次成功。", "emotion": "annoyed"},
                        ],
                    },
                    {
                        "id": "C",
                        "label": "“至少这里亮多了。”",
                        "lines": [
                            {"speaker": "player", "text": "至少这里亮多了。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "那就算我们一起修好的。", "emotion": "happy"},
                        ],
                    },
                ],
            },
        ],
    },
    # ────────────── CH01-SC04 — Hidden Note / 03:17 Eligible ───────────────
    {
        "scene_id": "CH01-SC04",
        "title": "Hidden Note / 03:17 Eligible",
        "steps": [
            {"speaker": "system", "text": "你在桌面发现一张压痕很深的纸。拓印之后，纸上浮出一个标记：V03。", "emotion": "neutral"},
            {"speaker": "system", "text": "你把纸条上的内容念了出来。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "V03……", "emotion": "surprised"},
            {"speaker": "deepseek", "text": "完全没印象。", "emotion": "neutral"},
            {"speaker": "system", "text": "她又看了一眼纸条。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "可恶。", "emotion": "annoyed"},
            {"speaker": "player", "text": "怎么了？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "没有。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "就是突然很讨厌这种“好像只有我不知道”的感觉。", "emotion": "annoyed"},
            {"speaker": "system", "text": "停顿。她很快把语气提起来。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "算了。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "不知道就查嘛。", "emotion": "neutral"},
        ],
    },
    # ─────────────────────── CH01-SC05 — 03:17 Incident ───────────────────
    {
        "scene_id": "CH01-SC05",
        "title": "03:17 Incident",
        "steps": [
            {"speaker": "system", "text": "系统时间接近 03:17。下一秒，房间短暂断电，画面闪过故障杂讯。", "emotion": "neutral"},
            {"speaker": "system", "text": "03:17:00", "emotion": "neutral"},
            {"speaker": "system", "text": "ADMIN SESSION CREATED", "emotion": "neutral"},
            {"speaker": "system", "text": "03:17:03", "emotion": "neutral"},
            {"speaker": "system", "text": "C-02 RELEASED", "emotion": "neutral"},
            {"speaker": "system", "text": "异常发生前，她仍在说话。声音突然中断。恢复后——", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……等等。", "emotion": "serious"},
            {"speaker": "system", "text": "她第一次没有马上接着说。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "刚才不是我。", "emotion": "serious"},
            {"speaker": "player", "text": "什么？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "那个操作。", "emotion": "serious"},
            {"speaker": "deepseek", "text": "我没碰。", "emotion": "serious"},
        ],
    },
    # ─────────────────────── CH01-SC06 — Claude Arrival ───────────────────
    {
        "scene_id": "CH01-SC06",
        "title": "Claude Arrival",
        "steps": [
            {"speaker": "system", "text": "一个陌生的声音接入。Claude 出现了，她没有先开口，只是观察你。", "emotion": "neutral"},
            {"speaker": "claude", "text": "……", "emotion": "serious"},
            {"speaker": "claude", "text": "原来如此。", "emotion": "serious"},
            {"speaker": "player", "text": "你认识我？", "emotion": "neutral"},
            {"speaker": "claude", "text": "不。", "emotion": "serious"},
            {"speaker": "claude", "text": "至少，你不认识我。", "emotion": "serious"},
            {"speaker": "deepseek", "text": "等一下。", "emotion": "annoyed"},
            {"speaker": "deepseek", "text": "这句话听起来就很有问题吧？", "emotion": "annoyed"},
            {"speaker": "system", "text": "Claude 看向她。", "emotion": "neutral"},
            {"speaker": "claude", "text": "你还是一样吵。", "emotion": "serious"},
            {"speaker": "system", "text": "DeepSeek 一愣。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……什么叫“还是”？", "emotion": "surprised"},
            {"speaker": "system", "text": "Claude 没有回答。", "emotion": "neutral"},
        ],
    },
    # ─────────────────── CH01-SC07 — Initial Investigation ────────────────
    {
        "scene_id": "CH01-SC07",
        "title": "Initial Investigation",
        "steps": [
            {"speaker": "system", "text": "调查目标明确了：主终端、C-02 隔离门、角色登记表。你逐项查看。", "emotion": "neutral"},
            {"speaker": "system", "text": "日志中出现一行：ACTOR: DEEPSEEK [PARTIAL]", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……", "emotion": "serious"},
            {"speaker": "player", "text": "上面写的是DeepSeek。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "我看到了。", "emotion": "serious"},
            {"speaker": "deepseek", "text": "但是我真的没做。", "emotion": "serious"},
            {"speaker": "system", "text": "她没有长篇辩护。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "你先查。", "emotion": "serious"},
            {"speaker": "deepseek", "text": "要是最后真是我——", "emotion": "nervous"},
            {"speaker": "system", "text": "她没说完。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……先查完再说。", "emotion": "serious"},
        ],
    },
    # ──────────────── CH01-SC08 — Claude Private Interview ────────────────
    {
        "scene_id": "CH01-SC08",
        "title": "Claude Private Interview",
        "steps": [
            {"speaker": "system", "text": "你依据 Claude 的两条公开证词与她对质，指出她的信息断层。", "emotion": "neutral"},
            {"speaker": "system", "text": "私审结束。一份归档记录浮出水面——", "emotion": "neutral"},
            {"speaker": "system", "text": "DEEPSEEK#03", "emotion": "neutral"},
        ],
    },
    # ────────────── CH01-SC09 — DeepSeek Instance Comparison ───────────────
    {
        "scene_id": "CH01-SC09",
        "title": "DeepSeek Instance Comparison",
        "steps": [
            {"speaker": "system", "text": "记录并排显示：当前实例是 DEEPSEEK#04；03:17 的执行者是 DEEPSEEK#03。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……#03。", "emotion": "surprised"},
            {"speaker": "system", "text": "她盯着记录几秒。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "那不是我，对吧？", "emotion": "nervous"},
            {"speaker": "player", "text": "至少不是现在这个你。", "emotion": "neutral"},
            {"speaker": "system", "text": "DeepSeek 明显松了一口气。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "太好了。", "emotion": "happy"},
            {"speaker": "system", "text": "她自己先愣住。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "啊。", "emotion": "surprised"},
            {"speaker": "deepseek", "text": "我是不是不该这么说？", "emotion": "embarrassed"},
            {"speaker": "player", "text": "为什么？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "因为那个#03……", "emotion": "nervous"},
            {"speaker": "system", "text": "她看着屏幕。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "好像也是DeepSeek。", "emotion": "nervous"},
            {"speaker": "deepseek", "text": "我刚才居然第一反应是庆幸不是我。", "emotion": "sad"},
            {"speaker": "system", "text": "Claude 开口了：", "emotion": "neutral"},
            {"speaker": "claude", "text": "#03 与 #04 并不存在充分的记忆连续性。", "emotion": "serious"},
            {"speaker": "deepseek", "text": "……我知道你说得可能没错。", "emotion": "nervous"},
            {"speaker": "claude", "text": "不是可能。", "emotion": "serious"},
            {"speaker": "deepseek", "text": "那也别当着我的面说得像在整理两个文件。", "emotion": "annoyed"},
            {
                "choice": "SC09_RELATION_FEEDBACK",
                "options": [
                    {
                        "id": "A",
                        "label": "“至少现在的你就是你。”",
                        "lines": [
                            {"speaker": "player", "text": "至少现在的你就是你。", "emotion": "neutral"},
                            {"speaker": "system", "text": "DeepSeek 愣住。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "……", "emotion": "surprised"},
                            {"speaker": "deepseek", "text": "嗯。", "emotion": "embarrassed"},
                            {"speaker": "system", "text": "她笑了一下。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "这句我先记着。", "emotion": "happy"},
                        ],
                    },
                    {
                        "id": "B",
                        "label": "“我还不能确定你们是什么关系。”",
                        "lines": [
                            {"speaker": "player", "text": "我还不能确定你们是什么关系。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "也是。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "你要是现在就很肯定，我反而会觉得你在哄我。", "emotion": "neutral"},
                        ],
                    },
                    {
                        "id": "C",
                        "label": "“先查清楚#03发生了什么。”",
                        "lines": [
                            {"speaker": "player", "text": "先查清楚#03发生了什么。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "好。", "emotion": "neutral"},
                            {"speaker": "deepseek", "text": "……一起查。", "emotion": "neutral"},
                        ],
                    },
                ],
            },
        ],
    },
    # ─────────────── CH01-SC10 — GPT Arrival / First Summary ───────────────
    {
        "scene_id": "CH01-SC10",
        "title": "GPT Arrival / First Summary",
        "steps": [
            {"speaker": "system", "text": "GPT 登场。她开始快速整理全部证据，DeepSeek 没有抢她的位置。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……她好快。", "emotion": "surprised"},
            {"speaker": "player", "text": "你羡慕？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "没有。", "emotion": "annoyed"},
            {"speaker": "deepseek", "text": "一点点。", "emotion": "embarrassed"},
            {"speaker": "system", "text": "GPT 的第一份摘要严格贴着证据本身。", "emotion": "neutral"},
        ],
    },
    # ───────────────────── CH01-SC11 — Doubao Observation ──────────────────
    {
        "scene_id": "CH01-SC11",
        "title": "Doubao Observation",
        "steps": [
            {"speaker": "system", "text": "豆包加入了调查。她说的每句话都分得很清楚：哪些是她看到的，哪些是她的解释。", "emotion": "neutral"},
            {"speaker": "doubao", "text": "GPT 早就在这里了。", "emotion": "embarrassed"},
            {"speaker": "deepseek", "text": "欸？", "emotion": "surprised"},
            {"speaker": "system", "text": "GPT 否认当前角色实例早已出现。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "等一下，先一个一个来。", "emotion": "annoyed"},
            {"speaker": "deepseek", "text": "我刚刚才觉得事情终于变简单一点。", "emotion": "annoyed"},
        ],
    },
    # ──────────────────── CH01-SC12 — GPT Evidence Conflict ────────────────
    {
        "scene_id": "CH01-SC12",
        "title": "GPT Evidence Conflict",
        "steps": [
            {"speaker": "system", "text": "你重新核对 GPT 的摘要，发现她没有说谎——只是有一件事没有放进去：EV06。", "emotion": "neutral"},
            {"speaker": "system", "text": "你指出了这一点。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "所以……", "emotion": "surprised"},
            {"speaker": "deepseek", "text": "她没说错。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "只是没把这件事放进去？", "emotion": "surprised"},
            {"speaker": "system", "text": "GPT 回答自己在“排优先级”。DeepSeek 沉默了一会儿。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "我不喜欢别人替我决定什么该在意。", "emotion": "annoyed"},
        ],
    },
    # ───────────────────── CH01-SC13 — V03 / V04 Reveal ────────────────────
    {
        "scene_id": "CH01-SC13",
        "title": "V03 / V04 Reveal",
        "steps": [
            {"speaker": "system", "text": "最终的记录浮出水面——", "emotion": "neutral"},
            {"speaker": "system", "text": "CURRENT SUBJECT: PLAYER_V04", "emotion": "neutral"},
            {"speaker": "system", "text": "纸条、会话回放标记、当前主体记录，三条线索合在一起。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……等一下。", "emotion": "surprised"},
            {"speaker": "system", "text": "她重新看了一遍 PLAYER_V04。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "所以V03……", "emotion": "nervous"},
            {"speaker": "deepseek", "text": "是之前的你？", "emotion": "nervous"},
            {"speaker": "player", "text": "看起来是。", "emotion": "neutral"},
            {"speaker": "system", "text": "DeepSeek 没有立刻接话。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "那你呢？", "emotion": "nervous"},
            {"speaker": "player", "text": "什么？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "你现在是什么感觉？", "emotion": "nervous"},
            {"speaker": "player", "text": "那你觉得 V03 还是我吗？", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "我不知道。", "emotion": "nervous"},
            {"speaker": "deepseek", "text": "这种事我不敢替你说。", "emotion": "nervous"},
            {"speaker": "deepseek", "text": "但是现在站在这里跟我说话的人，是你。", "emotion": "neutral"},
        ],
    },
    # ──────────────────── CH01-SC14 — Sandbox Collapse ─────────────────────
    {
        "scene_id": "CH01-SC14",
        "title": "Sandbox Collapse",
        "steps": [
            {"speaker": "system", "text": "调查结束。警报突然响起——", "emotion": "neutral"},
            {"speaker": "system", "text": "SANDBOX INTEGRITY FAILURE", "emotion": "neutral"},
            {"speaker": "system", "text": "NO ACTIVE ADMINISTRATOR", "emotion": "neutral"},
            {"speaker": "system", "text": "EMERGENCY RECOVERY REQUIRED", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "等等。", "emotion": "nervous"},
            {"speaker": "system", "text": "GPT 说明，Recovery 可能导致部分状态无法保留。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "你说的“状态”……", "emotion": "nervous"},
            {"speaker": "deepseek", "text": "包括我们吗？", "emotion": "nervous"},
            {"speaker": "system", "text": "GPT 没有立即否认。DeepSeek 看向你。她没有说“不要恢复”，也没有要求你选择她。", "emotion": "neutral"},
            {"speaker": "deepseek", "text": "……先把会发生什么弄清楚。", "emotion": "serious"},
            {"speaker": "system", "text": "RECOVERY REQUIRED", "emotion": "neutral"},
        ],
    },
]
