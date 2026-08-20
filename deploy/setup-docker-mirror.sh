#!/usr/bin/env bash
set -euo pipefail
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"]
}
EOF
systemctl restart docker
docker info 2>/dev/null | grep -A2 'Registry Mirrors' || true
