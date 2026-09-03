# readme-fact-hygiene — README 事实口径修正（P0：求职口径诚实性）

- 状态：PASS
- 日期：2026-09-04
- 环境：本地（README 编辑 + 测试复跑）
- 依据：`validation-results/eval-memory-recall-realdata/result.md`（提案率 3.2%）、`validation-results/memory-write-fewshot/result.md`（few-shot 后仍 3.2%，路线 B 关闭）、`deploy/STATUS.md`（线上仅 DEEPSEEK_API_KEY）、`backend/app/main.py` build_provider（默认共享 DeepSeek adapter）

## 目的

README 是求职第一接触面。修正三处与线上事实不一致或缺失披露的口径，避免把确定性状态机包装成 Agent：

1. 测试数字 556 → **558**（README 两处；实测 558 passed, 12 skipped）。
2. 披露线上仅 DeepSeek 真机（ChatGPT/Claude/豆包 后日谈由 DeepSeek 扮演，无 key 环境回落 mock）。
3. 披露记忆写入层真实数据提案率 **3.2%**（4/126）与 few-shot 引导失败（仍 3.2%），记忆系统标注为「检索层就绪，生产写入机制待验证」。

## 变更

- `README.md` 五处：
  - 「在线体验」补充 DeepSeek 真机口径；
  - 「技术亮点·记忆系统」追加写入层待验证标注；
  - 「工程纪律」「测试与验证」556 → 558；
  - 「评测」节新增「记忆写入真实数据复验」条目（3.2% + few-shot 无效 + 报告链接）。

## 验证

- 后端：`backend && .venv/bin/python -m pytest -q` → **558 passed, 12 skipped**（GAL_PROVIDER=mock）
- 前端：`frontend-vue && npm run test:unit` → **77 passed**（26 files）
- `git diff --stat` 仅 README.md 一个文件。

## 限制

- 无。本次为纯文档修正，不改代码路径。
