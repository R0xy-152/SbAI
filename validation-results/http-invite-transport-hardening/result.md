# HTTP 邀请码传输加固验证

- **状态：** PASS_WITH_LIMITATION
- **日期：** 2026-09-03
- **环境：** macOS 本地仓库；线上阿里云 ECS 114.55.133.96；Caddy + Docker Compose

## 用例与结果

| 用例 | 结果 | 证据 |
| --- | --- | --- |
| 纯 HTTP IP 不再提供页面 | PASS | `HEAD http://114.55.133.96/login?redirect=%2Fchapters` 返回 301，`Location: https://sbai.xin/login?redirect=%2Fchapters` |
| URL 片段跨重定向保留 | PASS | Playwright 从 `http://114.55.133.96/login#transport-fragment-probe` 导航后落在 `https://sbai.xin/login#transport-fragment-probe`；片段未上传 HTTP 服务端 |
| HTTP 登录端点不再反代 Backend | PASS | 使用无效探针值 `POST http://114.55.133.96/api/auth/login` 返回 Caddy 301，未返回 Backend 的认证响应 |
| www / nip.io 收敛到正式域名 | PASS | `https://www.sbai.xin/test?probe=1` 返回 301 到 `https://sbai.xin/test?probe=1`；服务器本机验证 nip.io HTTP→HTTPS→`sbai.xin` |
| 正式 HTTPS 服务可用 | PASS | `GET https://sbai.xin/api/health` 返回 HTTP 200 |
| 线上 Cookie Secure 开关 | PASS | Backend 容器内断言 `GAL_AUTH_COOKIE_SECURE=true` |
| Caddy 配置 | PASS | 服务器 `caddy validate --adapter caddyfile` 返回 `Valid configuration`，reload 后服务为 active |
| 前端公网 HTTP 兜底 | PASS | 传输判定 + LoginView 定向测试 7/7；公网 HTTP 自动提交被阻止、按钮禁用并展示 HTTPS 链接 |
| 前端完整验证 | PASS | Vitest 26 files / 78 tests；`vue-tsc` 通过；Vite production build 通过 |
| Compose 默认值 | PASS | `docker-compose.yml` 默认值为 `${GAL_AUTH_COOKIE_SECURE:-true}`；`.env.example` 为 `true` |

## 变更与回滚证据

- 线上旧 Caddy 配置备份：`/etc/caddy/Caddyfile.pre-http-hardening-20260903`。
- 仓库新增 `deploy/Caddyfile`，后续部署不再依赖服务器手工配置。

## 限制

1. 本机没有 Docker CLI，未执行 `docker compose config`；已通过仓库值检查和线上容器环境断言覆盖该项。
2. 本次只立即部署了关闭漏洞所需的 Caddy 配置。前端提醒与兜底源码已在本地完成并验证，但未单独部署：服务器应用仍在 commit `287c5cd`，本地 HEAD 含其他尚未上线功能，直接整体部署会扩大本任务范围。
3. 本地网络访问 nip.io 会被链路中的 `Beaver` 403 / TLS reset 干扰；nip.io 重定向由服务器本机 Host/TLS 定向请求验证。
