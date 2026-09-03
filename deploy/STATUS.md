# 线上运营状态（deploy/STATUS.md）

高频变化、与代码无关的运营信息集中于此（AGENTS.md 只指向本文件）。
**Secret 绝不写入本文件**（密码/API key 通过私聊传递，只落在服务器环境）。

## 当前上线状态（2026-09-03）

- 服务器：阿里云 ECS 114.55.133.96（2核2GiB Ubuntu；Docker 三服务 frontend-vue nginx / backend / postgres，均 restart: unless-stopped；Caddy 反代 80/443；swap 2G）
- 玩家唯一入口：`https://sbai.xin/`（备案+HTTPS 已上线，`GAL_AUTH_COOKIE_SECURE=true`）；`http://114.55.133.96/`、旧 nip.io 与 www 入口只重定向到该正式地址，不再提供页面或 API。
- 已部署 commit：4e85c86（线上从 287c5cd 一次跳到 4e85c86，含：AI 对话人机感改造(角色人格/记忆/推理回灌/关系阶段/LLM-as-judge) + save schema v1→v2 迁移 + 序章「对开发者的话」收集/导出 + 二维码直达登录 + player 画像召回修复(#3) + 邀请码 HTTPS 传输加固；镜像构建走阿里云 pip 源，Dockerfile 已回滚干净）
- 玩法：标题「开始游戏」→ 章节选择（当前仅序章解锁）→ /story?story_id=prologue 无序探班（AI 停用）→ 汇合后选角色 → /game 对应角色后日谈（DeepSeek 真实自由聊天）；旧调查玩法经左上角「行动」按钮
- 新增 galgame 基础功能：聊天框右下角 ▼ 左侧「自动/快进/保存/读取」控制条（AUTO 自动推进、SKIP 跳到选择点、SAVE/LOAD 打开系统面板）；文字速度基线 1.2x（设置默认倍率不变）；设置移除「睁眼转场」开关（转场仍默认开启）
- 账号功能（docs/18）：已启用（GAL_AUTH_REQUIRED=true，仅服务器 .env 含 GAL_AUTH_SECRET）；展示账号 01（quota 100）/ 02（quota 100）/ 03（quota 200），邀请码明文不落库；存量匿名存档已清空，新玩家需邀请码登录
- 用量监控：`docker compose exec backend python -m app.auth.cli usage`（每账号 quota 用量/登录次数/活跃会话/游戏会话/最后登录）
- DEEPSEEK_API_KEY：已配置，仅存服务器 `/srv/gal/.env`（不入库）；缺 key 时回落 mock
- 备案指引（控制台走查）：`deploy/ALIYUN.md` §④

- SSH 访问：本机密钥 `~/.ssh/gal_root_ed25519`（Host 别名 `gal`，`ssh gal` 即密钥登录）；root 密码不入库，由用户在控制台自行设为强密码（agent 走密钥，无需知晓密码）
## 待办

- [x] sbai.xin ICP 备案 + HTTPS 上线（2026-08-28）：A 记录 @/www → 114.55.133.96；Caddyfile 加域名；Let's Encrypt 证书自动签发；GAL_AUTH_COOKIE_SECURE 改 true。正式地址 https://sbai.xin/
- [ ] DeepSeek key 曾在聊天中出现过：如需可在开放平台重新生成 → 替换 `/srv/gal/.env` → `docker compose up -d backend`
- [ ] 缺美术：豆包立绘（main + 尴尬）、场景背景（docs/17 §6.1）；差分立绘 resolver 按 `{角色}_{表情英文id}.png` 探测，补图自动生效

## 变更记录

- 2026-08-21：AI 玩法新开局删除前置剧情；常驻背景替换为用户教室图；DeepSeek key 接入，真实 AI 回复生效
- 2026-08-21（二次部署）：账号配额+章节选择、无序序章流程上线；账号功能首次切换（删 18 条匿名存档）；修复 .dockerignore 导致 backend 构建失败的 bug（docs/story/Prologue.md 放行）
- 2026-08-21（三次部署）：新增展示账号 02（quota 100）、03（quota 200）；auth.cli 新增 usage 子命令（按账号监控用量）
- 2026-08-21（四次部署）：e2e 适配序章新流程；文字速度基线 1.2x；设置移除睁眼转场开关；修复序章瞬间闪现 background1.png；新增 AUTO/SKIP/SAVE/LOAD 控制条
- 2026-08-22（五次部署）：替换 chatgpt_happy 为透明背景版本；三人集合立绘恢复原尺寸同基线（取消 scale/offset_y）；自由对话新增点击任意位置/滚轮下滑「继续对话」（回应态可用），滚轮上滑打开历史
- 2026-08-28（六次部署）：sbai.xin 备案通过并上线 HTTPS —— 云解析加 A 记录（@/www → 114.55.133.96），Caddyfile 加 sbai.xin/www.sbai.xin，Let's Encrypt 证书自动签发（有效期至 2026-11-26），GAL_AUTH_COOKIE_SECURE 改 true（当时 HTTP IP 仍可加载页面，仅 Cookie 不落地；此缺口于 2026-09-03 关闭）
- 2026-08-28（安全加固）：外部端口扫描+内部排查后 —— /srv/gal/.env 改 600；sshd 关闭 X11Forwarding/AllowTcpForwarding；安装启用 fail2ban（sshd jail）；前端 8080 改绑 127.0.0.1（docker-compose.yml 同步入库，外网 8080 已关闭）。待用户在控制台：安全组收紧 22 源 IP、删除 8080 放行、更换 root 密码
- 2026-09-03（邀请码传输加固）：线上 Caddy 已将纯 HTTP IP、旧 nip.io 与 www 入口统一重定向到 `https://sbai.xin`；仓库 Compose/Cookie 生产默认改为 Secure，登录页源码在公网 HTTP 环境阻止邀请码提交。
- 2026-09-03（七次部署）：整包上线到 4e85c86 —— AI 对话人机感（角色人格/记忆/推理/关系/评测）与序章 AI 后日谈真实模型链路、save v2 自动迁移、对开发者的话收集、二维码登录、player 画像修复、HTTPS 传输加固前端源码；验证：health 200 / HTTPS 200 / HTTP 301 跳转 / 账号 CLI 正常 / backend 无错误日志。
