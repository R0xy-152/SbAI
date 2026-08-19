# docs/13 Task 6 — 实现 Backend Save Snapshot

**状态：PASS**
**日期：2026-08-19**
**范围：** docs/13 §14-21 / Task 6（GameSave / SaveSnapshotService / SaveRepository / Save API / schema version；1 Auto + 6 Manual；PostgreSQL + JSON 双后端）

## 1. 完成了什么

实现 Backend 存档快照层（docs/13 §14.2：Backend Capture，Frontend 不提交游戏状态）：

- **GameSave**（`backend/app/save/repository.py`）：存档记录实体（id / player_id / slot_type / slot_index / title / source_session_id / schema_version / snapshot / chapter_id / phase / created_at / updated_at）。`info()` 只下发 slot 元数据，snapshot 不下发浏览器（docs/13 §29）。
- **SaveRepository 接口 + 双实现**：
  - `JsonSaveRepository`：JSON 文件（TV-14 同款 fixture，原子写 tmp + os.replace，docs/13 §18 全或无）；无 PostgreSQL 时兜底。
  - `PostgresSaveRepository`：PostgreSQL JSONB（docs/13 §16 目标）；id 主键 + 每 player 每 slot 的 partial unique index（§16.1）；单事务 upsert（§18.1）；表幂等自建。
- **SaveSnapshotService**（`backend/app/save/service.py`）：`capture`（单次权威 `orchestrator._snapshot()` 读取 → Narrative / Script cursor / Game State / 逐角色 Memory / Messages + visibility / Evidence / Claim / Contradiction / Inference / Private Interview / Scene / Presence / Emotion，docs/13 §17）+ `presentation` 稳定态（scene / present_characters / emotion / last_dialogue）；`save_manual` / `save_auto`（覆盖保留 slot id，§16.1）；`list_saves`（§20.1：auto + manual[6]）；`load_save`（§19.1：新建 Active Session；schema_version 不支持 → 明确失败）；`delete_manual`。
- **Schema version**：`SCHEMA_VERSION = 1`，每份 snapshot 带 `schema_version`；未来结构变化必须 bump + Migration（§16.2）。
- **Orchestrator**（`backend/app/game/orchestrator.py`）新增：`import_snapshot`（§19.1：快照 → 新 session_id + restore + 持久化）、`gameview_state`（§20.3：Load 返回的初始 GameViewState = presentation_state + history）。
- **Save API**（`backend/app/api/saves.py`，docs/13 §20）：
  - `GET /api/saves?player_id=` → `{auto, manual:[6]}`
  - `POST /api/saves/manual/{slot}`（player_id / session_id / title）
  - `POST /api/saves/auto`（player_id / session_id）
  - `POST /api/saves/{save_id}/load` → `{session_id, state, history}`（404 / 409 schema / 422 校验）
  - `DELETE /api/saves/manual/{slot}?player_id=`
- **main.py**：`app.state.save_service` 接线；`GAL_SAVE_BACKEND=postgres`（需 `GAL_POSTGRES_DSN`）用 PG，默认 JSON。
- **docker-compose.yml**：新增 `backend`（FastAPI + psycopg，GAL_SAVE_BACKEND=postgres）+ `postgres`（16-alpine，healthcheck，volume）服务，`frontend-vue` 依赖 backend；新增 `backend/Dockerfile`、`.dockerignore`。docs/13 §30 三服务目标达成。
- 新增 `psycopg[binary]` 依赖（Docker 镜像内已装；本地 venv 亦装以跑 PG 测试）。

## 2. 修改了哪些文件

- `backend/app/save/__init__.py`、`backend/app/save/repository.py`、`backend/app/save/service.py`（新增，Save 层）
- `backend/app/api/saves.py`（新增，Save API）
- `backend/app/game/orchestrator.py`（+`import_snapshot` / `gameview_state`）
- `backend/app/main.py`（save_service 接线 + PG/JSON 选择）
- `backend/Dockerfile`、`.dockerignore`（新增）
- `docker-compose.yml`（backend / postgres 服务）
- `backend/tests/test_save_repository.py`、`test_save_service.py`、`test_save_api.py`（新增，17 项测试）
- `backend/requirements.txt`（+psycopg[binary]）

## 3. 如何验证

