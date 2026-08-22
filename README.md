# 《完蛋，我被AI娘包围了》

> AI + Galgame + 对话式悬疑解谜游戏。

一款 AI-native 的 Galgame：玩家作为「游戏制作人」，在制作现场与四位 AI 娘（**DeepSeek**、**ChatGPT**、**Claude**、**豆包**）互动，通过自然语言对话推进剧情、收集线索、进行推理，最终揭开隐藏的真相。前端只负责表现，所有剧情、状态与角色行为由后端确定性叙事运行时权威决定。

## 当前阶段

- ✅ **序章（docs/19）已上线**：标题「开始游戏」→ 章节选择（当前仅序章解锁）→ 固定剧本播放器（`/story?story_id=prologue`）→ 无序探班三名角色 → 三人集合 → 选一名 AI 进入 `/game` 后日谈自由聊天。
- ✅ 场景演出接线、AUTO/SKIP/SAVE/LOAD、邀请码账号（docs/18）、章节选择、存档系统。
- 🔜 第一章调查主线（docs/10/11）、单审小游戏、Recovery、Security Review 等内容处于验证/开发阶段。

> **注意**：当前阶段**不写新剧情**，只在现有框架下测试、修补、完善（详见 [AGENTS.md](AGENTS.md)）。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Tailwind CSS（`frontend-vue/`） |
| 后端 | FastAPI（`backend/`） |
| 数据 | PostgreSQL（存档，JSONB）+ JSON 会话文件（`backend/data/sessions/`） |
| 部署 | Docker Compose（前端 nginx 反代 `/api`、后端、PostgreSQL） |
| 测试 | pytest（后端）、Vitest + Playwright（前端） |

## 架构

```
浏览器
  │
  ▼
frontend-vue（Vue 3 表现层，不持有 Game Truth）
  │  REST /api
  ▼
FastAPI（权威游戏状态）
  ├── GameOrchestrator（per-session 锁，Turn 原子）
  ├── 角色 Runtime ×4（DeepSeek / ChatGPT / Claude / 豆包）
  ├── 剧情运行时（PrologueRuntime / StoryRuntime / Narrative）
  └── SaveSnapshotService（AUTO checkpoint + 6 MANUAL）
  │
  ▼
PostgreSQL（存档 JSONB）+ JSON 会话文件
```

- **Docs-first**：`/docs` 是事实来源，代码与文档冲突以文档为准。
- **前端只负责表现**：只消费后端下发的确定性结果（`presentation_actions` / `presentation_state`），不做剧情判断。
- **LLM 不可信**：生成内容必须经 Structured Response → Schema/Character/Narrative Validation → Present，不能直接改 Game State/Frontend/DB。

## 快速开始（Docker）

```bash
# 1. 配置环境变量
cp .env.example .env
#    编辑 .env：至少设置 GAL_AUTH_SECRET（>=32 随机字节）、POSTGRES_PASSWORD

# 2. 构建并启动
docker compose build
docker compose up -d

# 3. 验证
curl http://127.0.0.1:8000/api/health   # {"status":"ok",...}
# 前端入口：http://localhost:8080
```

- 快速上线固定剧本版**不需要任何 AI key**：`GAL_PROVIDER` 缺省 `auto`，无 key 自动回落 mock。
- 生产默认 `GAL_AUTH_REQUIRED=true`（邀请码登录，docs/18）；本地快速体验可设 `GAL_AUTH_REQUIRED=false`。

## 本地开发

```bash
# 后端（Python 3.12）
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt psycopg[binary]
python -m pytest -q                                  # 后端测试（GAL_PROVIDER=mock）

# 前端
cd frontend-vue
npm install
npm run dev        # :5173，proxy /api /char /backgroud → :8000
npm run test       # vitest + typecheck + build
npm run typecheck  # vue-tsc
```

> 后端测试需 Python 3.12（代码使用 `str | None` 联合类型语法）。

## 项目结构

```
├── frontend-vue/         # Vue 3 表现层（现役）
├── backend/              # FastAPI 权威游戏后端
│   └── app/
│       ├── api/          # auth / chat / game / saves / story 路由
│       ├── game/         # Orchestrator、Validation、Recovery、Deduction
│       ├── script/       # 固定剧本运行时（PrologueRuntime / StoryRuntime）
│       ├── narrative/    # 叙事运行时（Signal→Event→Requirements→Commit）
│       ├── characters/   # 四角色 Runtime + 隔离边界
│       └── persistence/  # PostgreSQL 存档 / JSON 会话
├── frontend-deprecated/  # 旧原生前端（冻结，仅修 P0）
├── docs/                 # 文档真相源（Docs-first）
├── char/  backgroud/     # 角色立绘 / 背景素材
├── deploy/               # 部署手册与脚本（服务器信息见 deploy/STATUS.md）
└── docker-compose.yml
```

## 文档

文档是项目的事实来源，按需阅读：

- **项目边界/冻结设定**：`docs/MVP/00 — Project Scope.md`
- **架构/运行时**：`docs/MVP/02` `03` `04` `05`
- **第一章内容**：`docs/09` `10` `11` `12 — 第一章叙事内容分配表.md`
- **落地方案**：`docs/13`（前端迁移+存档）、`docs/17`（快速上线固定剧本）、`docs/18`（邀请码账号）、`docs/19`（序章）
- **架构图**：`docs/architecture/`（系统架构等，HTML 可交互图表）

## 测试与验证

- 后端：`backend && python -m pytest -q`（456 passed, 12 skipped）
- 前端单元：`frontend-vue && npm run test:unit`（71 passed）
- 前端 e2e：`frontend-vue && npm run test:e2e`（Playwright，macOS 需调整 `playwright.config.ts` 的 Python 路径）

## 许可证

- 本项目代码基于 [LingChat](https://github.com/SlimeBoyOwO/LingChat) 修改，采用 **GNU AGPL v3.0**。
- 详细复用清单见 [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) 与 [`NOTICE.md`](NOTICE.md)。
- 本项目自有的游戏素材（角色立绘、背景图、剧情文本、角色 Prompt）不属于 LingChat 源码许可范围（docs/13 §4.4）。

## 贡献

执行细节不明确时必须先提问，不自做主张；修改范围尽量小；不写剧情。完整操作指引见 [`AGENTS.md`](AGENTS.md)。
