# 二维码填充邀请码直达开始界面 — 验证结果

- **状态：** PASS
- **日期：** 2026-09-03
- **方案：** 档位 B（`https://sbai.xin/login#invite=<邀请码>`，前端读 `route.hash` 自动登录直达 `/`）
- **环境：** macOS；前端 Node v26.0.0 / vitest 4.1.11 / vue-tsc 2.1.10；后端 Python 3.12.14（venv 安装 segno 1.6.6）

## 改动

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `frontend-vue/src/views/LoginView.vue` | 修改 | 读 `route.hash` 的 `invite` 参数，预填并自动登录，回跳 `/` |
| `frontend-vue/src/views/__tests__/LoginView.spec.ts` | 新增 | 3 条单测：hash 自动登录回跳 `/`、无 hash 不自动登录、手动提交回跳 redirect |
| `deploy/gen_invite_qr.py` | 新增 | 读 `invite-codes.md`，用 segno 逐码生成二维码 PNG + MANIFEST.md |
| `deploy/invite-qr/` | 生成 | 53 张 PNG + MANIFEST.md（未入库，见限制） |

## 用例与结果

| 用例 | 结果 | 证据 |
| --- | --- | --- |
| `#invite=CODE` 挂载后自动 `loginWithInvite('CODE')` 且 `replace('/')` | PASS | LoginView.spec.ts case 1 |
| 无 `#invite` 片段时不自动登录 | PASS | LoginView.spec.ts case 2 |
| 手动输入提交仍回跳 `redirect` | PASS | LoginView.spec.ts case 3 |
| vue-tsc 类型检查 | PASS | `npm run typecheck` exit 0 |
| 全量前端单测 | PASS | 25 files / 74 tests（71 存量 + 3 新增） |
| 二维码内容正确 | PASS | zxing-cpp 解码 5 张抽样，均等于 `https://sbai.xin/login#invite=<码>`；53 张 PNG 296×296 |

## 限制与阻塞

1. **台账 vs 线上账号不同步**：`invite-codes.md` 有 53 个码，但 `deploy/STATUS.md` 显示线上仅展示账号 01/02/03。二维码未对 DB 校验，非在库码扫码会 401；分发前须以 `auth.cli list` 对齐真实账号后再出图。
2. **Node 26 环境问题（非本次改动引入）**：Node v26 自带的 `localStorage` 全局会遮蔽 happy-dom，跑 vitest 需加 `NODE_OPTIONS=--no-experimental-webstorage`；存量 71 用例同样受影响。
3. 邀请码仍会留在浏览器历史（`login#invite=...` 那条记录），等价于「分享明文码」，docs/18 §4 已列为可接受限制。
4. 未做线上真实扫码端到端验证（仅单测 + 二维码解码）；上线前建议用一张真码在 `https://sbai.xin/` 走一遍。

