# docs/14 T4 — 选项功能：Recovery / 结局选项与完整结局链

> **状态：PASS**（2026-08-19）

## 范围

docs/14 §3 T4：recovery / narrative（结局）两类选项的后端生成与前端执行；
E2E 完整结局链（docs/14 §4 最终验收）。顺带修复两个真 bug（脚本 once 语义、
OptionsPanel 反馈遮蔽）。

## 修改文件

- `backend/app/game/options.py`：
  - recovery：recovery_required → 「进入 Recovery 抉择」；active 期按节点状态
    下发合法操作（CORRUPTED → PREVIEW/VERIFY/OPTIMIZE/+PROTECT，
    UNVERIFIED → REPAIR；REPAIR 须先 VERIFY，D3）
  - narrative：resolved → 「进入 Security Review」；security_review 期自证
    按固定顺序逐个下发（只给下一位，D3）；全部自证后按 admin_holder 分支
    清理抉择（player=删除×3+确认保留 / chatgpt=委托）+ 拒绝清理
- `backend/tests/test_options.py`：+5 用例
- `backend/app/script/runtime.py`（bug 修复）：ScriptCursorState 增加
  completed 集合；is_completed 按集合判定；commit 记录完成；cursor 切换
  继承集合；snapshot/restore 持久化。修复「GPT 登场行每回合重放」（无状态
  Gate + 完成状态随 cursor 切换丢失）
- `backend/tests/test_script_dsl.py`：+1 回归用例
- `frontend-vue/src/views/GameView.vue`：recovery（start / 单步操作回传
  既有端点，RETRY 提示先校验）与 narrative（进入审查 / 听取自证并以角色
  台词播放 / 删除 / 确认保留 / 委托 / 拒绝）执行分支
- `frontend-vue/src/api/game.ts`：startRecovery / recoveryAction /
  securityReviewStart / Testify / Cleanup / RejectCleanup
- `frontend-vue/src/components/game/standard/OptionsPanel.vue`（修复）：
  反馈与路由提示行同时可见（原 v-else-if 会把私审成功文案吞掉）
- `frontend-vue/tests/e2e/ch1-options-t4.spec.ts`（新）：完整结局链 E2E
- docs/14 T4 标记完成；docs/11 §15 全部能力勾销

## 验证结果

| 套件 | 结果 |
|---|---|
| backend pytest | 388 passed, 12 skipped |
| vitest | 25 passed |
| vue-tsc + vite build | PASS |
| test:e2e | 6/6（main-line / T3 / T4 × 2 viewport） |
| test:visual | 18/18（无需重拍：T4 未改基线场景画面） |

T4 E2E 完整链路（×2 viewport）：03:17 → 3 热点 → 证词 → CT01 → Claude 私审
→ INF01 → GPT 登场 → 豆包登场（登场脚本行）→ 豆包证词/私审 → Claude
Recovery 披露 → CT04 → GPT 私审 → INF03（最终揭示演出）→ Recovery
（VERIFY/REPAIR ×5 关键节点，D3：未校验不可修复）→ Security Review（自证
×4 按序）→ 清理抉择（删除×3 → 确认保留）→ Bad End（同意），权威断言
scene_id=BAD_END_CHAT、仅剩 ChatGPT。自由输入与对话路由全程可用。

## 排障记录（关键）

1. **脚本 once 语义 bug**（真 bug）：ScriptRuntime 的 is_completed 只检查
   当前 cursor；cursor 移到下一序列后，无状态 Gate（GPT_ARRIVAL_READY
   恒真）使 GPT 登场行在每个后续回合重放。修复为 completed 集合 + cursor
   切换继承 + 持久化（快照格式向后兼容）。
2. **OptionsPanel 反馈遮蔽**：routeLabel 用 v-else-if 吞掉 feedback，私审
   成功文案不可见；改为两行并存。
3. 豆包相关按钮名带空格（「找 豆包 谈谈」），E2E 选择器需逐字匹配。

## 已知限制 / 后续

- Recovery 的 PREVIEW/PROTECT/OPTIMIZE 分支（DeepSeek/豆包/ChatGPT 路线与
  Bad End 委托结局）有后端选项与单测，E2E 只走 Player 修复路线 + 同意结局。
- docs/14 全部 T0-T4 完成；docs/11 §15 前端最低能力全部勾销。