```bash
cd /d/gal/backend && .venv/Scripts/python -m pytest -q   # 全量（fixture mock）
GAL_TEST_POSTGRES_DSN=postgresql://gal:gal@localhost:5432/gal .venv/Scripts/python -m pytest -q
```

**全量 368 passed**（无 DSN 时 351 passed，PG 用例 12 项 skip）。

验收场景（docs/13 Task 6 验收 + §26.3），`test_save_service.py` / `test_save_repository.py` / `test_save_api.py`：

| 验收项 | 结果 |
|---|---|
| 1. DeepSeek / Claude Memory 不串 | PASS（load 后 memory 仅 deepseek scope，save 后新 memory 不进入） |
| 2. Evidence 恢复 | PASS（EV01 + hotspot 恢复） |
| 3. Claim 恢复 | PASS（claim_store + resolved_contradictions 恢复） |
| 4. Narrative phase 恢复 | PASS（investigation phase + flags 恢复） |
| 5. Character availability 恢复 | PASS（claude available + EV_CH1_CLAUDE_APPEARS 恢复） |
| 6. Private Interview progress 恢复 | PASS（rights / completed / EV05 恢复） |
| 7. Load 创建新 Active Session | PASS（new id ≠ 原 id；新会话已持久化；可继续对话） |
| 8. schema_version 不支持时明确失败 | PASS（SaveSchemaError → 409） |
| 核心契约 save→mutate→load→restored==save | PASS（全维度 snapshot 相等断言） |
| script cursor 恢复（03:17 不重放） | PASS（手动验证 + roundtrip 覆盖） |
| §26.3 create/overwrite manual / auto / list scoped / delete / invalid id | PASS |
| 后端双实现同语义（JSON + PG 参数化） | PASS（25 项 save 测试双后端全绿） |
| API：list / manual save / auto save / load / delete / 404 | PASS（5 项 TestClient） |

**Docker / PostgreSQL 集成验证**（本机 Docker Desktop 4.87 + WSL2）：

```bash
cd /d/gal && docker compose build && docker compose up -d
curl http://localhost:8000/api/health    # {"status":"ok","service":"gal-backend"}
curl http://localhost:8080/               # 200（nginx）
# 经运行中 backend：opening → POST /api/saves/manual/1 → list → load
# psql SELECT ... FROM game_saves → snapshot 为 JSONB object（手动确认）
docker compose down
```

全链路：Opening → 手动存档 → list → load 返回新 session_id + state + history，存档落 PostgreSQL JSONB 确认。

## 4. 结果

**PASS。** 后端 368 passed（含 17 项新 Save 测试，PG + JSON 双后端）+ Docker Compose 三服务（frontend-vue / backend / postgres）构建启动成功 + Postgres 存档端到端验证通过。

## 5. 已知限制

- **会话持久化仍是 JSON**（`JsonSessionRepository`），只有存档入 PostgreSQL；docs/13 §16 只要求存档进 PG，会话迁移留待后续。
- **Auto Save 端点在，checkpoint 未接**：`POST /api/saves/auto` 可用（手动触发），但 docs/13 §21.2 的 4 个 checkpoint（Opening / Claude Appeared / INF01 / INF03）是 Task 8 范围。
- **Load 后前端未接**：前端 saves store 的 `refresh()` / LoadView / SavePanel 仍是 Task 5 骨架，Task 7 接 `/api/saves`。
- **`get_by_id`（JSON 后端）是全量扫描**：每 player 最多 7 个存档，开销有界；PG 是主键查询。
- 首版 `presentation` 稳定态不含 slot/scale/offset 覆盖（§17.7「position override」留待 Task 7 视觉需求时补）。
- Docker 构建首次拉 `python:3.12-slim` / `nginx:1.27-alpine` 偶发 auth.docker.io 超时，重试/预拉即恢复（网络环境抖动，非代码问题）。

## 6. 建议提交

可以提交。改动：
- 业务：`backend/app/save/`、`backend/app/api/saves.py`、`backend/app/game/orchestrator.py`、`backend/app/main.py`
- 部署：`backend/Dockerfile`、`.dockerignore`、`docker-compose.yml`、`backend/requirements.txt`
- 验证：`backend/tests/test_save_{repository,service,api}.py`

（注：`CLAUDE.md` 有用户/编辑器侧的在途修改，与 Task 6 无关，不纳入本提交。）
