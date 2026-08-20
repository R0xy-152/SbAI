# 服务器部署手册（快速上线固定剧本版）

> 对应 docs/17 §4。服务器信息（IP / SSH / 域名）由部署执行人持有；本手册
> 覆盖从「拿到一台空 Linux 服务器」到「公网可玩」的全流程与验证/回滚。
>
> - 一键部署脚本：deploy/up.sh（Ubuntu / Alibaba Cloud Linux 3）
> - Windows Server 2022 备选方案：deploy/WINDOWS-SERVER-2022.md（主推仍是换 Linux）

## 0. 前提

- 服务器：Linux x86_64，能访问外网（拉镜像/依赖）；
- Docker Engine + Docker Compose v2（docker compose version 可用）；
- 本仓库代码（git clone 或打包上传，任选其一）。

## 1. 上传代码

```bash
# 方式 A：git（服务器能访问代码仓库时）
git clone <repo-url> gal && cd gal

# 方式 B：本机打包上传（无仓库访问时）
#   本机：  git archive --format=tar.gz -o gal-deploy.tar.gz HEAD
#   上传：  scp gal-deploy.tar.gz user@server:/srv/
#   服务器：mkdir -p /srv/gal && tar -xzf gal-deploy.tar.gz -C /srv/gal && cd /srv/gal
```

## 2. 配置环境变量

```bash
cp .env.example .env
vim .env   # 至少改两处：
#   FRONTEND_PORT —— 直连公网设 80；有上层反代保持 8080
#   POSTGRES_PASSWORD —— 换成强密码
```

> 快速上线版不需要 DEEPSEEK_API_KEY / ANTHROPIC_API_KEY：GAL_PROVIDER 缺省
> auto，无 key 自动回落 mock（docs/17：AI 回复已停用，剧本不依赖任何 LLM）。

## 3. 构建并启动

```bash
docker compose build
docker compose up -d
docker compose ps          # 三个服务：frontend-vue / backend / postgres(healthy)
```

## 4. 上线验证清单（全部通过才算部署完成）

自动化脚本（推荐，覆盖 4.1–4.3 + 静态资源 + 页面）：

```bash
pwsh -File deploy/verify.ps1 -BaseUrl http://127.0.0.1:<FRONTEND_PORT>
```

手动等价清单：

```bash
# 4.1 健康检查
curl -s http://127.0.0.1:8000/api/health
# 经前端 nginx：
curl -s http://127.0.0.1:<FRONTEND_PORT>/api/health

# 4.2 固定剧本冒烟：首次 advance 应返回 SYSTEM INITIALIZING...
curl -s -X POST http://127.0.0.1:<FRONTEND_PORT>/api/story/advance \
  -H 'Content-Type: application/json' -d '{"session_id":null,"player_id":"deploy-check"}'

# 4.3 存档链路（postgres）：上一步会触发 AUTO 存档
curl -s 'http://127.0.0.1:<FRONTEND_PORT>/api/saves?player_id=deploy-check'
#   返回的 auto 非 null 即 postgres 写入正常

# 4.4 浏览器实测：打开 http://<server>:<FRONTEND_PORT>/
#   开始游戏 → 逐行推进 → 三个选项点（A/B/C 胶囊窗口）→「第一章 完」结局 → 返回标题
```

## 5. 域名与 HTTPS（可选）

### 5.1 方案一：上层 Caddy（自动 HTTPS，推荐）

```
# 保持 FRONTEND_PORT=8080，Caddy 反代：
# Caddyfile:
#   your.domain {
#       reverse_proxy 127.0.0.1:8080
#   }
```

### 5.2 方案二：上层 Nginx + certbot

```nginx
server {
    listen 80;
    server_name your.domain;
    location / { proxy_pass http://127.0.0.1:8080; proxy_set_header Host $host; }
}
```

同源反代下前端 nginx 的 /api、/char、/backgroud 均走容器内网，无需额外配置。

## 6. 更新与回滚

```bash
# 更新（服务器上）
git pull && docker compose build && docker compose up -d

# 回滚到某提交
git checkout <commit> && docker compose build && docker compose up -d

# 快速回滚旧玩法入口（docs/17 §5）：把 Title/LoadView 的 push('/story') 改回 '/game'
```

## 7. 数据与备份

- 会话 JSON：宿主目录 ./backend/data（compose 已挂载）；
- 存档（postgres）：named volume postgres_data。

```bash
# 备份
tar -czf data-backup-$(date +%F).tar.gz backend/data
docker compose exec -T postgres pg_dump -U gal gal > saves-backup-$(date +%F).sql
# 恢复
docker compose exec -T postgres psql -U gal gal < saves-backup-XXXX.sql
```

## 8. 安全基线

- backend 只绑定宿主 loopback（127.0.0.1:8000），公网不可直达；
- postgres 不发布任何宿主端口；
- 防火墙只放行 80/443（或所选的 FRONTEND_PORT）；
- 生产环境必须修改 POSTGRES_PASSWORD（.env）；
- 仓库内绝不放任何 API key / .env。
