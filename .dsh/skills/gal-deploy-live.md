---
name: gal-deploy-live
description: 把本地更新打包部署到 gal 线上服务器（git bundle 上传 + reset + 重建容器 + 验证）
whenToUse: 用户要求部署上线、发布本地更新到服务器、或修复线上问题时
---

# gal 打包发布服务器流程

把本地代码更新部署到线上服务器（阿里云 ECS 114.55.133.96，/srv/gal）。

## 0. 前置确认（不可跳过）

1. **检查工作区未提交改动**：`git status --short`。只部署已提交的 commit；若有与本次部署无关的并行改动，**绝不卷入 bundle**（bundle 只含 commit，未提交改动天然不进）。
2. **SSH 访问（密钥认证）**：本机 `ssh gal` 即可登录（Host 别名见 `~/.ssh/config`，密钥 `~/.ssh/gal_root_ed25519`，无需密码）；root 密码不入库，**绝不写进 skill/仓库/提交记录**。
3. **本地验证**（可选但推荐）：
   - 后端：`cd backend && .venv/Scripts/python -m pytest -q`
   - 前端：`cd frontend-vue && npm.cmd run build`（PowerShell 禁止脚本运行，必须用 `npm.cmd` 而非 `npm`）
4. **删除旧 bundle 再重建**：残留的 `gal-new.bundle` 或 `gal-new.bundle.lock` 会导致 `git bundle create` 崩溃（exit=-1073740940 堆损坏）或静默失败。先 `Remove-Item gal-new.bundle, gal-new.bundle.lock -Force` 再创建。

## 1. 创建并验证 bundle

```powershell
cd D:\gal
Remove-Item gal-new.bundle, gal-new.bundle.lock -Force -ErrorAction SilentlyContinue
git bundle create gal-new.bundle HEAD
git bundle list-heads gal-new.bundle   # 必须显示最新 commit hash，确认无旧缓存
```

> Windows 下**必须用 git bundle**，不要用 `git archive`（中文文件名会损坏）。

## 2. 上传到服务器

```bash
# 密钥登录上传（本机 macOS；Windows 同样用 scp，密钥已配）
cd /Users/ming/gal/SbAI
scp gal-new.bundle gal:/srv/gal-new.bundle
```

- 276MB 左右，约 1-3 分钟，建议后台运行。
- `remote.py` 通用用法：`--cmd "远端命令"` / `--put 本地 远端` / `--script 脚本`。
- **已知坑**：`--script` 的 Windows 路径会拼错（`/tmp/D:galdeploy...`），传 Windows 路径的脚本请改用 `--put` 上传到固定路径（如 `/tmp/deploy.sh`）再 `--cmd "bash /tmp/deploy.sh"`。
- **已知坑**：`--cmd` 内含 `&&`、引号、重定向时会被 PowerShell/argparse 拆坏，复杂命令请写成 .sh 上传执行。

## 3. 服务器 reset + 重建

```bash
# 服务器上（ssh gal）
cd /srv/gal && git fetch /srv/gal-new.bundle HEAD && git reset --hard FETCH_HEAD && git log --oneline -2
cd /srv/gal && docker compose build backend frontend-vue && docker compose up -d
```

- 只改了 backend 就 `docker compose build backend && docker compose up -d backend`（快很多）。
- `.env` 不入库、`git reset --hard` 后保留；改 `.env` 后需 `docker compose up -d backend` 重建生效。
- 改了 `.env` 新增了 `GAL_AUTH_SECRET` 等变量时，compose 的 `${VAR:?}` 语法要求变量存在，否则 build/up 失败。

## 4. 验证清单（全部通过才算完成）

```bash
# 健康检查
curl -s http://127.0.0.1:8000/api/health          # {"status":"ok",...}
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/   # 200（前端）
curl -s -o /dev/null -w '%{http_code}' http://114.55.133.96/    # 200（公网）

# 账号登录验证（用 auth.cli create 的邀请码）
docker compose exec -T backend python -m app.auth.cli list      # 账号列表
docker compose exec -T backend python -m app.auth.cli usage     # 用量统计

# 浏览器 E2E（本地有 Playwright 时）：frontend-vue/scripts/prologue-smoke.mjs
# 注意：线上有 GAL_AUTH_REQUIRED=true，冒烟脚本需先登录（context.request.post /api/auth/login 注入 cookie）
```

## 5. 收尾

- 更新 `deploy/STATUS.md` 的「已部署 commit」和变更记录，commit 入库。
- 部署验证证据（截图等）放 `validation-results/<任务>/result.md` + evidence/。
- 临时脚本（含邀请码/密码的 .sh/.mjs）用后即删，**绝不入库**。

## 回滚

```bash
# 服务器上
cd /srv/gal && git checkout <上一commit> && docker compose build backend frontend-vue && docker compose up -d
```
