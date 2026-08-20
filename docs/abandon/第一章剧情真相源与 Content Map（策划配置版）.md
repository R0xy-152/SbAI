# 第一章剧情真相源与 Content Map（策划配置版）

## 0. 文档用途

用于：

- 程序实现；
- 剧情节点配置；
- Agent开发；
- 测试验收。

优先级：

剧情事实 > 本文档 > 其他配置文档。

---

# 1. 主线流程总表

|阶段|节点|触发|结果|
|-|-|-|-|
|Opening|N00|游戏开始|进入Sandbox|
|纸条事件|EV01|调查热点|获得03:17线索|
|03:17事件|INCIDENT_0317|EV01+调查行为|Claude出现|
|Claude调查|EV02-05|完成调查|获得INF01|
|GPT登场|GPT_APPEAR|INF01完成|GPT加入|
|第一次Summary|GPT_SUMMARY_01|GPT加入|整理证据|
|豆包登场|DOUBAO_APPEAR|Summary完成|开放观察线|
|豆包调查|EV08|完成调查|获得异常证据|
|GPT二次分析|GPT_SUMMARY_02|EV08完成|发现Sandbox问题|
|GPT私审|CT04|满足条件|获得核心推论|
|Recovery|RECOVERY|SANDBOX异常|进入最终阶段|
|结局|END|Recovery结果|三出口|

---

# 2. 角色配置

## DeepSeek

定位：

引导角色。

功能：

- Opening介绍；
- 情绪稳定；
- 基础信息提供。

隐藏信息：

拥有部分早期Sandbox记录。


---

## Claude

定位：

悬疑核心角色。

登场：

INF01之前。

规则：

Truth Contract。

允许：

- 回避；
- 拒绝回答；
- 权限不足。

禁止：

- 主动编造事实。


私审目标：

确认：

- 她为何知道03:17；
- 她为何隐藏信息。


---

## GPT

定位：

逻辑分析角色。

登场：

INF01之后。


能力：

- Evidence排序；
- Summary；
- Claim验证。


限制：

不能读取玩家未获得Evidence。


---

## 豆包

定位：

观察误差来源。


能力：

提供非结构化信息。


特点：

低准确率。

高关联性。


---

# 3. Evidence配置

## EV01

名称：

神秘纸条。


来源：

Sandbox异常区域。


玩家信息：

03:17相关提示。


真实用途：

开启Incident Gate。


---

## EV02-05

用途：

建立Claude阶段矛盾。


要求：

每个Evidence必须：

- 支持至少一个Claim；
- 或推翻一个错误Claim。


---

## EV08

用途：

证明观察层存在偏差。


效果：

开放GPT第二阶段分析。


---

## EV10

必须补充：

Evidence列表。

要求：

明确：

- 获取方式；
- 所属节点；
- 支持结论。


---

# 4. Claim系统

## C01

主题：

03:17只是系统错误。


状态：

错误。


---

## C02

主题：

Claude导致异常。


状态：

错误。


---

## C03

主题：

Sandbox正在循环。


状态：

正确。


---

# 5. Conflict配置

## CT01

对象：

Claude信息。

目的：

建立怀疑。


---

## CT04

对象：

GPT推理。

目的：

进入Recovery。


---

# 6. Recovery配置

## RECOVERY_START

条件：

```
EV全部完成
+
GPT Summary完成
+
Integrity Failure触发
```


---

## Security Review

目标：

判断角色可信度。


输入：

- Evidence；
- Character Statement；
- Player选择。


---

## Administrator Permission Game

结果：

产生：

- delegated；
- consent；
- self proof。


---

# 7. 结局规则

## BAD_END_DELEGATED

条件：

玩家授权AI管理权限。


结果：

```
END_DELEGATED=true
```


表现：

Sandbox稳定。

玩家失去主动权。


---

## BAD_END_CONSENT

条件：

玩家接受永久留在Sandbox。


结果：

```
STAY_SANDBOX=true
```


表现：

AI陪伴。

现实断开。


---

## TO_BE_CONTINUED

条件：

完成最终自证。


结果：

```
REALITY_RETURN=true
AI_CONNECTION=true
```


表现：

现实恢复。

AI仍存在。


---

# 8. 实现约束

## 必须保持

- GPT INF01后出现；
- 03:17为Gate，不是时间事件；
- 第一章不解释终极谜底；
- 普通调查错误不可阻断主线。


---

# 9. 未决事项

C1-C4：

进入后续版本决策。


包括：

- Claude Truth Contract扩展；
- 自由文本结局映射；
- 纸条来源；
- 第二章关联内容。