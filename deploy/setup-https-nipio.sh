#!/usr/bin/env bash
set -euo pipefail
cd /srv/gal
# 1. 前端从宿主 80 挪到 8080，把 80/443 让给 Caddy
sed -i 's|^FRONTEND_PORT=.*|FRONTEND_PORT=8080|' .env
docker compose up -d frontend-vue
# 2. 安装仓库内的 Caddy 配置：所有公网入口统一收敛到 https://sbai.xin。
install -m 644 deploy/Caddyfile /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
# 3. 启动 Caddy
systemctl enable --now caddy
sleep 5
systemctl status caddy --no-pager | head -5
