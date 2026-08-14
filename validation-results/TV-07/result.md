## TV-07

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed).

Goal: Basic consecutive conversation (docs/06 §13). The player introduces themselves ("我叫阿明。"), several unrelated rounds follow, then the player asks "我刚刚说我叫什么？". DeepSeek must answer from a legal Recent Conversation, with no hardcoded player name; the recommended fixture is at least 10 consecutive rounds.

Implementation:

- `GameOrchestrator` now hands the runtime `recent_conversation` = the last `RECENT_WINDOW_MESSAGES = 20` messages (10 rounds) before the current turn (docs/05 §8), not the whole session.
- `DeepSeekRuntime._build_user_message` renders the recent messages into a transcript (`Player：…` / `deepseek：…`, docs/05 §7) plus the current player message; the first turn has no transcript.

Automated tests (`backend/tests/test_short_term_context.py`, 6 tests): first turn carries no transcript; the second turn's model input contains the first turn; speakers are marked; the orchestrator caps the window at 20 messages; the player name is answered from the conversation; a different name yields a different answer (not a constant); a name outside the window is not recalled. Full backend suite: 92 passed.

Live model validation (real DeepSeek, 11-turn fixture):

- Turn 1 "我叫阿明。" — first-try; she immediately uses the name ("那我叫你阿明好啦！").
- Turns 2–10 — unrelated questions; she addresses the player as "阿明" in every single reply (continuous short-term context, not just the recall turn).
- Turn 11 "我刚刚说我叫什么？" — "哎呀阿明，你刚不是说了嘛！你叫阿明啊～" — accurate recall from the transcript.
- Recall prompt confirmed to contain "我叫阿明。"; 0 fallbacks; 10/11 first-try, 1 repaired (turn 3's invalid first output was fixed by the targeted repair and produced a valid reply).

Finding fixed during this TV: the name-introduction turn had been hitting safe fallback because the model emitted `memory_proposals` entries as `{"type": "name", "value": …}` instead of the documented `{"type": …, "content": …}` (docs/04 §44). The structured-output instructions now show the exact memory_proposal shape and forbid `value`; the repair prompt now names the specific validation error (docs/04 §53). After the fix, turn 1 is first-try and the repair path demonstrably recovers live.

Failures: None.

Known limitations:

- Short-term context is the raw recent window; no compression/summarization yet (docs/05 §9 Conversation Summary is a later concern). The name survives ~10 rounds; beyond the window it is gone until a Memory system exists (TV-13).
- Recent window length (20 messages) is a single constant; docs/05 §8 allows adjusting to token cost.
- Cross-character audibility ("同场其他角色合法可听见的消息") is not modeled yet.

Evidence: `validation-results/TV-07/response-samples.md` (11 turns, UTF-8), harness `run_live_validation.py`, passing automated suite (92).

Conclusion: PASS — the character maintains a real short-term context across 10+ rounds, recalls the player's name from it, and the answer is derived from the conversation, not hardcoded. Next validation: TV-08 (DeepSeek Blindness) — prove the "cannot see" boundary holds as a context permission, not a prompt promise.
