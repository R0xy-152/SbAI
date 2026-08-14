# AGENT.MD

## 目的

本文件用于约束 Codex / Agent 在本仓库中的开发行为。  
项目需求与设计事实以 `/docs` 为准，本文件不重复定义业务规则。

## 开始任务前

先判断任务属于哪个模块，只读取必要文档，避免无关上下文污染。

- 项目边界：`docs/00-project-scope.md`
- 当前 MVP：`docs/01-mvp-requirements.md`
- 系统架构：`docs/02-system-architecture.md`
- 剧情运行：`docs/03-narrative-runtime.md`
- 角色运行：`docs/04-character-runtime.md`
- Memory：`docs/05-memory-design.md`
- 技术验证顺序：`docs/06-tech-validation-plan.md`

不要默认每次读取全部文档。

## 开发原则

1. 先满足当前 Tech Validation，不提前扩展正式游戏功能。
2. 不因实现方便绕过已有模块边界。
3. LLM、Frontend、Memory 都不能成为 Game State 的隐式真相源。
4. 不把临时 POC / Fixture 当成正式剧情或正式配置。
5. 不为了“技术栈丰富”主动加入未被当前验证需要的基础设施。
6. 修改范围尽量小；不要顺手重构无关代码。
7. 未确认的设计问题不要自行永久固化，优先使用最小可替换实现。

## Agent 修改规则

- 若代码实现与 `/docs` 明确冲突：停止该实现，优先按文档修正。
- 若现有文档之间存在冲突：不要自行选择一个版本继续开发，应明确指出冲突。
- 若任务要求改变项目 Scope 或核心架构：先更新对应文档，再改代码。
- 普通实现细节无需新增文档，除非形成长期架构决策。

## Tech Validation

开发期间先确认当前对应的 `TV-xx`。

一个验证项只有在具备可复现证据后才能视为完成。  
测试结果、日志和截图放入验证结果目录，不要把运行日志写回规范文档。

失败时先定位负责层：

- UI / 动画 → Frontend
- API / Provider → Integration
- 结构化输出 / Persona → Character Runtime
- 剧情状态 → Narrative Runtime
- 上下文 / 串台 / 记忆 → Memory / Context
- Session 丢失 → Persistence

不要为了修一个局部问题同时修改多个层。

## 代码与配置

- 剧情内容、角色配置、Scene 等尽量与 Runtime 代码分离。
- API Key / Secret 不得写入前端、仓库或提交记录。
- 新依赖必须有当前任务的直接理由。
- 优先保持代码可读、可测试、可替换，不做当前阶段不需要的抽象。

## 完成任务时

输出至少说明：

1. 完成了什么。
2. 修改了哪些文件。
3. 如何验证。
4. 当前结果是 PASS、PASS_WITH_LIMITATION 还是仍有问题。
5. 已知限制或下一项阻塞是什么。

不要在没有验证证据时声称功能已经完成。

当你执行一项任务发现有任何执行细节不明确时，你必须向我提问，而不是自做主张。
在我回答之后仍有不明确的执行细节时，你需要向我追问，直到了解了所有细节。
你可以在提问前查阅你需要了解的所有代码，并在了解了代码逻辑后再向我提问。