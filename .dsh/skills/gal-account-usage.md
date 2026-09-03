---
name: gal-account-usage
description: 查看 gal 线上服务器全部邀请码账号的用量（额度/登录/活跃会话/游戏会话/最后登录）
whenToUse: 用户想监控邀请码使用情况、查看账号额度消耗、排查谁在用或用量异常时
---

# 查看线上全部账号用量

在服务器（阿里云 ECS 114.55.133.96，/srv/gal）上查看每个邀请码账号的使用统计。

## 一条命令

```bash
# 服务器上（本机经 ssh gal 执行）
cd /srv/gal && docker compose exec -T backend python -m app.auth.cli usage
```

本机完整调用（SSH 密钥登录，Host 别名 `gal`）：

```bash
ssh gal "cd /srv/gal && docker compose exec -T backend python -m app.auth.cli usage"
```

## 输出格式（示例）

```
展示账号 01  ACTIVE  1/100  logins=56  active=48  game_sessions=8  last_login=2026-08-21 08:34:56
展示账号 02  ACTIVE  0/100  logins=0   active=0   game_sessions=0  last_login=-
展示账号 03  ACTIVE  0/200  logins=0   active=0   game_sessions=0  last_login=-
```

| 字段 | 含义 |
|---|---|
| `ACTIVE` | 账号状态（ACTIVE/DISABLED） |
| `1/100` | quota 已用/总额；**每次 AI 自由聊天（/api/chat）扣 1**，失败/回落自动退款 |
| `logins=` | 累计登录次数（每次用邀请码登录 +1） |
| `active=` | 当前未过期未撤销的会话数（≈在线设备数） |
| `game_sessions=` | 绑定过的游戏会话数（实际开玩过的人数） |
| `last_login=` | 最近登录时间，`-` 表示从未登录 |

## 常用配套命令（同一账号系统）

```bash
docker compose exec -T backend python -m app.auth.cli list                # 简表：账号 id/状态/额度/名称
docker compose exec -T backend python -m app.auth.cli create --name 'XX' --quota 100   # 新建账号，邀请码只打印一次
docker compose exec -T backend python -m app.auth.cli add-quota <user_id> 100          # 加额度
docker compose exec -T backend python -m app.auth.cli disable <user_id>               # 封禁（立即踢下线）
docker compose exec -T backend python -m app.auth.cli rotate-code <user_id>           # 换邀请码（旧码作废，新码只打印一次）
docker compose exec -T backend python -m app.auth.cli revoke-sessions <user_id>       # 强制全部设备下线
```

## 关键事实与注意

1. **邀请码明文不落库**：库里只存 HMAC 哈希；`create`/`rotate-code` 打印的邀请码必须当场保存，丢失只能 rotate 换新码。
2. **一账号一邀请码**：`users.invite_code_digest` 是 UNIQUE；rotate 是替换不是新增。
3. **quota 粒度**：扣减发生在 `/api/chat`（后日谈自由聊天）；固定剧本 /story 和序章探班不消耗 quota。
4. 账号会话/游戏会话数据来源：`auth_sessions`、`game_session_owners` 表；统计 SQL 见 repository.py 的 `usage_stats()`。
5. **不要写任何邀请码明文、密码、API key 进 skill/仓库/提交记录**。

## 离线 SQL 等价查询（不依赖 CLI 时）

```bash
docker compose exec -T postgres psql -U gal -d gal -c "
SELECT u.display_name,
       u.quota_used || '/' || u.quota_total AS quota,
       u.last_login_at,
       count(s.token_digest) AS logins,
       count(s.token_digest) FILTER (WHERE s.revoked_at IS NULL AND s.expires_at > now()) AS active_sessions
FROM users u
LEFT JOIN auth_sessions s ON s.user_id = u.id
GROUP BY u.id ORDER BY u.created_at;"
```
