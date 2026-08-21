# 线上部署：账号配额 + 章节选择 + 无序序章流程（2026-08-21 第二次部署）

**状态：PASS**
**日期：2026-08-21**
**范围：** 将本地 3 个新 commit 部署上线（2538f55 账号配额+章节选择 → d211442 无序序章流程 → 381cfa0 文档状态标注 → 360efa5 .dockerignore 构建修复），并在服务器启用账号功能（docs/18 首次切换）。

## 1. 完成了什么

1. **提交本地未提交改动**：docs/story 系列标记「评审中」+ STATUS.md 密码备注 → commit `381cfa0`。
2. **修复部署阻塞的真实构建 bug**：commit `d211442` 的 `backend/Dockerfile` 新增 `COPY docs/story/Prologue.md`，但根 `.dockerignore` 的 `docs/` 规则把该文件排除出 build context → 服务器首次构建报 `/docs/story/Prologue.md: not found`。修复：`.dockerignore` 增加 `!docs/story/Prologue.md` 放行 → commit `360efa5`；本地 `docker build` 实测通过。
3. **git bundle 上传 + 服务器 reset**：`gal-new.bundle`（HEAD=360efa5）→ `/srv/gal-new.bundle` → `git fetch && git reset --hard FETCH_HEAD`。
4. **服务器重建容器**：`docker compose build backend frontend-vue && docker compose up -d`，三容器运行正常。
5. **账号首次切换（docs/18）**：`.env` 追加随机 `GAL_AUTH_SECRET`（64 hex）+ `GAL_AUTH_COOKIE_SECURE=false`（当前 HTTP）；删除 18 条存量匿名存档（`DELETE FROM game_saves;`，按用户指示不备份）；创建「展示账号 01」quota 100。
6. **部署后验证**：health / 登录 / auth/me / prologue story API / 浏览器 E2E 全链路。

## 2. 修改了哪些文件（本次部署相关 commit）

- `docs/story/*`（01-08 + AI Galgame Demo Story Bible v1.0）：文档状态 Active → 评审中（commit 381cfa0）
- `deploy/STATUS.md`：密码备注（commit 381cfa0）
- `.dockerignore`：放行 `docs/story/Prologue.md`（commit 360efa5，构建修复）

## 3. 如何验证

### 3.1 本地验证（部署前）
- backend：`pytest -q` → **454 passed, 12 skipped**
- frontend-vue：`npm run build`（vue-tsc + vite）→ **PASS**（207 modules）
- 本地 `docker build -f backend/Dockerfile` → **PASS**（COPY Prologue.md 成功）

### 3.2 服务器 API 验证（curl）
| 检查 | 结果 |
|---|---|
| `GET /api/health` | `{"status":"ok","service":"gal-backend"}` |
| `GET /`（公网 80） | 200 |
| `POST /api/auth/login`（邀请码） | 返回 user_id=16449f09604a4317a0c10979e416e581，「展示账号 01」，quota 100/0/100 |
| `GET /api/auth/me` | 同上（cookie 生效） |
| `GET /api/story/current?story_id=prologue` | 新 session，started=false |
| `POST /api/story/advance`（prologue） | started=true，node「今天难得有空。」scene=PROLOGUE-OPENING |

### 3.3 浏览器 E2E（Playwright → 公网 http://114.55.133.96）
登录邀请码 → 开始游戏 → /chapters → 序章 → /story?story_id=prologue → 无序探班 3/2/1 选项 → 三人集合 → 最终选择 → /game?character=chatgpt 后日谈。

选项序列与预期完全一致：
1. `['去找 DeepSeek','去找 ChatGPT','去找 Claude']`
2. `['去找 DeepSeek','去找 ChatGPT']`
3. `['去找 ChatGPT']`
4. `['与 DeepSeek 聊天','与 ChatGPT 聊天','与 Claude 聊天']`

**结果：PASS**（证据截图 7 张，见 §5）

## 4. 结果

**PASS。** 新功能（账号配额/章节选择/无序序章流程）已在公网生效；账号功能首次切换完成（存量匿名存档已按用户指示删除，未备份）；构建 bug 已修复并验证。

## 5. 证据

- `validation-results/live-deploy-verify/evidence/`：01-chapters.png / 02-opening.png / choice-1..4.png / 03-aftertalk.png（浏览器 E2E 截图）

## 6. 已知限制与注意事项

- **展示账号邀请码不落库**：`JCEX-UMQV-RSO5-HSKX-ASXS-FFZ4-MQ`（只在本次输出/私聊，无法从 DB 找回）。
- `GAL_AUTH_COOKIE_SECURE=false`：当前 HTTP 展示必须；正式 HTTPS（sbai.xin 备案通过后）需改 true 并重启 backend。
- 存量 18 条匿名存档已删除（用户确认不备份）；新玩家需用邀请码登录。
- `gal-new.bundle` 留于服务器 /srv 与本地（.gitignore），可删除。
