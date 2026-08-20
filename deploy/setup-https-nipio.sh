#!/usr/bin/env bash
set -euo pipefail
cd /srv/gal
# 1. 前端从宿主 80 挪到 8080，把 80/443 让给 Caddy
sed -i 's|^FRONTEND_PORT=.*|FRONTEND_PORT=8080|' .env
docker compose up -d frontend-vue
# 2. 写 Caddyfile：IP 走 HTTP 直连；nip.io 域名自动 HTTPS（Let's Encrypt）
cat > /etc/caddy/Caddyfile <<'EOF'
http://114.55.133.96 {
    reverse_proxy 127.0.0.1:8080
}

114.55.133.96.nip.io {
    reverse_proxy 127.0.0.1:8080
}
EOF
# 3. 启动 Caddy
systemctl enable --now caddy
sleep 5
systemctl status caddy --no-pager | head -5
