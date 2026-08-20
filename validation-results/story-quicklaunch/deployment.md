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

## 公网复核（安全组 80 放行后）

| 项 | 结果 |
|---|---|
| 公网 80 连通 | OPEN |
| deploy/verify.ps1 -BaseUrl http://114.55.133.96 | PASS 5/5 |
| Playwright 公网浏览器走查（开始游戏→全程推进→3 选项窗口→结局→返回标题） | PASS |

**公网复核中修复的坑**：`crypto.randomUUID` 只在安全上下文（HTTPS/localhost）可用，公网 HTTP IP 直连下抛 "crypto.randomUUID is not a function"，导致 player_id 生成失败、存档/剧本请求报错。修复：getPlayerId 加手工 UUID 回退（frontend-vue/src/api/saves.ts，commit 5da1326），服务器前端镜像已重建。

## HTTPS（nip.io 免费域名 + Caddy，用户选定先体验）

| 项 | 结果 |
|---|---|
| Caddy 安装（v2.11.4，官方源） | PASS |
| 前端从宿主 80 挪到 8080，80/443 交给 Caddy | PASS（IP:80 直连经 Caddy 反代无回归） |
| 证书：Let's Encrypt 生产签发（中间证书 CN=YE2，有效期至 2026-11-18，Caddy 自动续期） | PASS（服务器本地 curl 无 -k 全链校验 200） |
| HTTP→HTTPS 自动跳转 | PASS（Caddy auto_https） |
| 签发过程：HTTP-01 被运营商干扰 → 443 开放后 tls-alpn-01 验证成功（authz valid）→ 生产签发 | PASS |

**已知限制（nip.io 免费域名的副作用）**：境外网络访问 *.nip.io 域名时 TLS 握手会被 GFW 间歇性/持续性 reset（部署机境外出口实测 8/8 失败）；**国内玩家访问不受影响**（干扰仅出现在跨境链路）。绑定正式备案域名后无此问题（换 Caddyfile 一行即可）。

## 建议（用户侧，可选）

- 部署完成后在阿里云控制台重置 root 密码（当前为临时密码）；
- 绑定域名 + HTTPS（DEPLOY.md §5，443 需同时放行）。

**玩家访问地址：http://114.55.133.96/**

## 新增部署工具

- deploy/remote.py —— SSH 驱动（cmd/put/script，UTF-8 输出）；
- deploy/server-verify.sh —— Linux 服务器端验收（无 pwsh 环境）；
- deploy/server-walk.py —— 服务器端完整剧本走查；
- deploy/setup-docker-mirror.sh —— 国内镜像加速配置。
