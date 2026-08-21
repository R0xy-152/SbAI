# 线上运营状态（deploy/STATUS.md）

高频变化、与代码无关的运营信息集中于此（AGENTS.md 只指向本文件）。
**Secret 绝不写入本文件**（密码/API key 通过私聊传递，只落在服务器环境）。

## 当前上线状态（2026-08-21）

- 服务器：阿里云 ECS 114.55.133.96（2核2GiB Ubuntu；Docker 三服务 frontend-vue nginx / backend / postgres，均 restart: unless-stopped；Caddy 反代 80/443；swap 2G）
- 玩家入口：`http://114.55.133.96/`；`https://114.55.133.96.nip.io/`（本地网络对 nip.io SNI 有 GFW 干扰，HTTP 正常；服务器自测 HTTPS 200）
- 已部署 commit：217e024（AI 玩法新开局删前置剧情 + 教室背景图 + DeepSeek 接入文档）
- 玩法：/story 固定剧本（AI 停用）→ 结局「继续聊天」→ /game DeepSeek 真实自由聊天；标题「AI 对话玩法」直接自由聊天；旧调查玩法经左上角「行动」按钮
- DEEPSEEK_API_KEY：已配置，仅存服务器 `/srv/gal/.env`（不入库）；缺 key 时回落 mock
- 备案指引（控制台走查）：`deploy/ALIYUN.md` §④

## 待办

- [ ] sbai.xin ICP 备案（个人、免费、7-20 天）：**通过前不要添加 DNS A 记录**；通过后加 A 记录（@ 和 www）→ 通知 AI 改 Caddyfile 加域名 + HTTPS（2 分钟）
- [ ] 服务器 root 临时密码尽快改掉（当前为部署期临时密码，值只在私聊里）
- [ ] DeepSeek key 曾在聊天中出现过：如需可在开放平台重新生成 → 替换 `/srv/gal/.env` → `docker compose up -d backend`
- [ ] 缺美术：豆包立绘（main + 尴尬）、场景背景（docs/17 §6.1）；差分立绘 resolver 按 `{角色}_{表情英文id}.png` 探测，补图自动生效

## 变更记录

- 2026-08-21：AI 玩法新开局删除前置剧情；常驻背景替换为用户教室图；DeepSeek key 接入，真实 AI 回复生效
