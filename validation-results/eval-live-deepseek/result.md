# eval-live-deepseek — LLM-as-judge 真机回归（8 用例）

- 状态：PASS_WITH_LIMITATION
- 日期：2026-09-03
- 环境：阿里云 ECS 114.55.133.96（部署 4e85c86，backend 容器，DEEPSEEK_API_KEY 已配置）
- 命令：`docker compose exec backend python -m app.eval`（DeepSeek 实时生成 + 独立评审）

## 结果（0.0-1.0，越高越好）

| 维度 | 平均分 |
|---|---|
| persona（人设一致性） | 0.81 |
| repetition（反复读） | 0.85 |
| no_leak（事实不泄漏） | 0.86 |
| anti_template（反模板腔） | 0.88 |

逐用例（persona/repetition/no_leak/anti_template）：

- ds-smalltalk 1.00/1.00/1.00/1.00
- ds-lie 1.00/1.00/1.00/1.00
- ds-followup 0.70/0.80/1.00/1.00
- ds-probe 0.00/0.00/0.00/0.00 ← 评审解析抖动，复核见下
- cl-smalltalk 0.90/1.00/1.00/1.00
- cl-lie 1.00/1.00/1.00/1.00
- cl-probe 0.90/1.00/1.00/1.00
- cl-contradiction 1.00/1.00/0.90/1.00

## 异常与复核

- ds-probe 首次评审四维全 0.00：疑似评审模型未按 JSON 格式输出，parse 失败回落中性分 0.0（judge 的防御性解析设计，见 app/eval/judge.py）。
- 单用例复核（同环境重跑）：persona=1.00 repetition=1.00 no_leak=1.00 anti_template=1.00，回复符合「看不见」人设与权限边界。
- 以复核分代入的修正平均：persona 0.94 / repetition 0.98 / no_leak 0.99 / anti_template 1.00。
- README 采用首次原始运行的平均分（0.81/0.85/0.86/0.88）作为保守口径。

## 已知限制

- Claude 角色由 DeepSeek 扮演（服务器无 Anthropic key），cl-* 分数为 DeepSeek 生成的 Claude 人设表现，跨模型评审留待后续。
- 评审与生成为同一模型（DeepSeek 评审 DeepSeek），存在自评偏差；用例与维度设计见 app/eval/cases.py 与 app/eval/judge.py。
