# memory-partition-fix — 画像分区不变量修复 + 画像通道语义召回

- 状态：PASS
- 日期：2026-09-03
- 环境：macOS / Python 3.12 / GAL_PROVIDER=mock
- 触发：eval-memory-recall 实验发现（2026-09-03）

## 问题

实验发现两个真实缺陷：

1. **分区不变量破坏**：溢出 top-5 画像窗口的玩家画像（最早的 player_* 记忆）不再被 player_ids 识别，经一般窗口语义召回被"救回"，并进入强化循环——违反 docs/05 §38 的互斥不变量（同一 Memory 只出现一次、player_* 绝不进通用窗口）。
2. **画像通道无语义召回**：retrieve_player_notes 只按 recency 排序，cap 5 会把玩家主动提起的更早画像永久挤出。

## 修复

- app/game/memory.py：
  - retrieve_context 的 player_ids 过滤改为基于该角色**全部** player_* 记忆 id（而非仅当前画像窗口内），互斥不变量在窗口溢出时依然成立；
  - retrieve_player_notes 增加 query 参数：与通用窗口一致的相关性排序（bigram Jaccard，deterministic，无 embedding），玩家主动提起的更早画像被带回画像窗口；
  - retrieve_context 把 query 同时转发给两个窗口。
- docs/MVP/05 — Memory Design.md：§38 补记轻量相关性排序与互斥不变量；§39 加注（bigram 排序不属于 Semantic Retrieval）。
- 回归测试（2 新增）：
  - test_memory_relevance.py::test_retrieve_player_notes_with_query_surfaces_older_relevant_note
  - test_relationship_and_player_model.py::test_partition_invariant_holds_for_player_notes_outside_window

## 验证

| 项 | 结果 |
|---|---|
| 后端全量 pytest | 558 passed, 12 skipped（原 556 + 2 新增） |
| 记忆召回实验重跑（Layer 1） | 一般记忆 5/10 → 10/10 不变；画像通道 OFF 5/6 → ON 6/6；泄漏通道 0/6（修复前 ON 1/6） |
| 小明（最旧画像）修复前 | ON=GEN（泄漏进一般窗口，被强化） |
| 小明（最旧画像）修复后 | ON=PL（画像通道语义召回，不参与强化） |
| 强化侧查修复后 | 一般窗口 10/16；全部 6 条 player_* 0 次强化（修复前小明被误强化） |

## 已知限制

- 画像通道仍不参与 decay/reinforce（与合并时语义一致，docs/05 §66 只覆盖一般窗口）。
- Layer 2 真机引用命中率不受本修复影响（修复前 3/4 中小明经泄漏通道同样进上下文），未重跑真机。
- 服务器生产仍为 4e85c86，未部署本次修复（部署随下次整包上线）。
