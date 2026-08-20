# 服务器部署记录（快速上线固定剧本版）

- **状态：PASS_WITH_LIMITATION**（限制 = 阿里云安全组尚未放行 80，公网访问待用户添加规则后复核）
- **目标服务器：** 114.55.133.96（阿里云 ECS，2核 1.6Gi 内存 / 40G 盘 / 100Mbps）
- **系统：** Ubuntu 22.04（OpenSSH 8.9p1 Ubuntu-3ubuntu0.16；由 Windows Server 2022 经控制台更换而来）

## 部署过程

| 步骤 | 内容 | 结果 |
|---|---|---|
| 1 | 服务器准备：2G swap + /etc/fstab 持久化 | PASS |
| 2 | 代码传输：git bundle（166MB，中文文件名完好）→ /srv/gal 克隆 | PASS（HEAD 4274d38） |
| 3 | Docker 安装（apt 官方源）+ systemd 自启 | PASS |
| 4 | 镜像加速：registry-1.docker.io 不可达 → daemon.json 配 docker.m.daocloud.io | PASS（修复国内拉镜像超时） |
| 5 | 生产 .env：FRONTEND_PORT=80、POSTGRES_PASSWORD 强密码 | PASS |
| 6 | docker compose build + up（frontend-vue / backend / postgres） | PASS（三容器 Up，postgres healthy） |
| 7 | postgres DSN 修复：密码含 @ 导致 psycopg 主机解析错（/api/saves 500）→ 换无特殊字符密码并 down -v 重建卷 | PASS（修复） |
| 8 | 服务器端验收 server-verify.sh：health / 剧本首节点 / postgres AUTO 存档 / 静态资源 / 页面 | PASS 5/5 |
| 9 | 服务器端完整剧本走查 server-walk.py：178 行、3 选项、14 场景边界、结局、刷新恢复、AUTO 存档 | PASS（与本机一致） |

## 待办（用户侧）

- 阿里云安全组入方向放行 TCP 80/80 → 0.0.0.0/0（当前公网 80 仍 closed/filtered）；
- 放行后从部署机跑 deploy/verify.ps1 -BaseUrl http://114.55.133.96 + Playwright 浏览器走查完成公网复核；
- 建议：部署完成后修改 root 密码（当前为临时密码）；
- 可选：绑定域名 + HTTPS（DEPLOY.md §5，443 需同时放行）。

## 新增部署工具

- deploy/remote.py —— SSH 驱动（cmd/put/script，UTF-8 输出）；
- deploy/server-verify.sh —— Linux 服务器端验收（无 pwsh 环境）；
- deploy/server-walk.py —— 服务器端完整剧本走查；
- deploy/setup-docker-mirror.sh —— 国内镜像加速配置。
