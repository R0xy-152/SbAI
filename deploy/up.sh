#!/usr/bin/env bash
# 快速上线一键部署（Linux 服务器：Ubuntu 22.04 / Alibaba Cloud Linux 3）。
# 用法：把仓库放到服务器后，在仓库根目录执行：
#   sudo bash deploy/up.sh
# 会依次：装 Docker（缺失时）→ 生成 .env（缺失时）→ 构建启动 → 基础验收。
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== 1/4 检查 Docker =="
if ! command -v docker >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
  else
    echo "没有 apt-get，请手动安装 Docker 后重试" && exit 1
  fi
fi

echo "== 2/4 生成 .env（若缺失）=="
if [ ! -f .env ]; then
  cp .env.example .env
  echo "已生成 .env，请按需修改（FRONTEND_PORT=80 / POSTGRES_PASSWORD=强密码）后重新执行本脚本"
  exit 0
fi

echo "== 3/4 构建并启动 =="
docker compose build
docker compose up -d

echo "== 4/4 等待就绪 =="
sleep 12
docker compose ps

if command -v pwsh >/dev/null 2>&1; then
  pwsh -File deploy/verify.ps1 -BaseUrl "http://127.0.0.1:${FRONTEND_PORT:-8080}" || true
else
  echo "未安装 pwsh，请手动验收：curl http://127.0.0.1/api/health"
  curl -fsS "http://127.0.0.1:${FRONTEND_PORT:-8080}/api/health" && echo "health ok"
fi

echo "部署完成。访问 http://<公网IP>/（或所配端口）开始游戏。"
