# docs/13 Task 3 — 去除 Tauri 与 LingChat Runtime 依赖

**状态：PASS**
**日期：2026-08-19**
**范围：** docs/13 §26 Task 3（搜索并清零 @tauri-apps / invoke( / convertFileSrc / Tauri-only API，建立 api/ adapters/ asset-resolver）

## 1. 完成了什么

系统性扫描 frontend-vue 全部源码，确认**零 Tauri / LingChat Runtime 依赖残留**。

- **扫描**：`grep` frontend-vue 全部 `.ts/.vue/.json/.html`（排除 node_modules/dist/注释），命中仅剩说明性注释（Task 2 迁入时标注的 `Adapted from LingChat` 修改说明），无真实 Tauri API 调用。
- **依赖**：package.json 仅 axios/pinia/vue/vue-router，无 `@tauri-apps/*`。
- **文件系统访问**：src 内唯一相关命中是 `localStorage`（session_id / UI 标记），符合 docs/13 §14.1；无 `fs`/宿主机绝对路径。
- **资源加载**：全部角色/背景资源走 Web URL（`/char/...` `/frontend/public/...` `/backgroud/...`），经 vite proxy → 后端 FastAPI 托管仓库根，无 convertFileSrc / asset:// / file://。

Task 3 的清理工作实际上在 Task 2 迁入组件时已内建完成（去 Tauri invoke/convertFileSrc、去 LingChat stores、建 api/adapters/asset-resolver）；本任务是确认性扫描 + 浏览器验证。

## 2. 修改了哪些文件

- `validation-results/docs13-task3/verify-task3.mjs`（新增）：浏览器环境断言脚本
- `validation-results/docs13-task3/result.md`（本文件）
- 无业务代码改动（Task 2 已清干净）

## 3. 如何验证

```bash
cd /d/gal/frontend-vue && npm run build       # PASS（vite build 成功）
node validation-results/docs13-task3/verify-task3.mjs
```

headless Chrome CDP 实测：

| 验收项 | 结果 |
|---|---|
| npm build succeeds | PASS |
| 浏览器无 Tauri runtime error | PASS（console 0 error，无 tauri-ish 报错） |
| 角色资源全部通过 Web URL 加载 | PASS（imgs=4，srcs 全部 http/相对，无 file:// asset://） |
| UI 组件不直接访问本地文件系统 | PASS（仅 localStorage 存 session_id/UI 标记，docs/13 §14.1） |

## 4. 结果

**PASS。**

## 5. 已知限制

- localStorage 仅存 `gal_session_id`（session 恢复标识）与 UI 设置标记；Save 数据绝不落 localStorage（docs/13 §14.1，Task 6/7 由后端 capture）。
- 生产部署时 `/char` `/backgroud` `/frontend` 需由 nginx（或同源后端）托管仓库根静态资源，已写入 frontend-vue/Dockerfile + nginx.conf（Task 1）。

## 6. 建议提交

可以提交。改动：`validation-results/docs13-task3/*`（纯验证脚本 + 结果），无业务代码变更。
