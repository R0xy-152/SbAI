# 序章对话交互与立绘修复验证

- 状态：PASS
- 日期：2026-08-21
- 环境：Windows 11；Node.js 24.18.0；Vitest 4.1.11；Python 3 / pytest

## 验证范围

1. DeepSeek 害羞立绘替换为用户修复的 1024×1536 ARGB PNG。
2. 对话标题栏不再渲染角色副标题。
3. 表情差分先预加载，再在单一 `img` 节点上原子替换。
4. 序章剧本台词、段落标题与运行时展示中的「后日谈」已统一替换为「序章」。
5. 全屏点击、空格键和滚轮向下可推进台词，现有交互控件被排除。
6. 滚轮向上打开半透明对话历史窗口；窗口内使用原生纵向滚动，右上角 X 关闭。
7. 打字中推进会立即补全本句，120ms 后只进入下一句一次。

## 可复现命令与结果

- `cd frontend-vue && npm run test:unit`：24 个测试文件、71 个用例全部通过。
- `cd frontend-vue && npm run build`：类型检查与 Vite 生产构建通过。
- `cd backend && .venv/Scripts/python -m pytest -q`：456 通过，12 跳过，1 条既有 Starlette 弃用警告。
- `rg -n "后日谈" docs/story/Prologue.md backend/app frontend-vue/src`：无匹配。

## 限制

- 本轮未使用真实鼠标/触控板做人工手感评估；输入排除、历史内容与打字机时序由自动化回归测试覆盖。
