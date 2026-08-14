## TV-15

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed).

Goal: 验证单次外部模型或生成失败不会摧毁Session (docs/06 §21). The three required simulated cases — A Provider Timeout, B Invalid Structured Output, C 空Response — must each leave the session intact: Game State不被错误提交, Completed Event不被提前写入, Invalid内容不进入正式Memory, Player得到可恢复反馈, Retry后Session可以继续.

Design (what already enforced the contract, consolidated and gap-filled):

- **Provider layer** (`app/providers/deepseek.py`): `httpx.HTTPError` (timeouts included) → `ProviderError`; empty content/choices → `ProviderError` (docs/04 §55 recoverable). Gap-filled with an explicit timeout test: `httpx.TimeoutException` surfaces as `ProviderError`, never a crash.
- **Runtime layer** (docs/04 §48-55): invalid/empty structured output → Schema Validation rejects → one targeted Repair → Safe Fallback; a provider failure is propagated, not masked by a fabricated reply.
- **Orchestrator layer** (docs/03 §28): the narrative event is evaluated before the character speaks but committed only after its output succeeds — a failed turn changes neither state nor memory, and (TV-14) writes no snapshot.
- `backend/tests/test_failure_recovery.py` (new, 6 tests) ties the whole docs/06 §21 contract together:
  - Case A: a timeout on the turn that would fire `EV_POC_CLAUDE_APPEARS` → `ProviderError` raised, flags and completed_events empty; the identical retry succeeds, fires the event, and keeps the same session (message_count=2). The same scenario through persistence: the failed turn writes no snapshot, the retry's snapshot carries the event, and a fresh orchestrator restores it without re-firing.
  - Case B: a model answering non-JSON prose every time → repair fails → the player gets the safe fallback line; the invalid content never enters history or memory; the session continues.
  - Case C: valid JSON with an empty dialogue → rejected → repair fails → safe fallback; and provider-empty content → recoverable `ProviderError`, no state committed.
  - API level: a mid-session provider failure returns 503 (recoverable feedback, never a fabricated reply); the retry with the known session id continues the SAME session (message_count=3).
- `backend/tests/test_provider_deepseek.py`: +1 test (timeout → `ProviderError`).

Automated tests: full backend suite **163 passed** (was 156, +7: 6 consolidated + 1 timeout mapping).

Live model validation (real DeepSeek, failures injected per docs/06 §21「必须模拟」, recovery through the real chain):

- Case A (timeout injected into the first character call): `ProviderError` raised; state after the failure had no flag and no completed event; the retry of "是谁把我们抓来的？" got a real reply ("唔～我也想知道呢…") and the event committed correctly; message_count=2, same session.
- Case B (non-JSON prose injected): the runtime's targeted repair call reached the real model (repair prompt with `[系统提示]` present in the recorded call) and DeepSeek answered validly ("你好呀！我们现在是被困在哪里了呀？…"); the injected prose never entered history; no memory written; the next turn continued.
- Case C (empty string injected): repaired through a real-model call into a valid reply; no memory written; the next turn continued.
- All deterministic checks True for every case (Summary: Case A=True Case B=True Case C=True).

Finding during this TV: Case A at the orchestrator level is uniform for timeout / HTTP error / empty content — the provider adapter already collapses all of them into `ProviderError`, so the same recoverable path protects every Case-A-like failure. The genuinely distinct paths are provider-failure (raise → retry) vs malformed-content (repair → fallback), and both are exercised.

Failures: None in the final run.

Known limitations:

- The failure of the first-ever turn (no known session id yet) surfaces as 503 without a session id, so a retry after that specific 503 starts a new session; a failure after any successful turn always keeps the known session (covered by the API test).
- A failed turn's player message remains in the message log (it was appended before the character call, pre-existing TV-03 behavior); the narrative state and memory are untouched, and no snapshot is written.
- The injected failures are simulated by design (docs/06 §21 requires simulating them); the recovery path is the real one.

Evidence: `validation-results/TV-15/response-samples.md`, harness `run_live_validation.py`, passing automated suite (163).

Conclusion: PASS — a timeout, an invalid structured output, or an empty response neither destroys the session nor commits anything prematurely; the player gets a recoverable signal and a retry continues correctly. Next validation: TV-16 (End-to-End Stability, the Final Gate).
