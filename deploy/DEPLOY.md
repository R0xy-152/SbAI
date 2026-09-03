# 服务器部署手册（快速上线固定剧本版）

> 对应 docs/17 §4。服务器信息（IP / SSH / 域名）由部署执行人持有；本手册
> 覆盖从「拿到一台空 Linux 服务器」到「公网可玩」的全流程与验证/回滚。
>
> - 一键部署脚本：deploy/up.sh（Ubuntu / Alibaba Cloud Linux 3）
> - 阿里云控制台准备步骤（换系统/安全组/密码）：deploy/ALIYUN.md
> - Windows Server 2022 备选方案：deploy/WINDOWS-SERVER-2022.md（主推仍是换 Linux）

## 0. 前提

- 服务器：Linux x86_64，能访问外网（拉镜像/依赖）；
- Docker Engine + Docker Compose v2（docker compose version 可用）；
- 本仓库代码（git clone 或打包上传，任选其一）。

## 1. 上传代码

```bash
# 方式 A：git（服务器能访问代码仓库时）
git clone <repo-url> gal && cd gal

# 方式 B：git bundle 打包上传（无仓库访问时，推荐；已验证中文文件名完好）
#   本机：  git bundle create gal.bundle HEAD
#   上传：  scp gal.bundle user@server:/srv/
#   服务器：git clone gal.bundle gal && cd gal
#   注意：不要用 Windows 下的 git archive 打包——中文文件名会在 tar 解包时损坏
#   （实测 deepseek_开心.png 等文件丢失），bundle 是二进制格式，编码安全。
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

## 2.5 国内服务器（阿里云等）必做：Docker 镜像加速

国内服务器直连 docker.io 会超时（实测阿里云杭州区 registry-1.docker.io 不可达），
首次构建前配置镜像加速：

```bash
bash deploy/setup-docker-mirror.sh   # 写入 daemon.json（docker.m.daocloud.io）并重启 docker
```

> 阿里云用户也可用「容器镜像服务 → 镜像加速器」里的个人专属地址替换。

## 3. 构建并启动

```bash
docker compose build
docker compose up -d
docker compose ps          # 三个服务：frontend-vue / backend / postgres(healthy)
```

## 4. 上线验证清单（全部通过才算部署完成）

自动化脚本（推荐，覆盖 4.1–4.3 + 静态资源 + 页面）：

```bash
# Linux 服务器上（无需 pwsh）：
bash deploy/server-verify.sh http://127.0.0.1:<FRONTEND_PORT>
# 或部署机远端：
pwsh -File deploy/verify.ps1 -BaseUrl http://<server>:<FRONTEND_PORT>
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

# 4.4 浏览器实测：生产打开 https://sbai.xin/；本机才使用 http://127.0.0.1:<FRONTEND_PORT>/
#   开始游戏 → 逐行推进 → 三个选项点（A/B/C 胶囊窗口）→「第一章 完」结局 → 返回标题
```

## 5. 域名与 HTTPS（生产必需）

### 5.1 方案一：上层 Caddy（当前生产方案）

```
# 保持 FRONTEND_PORT=8080，安装仓库中的生产配置并重载：
sudo install -m 644 deploy/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
```

`deploy/Caddyfile` 将纯 HTTP IP、旧 nip.io 与 www 入口统一重定向到
`https://sbai.xin`。不得让公网 HTTP 入口反向代理页面或 `/api/auth/login`，
否则邀请码会在 Cookie 签发前以明文 request body 穿过链路。

### 5.2 方案二：上层 Nginx + certbot

```nginx
server {
    listen 80;
    server_name your.domain;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name your.domain;
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
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
- 防火墙只放行 80/443；80 端口仅用于重定向到 HTTPS，不提供应用内容；
- 生产环境必须修改 POSTGRES_PASSWORD（.env）；
- 仓库内绝不放任何 API key / .env。
# 邀请码账号首次切换（docs/18）

首次启用账号功能前，先在 `/srv/gal/.env` 配置随机 `GAL_AUTH_SECRET` 与
`GAL_AUTH_COOKIE_SECURE=true`。该密钥后续不可随意更换，
否则所有既有邀请码摘要都会失效。

切换步骤（明确会删除旧匿名存档与会话）：

```bash
cd /srv/gal
docker compose exec -T postgres pg_dump -U gal -d gal > /srv/gal-before-accounts.sql
docker compose exec -T postgres psql -U gal -d gal -c "DELETE FROM game_saves;"
find /srv/gal/backend/data/sessions -maxdepth 1 -type f -name '*.json' -delete
docker compose up -d --build backend frontend-vue
docker compose exec backend python -m app.auth.cli create --name "展示账号 01" --quota 100
```

常用管理命令：

```bash
docker compose exec backend python -m app.auth.cli list
docker compose exec backend python -m app.auth.cli add-quota USER_ID 100
docker compose exec backend python -m app.auth.cli disable USER_ID
docker compose exec backend python -m app.auth.cli rotate-code USER_ID
docker compose exec backend python -m app.auth.cli revoke-sessions USER_ID
```

仅 localhost 本地 HTTP 联调时可临时设置 `GAL_AUTH_COOKIE_SECURE=false`；公网部署
不得关闭。修改后执行 `docker compose up -d backend`。
