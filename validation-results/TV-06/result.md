## TV-06

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), deterministic providers in tests (no network/key). Built on TV-05's structured-response validation.

Goal: Prove that unvalidated model content never becomes official game content (docs/06 §12): fabricated invalid generation results must not enter official History, affect Game State, write official Memory, or be shown directly to the Player; afterward Repair succeeds or Safe Fallback succeeds (docs/04 §51-54).

What was tested (all with fabricated invalid outputs, via `backend/tests/test_validate_before_present.py`, 5 tests):

1. Wrong `character_id` (model claims to be another character and answers with a fact it must not know, "我看见墙上写着密码 0427") → rejected; the player receives the safe fallback line, and "0427" appears nowhere in session History.
2. Nonexistent animation (`animation_proposal: "spin"`) → rejected; safe fallback only.
3. Non-JSON / malformed model output → safe fallback only; the raw invalid text never appears in History.
4. Game State invariant: an invalid turn still counts exactly one player turn and commits exactly one safe reply — nothing extra is written.
5. Baseline: valid output does enter History as approved content (the real dialogue, not the fallback).

Why the guarantees hold: `DeepSeekRuntime.respond()` returns only schema-validated responses (TV-05) — on invalid output it repairs once, then returns a story-neutral safe fallback. The orchestrator appends only that returned response to session History, and the API returns only its dialogue, so invalid raw content cannot reach History or the player. `memory_proposals` are validated but not yet persisted by any system, so "no official Memory write" holds trivially at this stage.

Full backend suite: 84 passed (79 prior + 5 new).

Failures: None.

Known limitations:

- The "references a fact the character is not allowed to know" case is only demonstrated combined with a schema violation (wrong character_id). A pure same-character forbidden-fact rejection needs the Knowledge/Memory-scope system (Character Validation, docs/04 §49), which arrives in later TVs.
- There is no Game State beyond session messages yet, so the "Game State" guarantee is tested against message state only; Narrative State checks come with the Narrative Runtime.
- No Memory system exists yet, so "no official Memory write" is satisfied by construction and noted, not asserted against a Memory store.

Evidence: passing test suite (`backend/tests/test_validate_before_present.py`), full suite 84 passed.

Conclusion: PASS — invalid generated content is rejected before it becomes official, and Repair/Safe Fallback behave as specified. Next validation: TV-07 (Short-term Context) — 10 consecutive turns, player name must be recoverable without hardcoding.
