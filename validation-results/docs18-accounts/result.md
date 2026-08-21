# docs/18 轻量邀请码账号与 AI 永久额度

- 状态：PASS_WITH_LIMITATION
- 日期：2026-08-21
- 环境：Windows 11 / Python 3.12 venv / Node 22 / Docker 29.7.2 / PostgreSQL 16 Alpine / Nginx 1.27 Alpine

## 已验证用例

1. 邀请码正确/错误登录、跨设备重复登录、HttpOnly Cookie 会话、注销、停用立即失效、过期会话拒绝。
2. 用户只能访问自己的 Game Session、History 与 Save；越权返回 404。
3. 每账号永久额度原子预扣；最后一个并发名额只有一个请求成功；耗尽返回 429；Provider 失败退款。
4. 前端登录状态恢复、旧匿名 localStorage 清理、额度展示/更新与退出清理。
5. PostgreSQL 真实容器建表、登录、鉴权、额度扣减/退款与 Session Owner 绑定。
6. 两个独立 HTTP Cookie 会话使用同一邀请码：设备一聊天并保存，设备二登录后列出并成功读取同一存档。
7. Backend/Frontend Docker 镜像构建及 Nginx 配置检查。

## 结果与证据

- Backend：`441 passed, 12 skipped`。
- Frontend unit：`59 passed`；`vue-tsc` PASS；Vite production build PASS。
- `docker compose config --quiet` PASS。
- PostgreSQL integration：`POSTGRES_AUTH_PASS`。
- HTTP full smoke：`HTTP_SMOKE_PASS`，聊天后剩余额度由 3 变 2，跨 Cookie Session 存档/读档成功。
- `nginx -t`：syntax ok / test successful。
- 所有临时验证 Compose project 及其 PostgreSQL volume 已删除。

## 限制

- 未直接部署到公网服务器；部署清理、备份和首批邀请码生成步骤已写入 `deploy/DEPLOY.md`。
- 用户确认当前继续使用 HTTP，因此 Cookie 暂不设置 `Secure`；仅适合受控展示，正式开放前必须切换 HTTPS。
- 额度预扣后若 Backend 进程立即崩溃，可能损失 1 次额度，需要 CLI 人工补回。
- 12 个 skipped 为既有真实 Provider 条件测试，不属于本任务新增失败。
