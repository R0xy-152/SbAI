# 线上运营状态（deploy/STATUS.md）

高频变化、与代码无关的运营信息集中于此（AGENTS.md 只指向本文件）。
**Secret 绝不写入本文件**（密码/API key 通过私聊传递，只落在服务器环境）。

## 当前上线状态（2026-08-21）

- 服务器：阿里云 ECS 114.55.133.96（2核2GiB Ubuntu；Docker 三服务 frontend-vue nginx / backend / postgres，均 restart: unless-stopped；Caddy 反代 80/443；swap 2G）
- 玩家入口：`http://114.55.133.96/`；`https://114.55.133.96.nip.io/`（本地网络对 nip.io SNI 有 GFW 干扰，HTTP 正常；服务器自测 HTTPS 200）
- 已部署 commit：4bb5a79（账号配额+章节选择 2538f55 → 无序序章流程 d211442 → .dockerignore 构建修复 360efa5 → auth.cli usage 4bb5a79）
- 玩法：标题「开始游戏」→ 章节选择（当前仅序章解锁）→ /story?story_id=prologue 无序探班（AI 停用）→ 汇合后选角色 → /game 对应角色后日谈（DeepSeek 真实自由聊天）；旧调查玩法经左上角「行动」按钮
- 账号功能（docs/18）：已启用（GAL_AUTH_REQUIRED=true，仅服务器 .env 含 GAL_AUTH_SECRET）；展示账号 01（quota 100）/ 02（quota 100）/ 03（quota 200），邀请码明文不落库；存量匿名存档已清空，新玩家需邀请码登录
- 用量监控：`docker compose exec backend python -m app.auth.cli usage`（每账号 quota 用量/登录次数/活跃会话/游戏会话/最后登录）
- DEEPSEEK_API_KEY：已配置，仅存服务器 `/srv/gal/.env`（不入库）；缺 key 时回落 mock
- 备案指引（控制台走查）：`deploy/ALIYUN.md` §④

- [ ] 服务器 root 临时密码：Gal@2026abc，当前正在频繁修改上线的时期，暂时不管密码更改问题但确保不泄露
## 待办

- [ ] sbai.xin ICP 备案（个人、免费、7-20 天）：**通过前不要添加 DNS A 记录**；通过后加 A 记录（@ 和 www）→ 通知 AI 改 Caddyfile 加域名 + HTTPS（2 分钟）
- [ ] DeepSeek key 曾在聊天中出现过：如需可在开放平台重新生成 → 替换 `/srv/gal/.env` → `docker compose up -d backend`
- [ ] 缺美术：豆包立绘（main + 尴尬）、场景背景（docs/17 §6.1）；差分立绘 resolver 按 `{角色}_{表情英文id}.png` 探测，补图自动生效

## 变更记录

- 2026-08-21：AI 玩法新开局删除前置剧情；常驻背景替换为用户教室图；DeepSeek key 接入，真实 AI 回复生效
- 2026-08-21（二次部署）：账号配额+章节选择、无序序章流程上线；账号功能首次切换（删 18 条匿名存档）；修复 .dockerignore 导致 backend 构建失败的 bug（docs/story/Prologue.md 放行）
- 2026-08-21（三次部署）：新增展示账号 02（quota 100）、03（quota 200）；auth.cli 新增 usage 子命令（按账号监控用量）
