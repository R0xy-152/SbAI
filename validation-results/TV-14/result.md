## TV-14

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed). Frontend: static Gal UI, session id persisted in `localStorage`.

Goal: 页面刷新或重新进入后可以恢复基本游戏 (docs/06 §20). After a refresh, the restored session must keep: the message history, the current Scene, the current Character, the Narrative flags, the completed events (which must NOT re-fire), and each character's Important Memory scope — and the player must be able to continue sending new messages.

Design:

- **Storage decision (asked, 2026-08-14)**: docs/02 §23 documents PostgreSQL as the persistence layer, but the machine has no Docker/psql and no DB driver, and docs/06 §20 only defines the validation contract, not the mechanism. Chosen: a durable JSON-file Repository as the TV-14 fixture behind the docs/02 §22 Repository boundary (Game Logic → Repository → store), clearly marked Fixture ≠ Production; PostgreSQL remains the target backend behind the same `SessionRepository` interface.
- `app/persistence/repository.py` (new): `PersistedSession` holds the docs/02 §21 session fields (session_id, messages, current_scene, current_character) plus the narrative state and the memory scopes; `SessionRepository` ABC; `JsonSessionRepository` writes one JSON file per session, atomically (`os.replace` on a temp file, so a crash mid-write leaves the previous snapshot intact); a corrupt/partial file loads as `None` — like SessionStore, an unusable id simply becomes a fresh session.
- `app/game/orchestrator.py`: optional `repository`. `_resolve_session` restores a known persisted id (Session Restore) and otherwise falls back to `get_or_create` — unknown ids still mint a fresh uuid, never trusting a stale client. After every **successful** turn a `_snapshot` is saved, so a failure never writes half a turn. `_restore_session` seeds the message store, narrative state, memory store, current character and current scene back into the process.
- `app/game/state/session.py`: `get` (non-mutating lookup) and `restore` (seed a persisted session under the id the client already knows).
- `app/game/memory.py`: `snapshot` / `from_snapshot`, rebuilding the id counter from the latest `created_at` so restored memories keep monotonic ordering and new ids don't collide.
- `app/main.py`: the running app wires `JsonSessionRepository` at `backend/data/sessions/` (gitignored).
- `frontend/app.js`: `session_id` is kept in `localStorage` (guarded for the Node DOM-stub tests), so a real browser refresh sends the same id back and the backend restores the session.

Automated tests (`backend/tests/test_session_restore.py`, 9 tests): the full docs/06 §20 refresh contract (history, scene, flag, completed event, memory scopes, current character, no event re-fire, continues) against a refresh that discards every in-memory store and shares only the repository; a restored current character answers a character-less turn; unknown ids still mint fresh; without a repository nothing persists; the snapshot file carries the full history; a failed turn leaves the snapshot byte-identical (and a fresh orchestrator never sees the failed message); a corrupt snapshot falls back to a fresh session; serialization round-trips narrative sets and memories; restored memory stores keep ids and ordering. Frontend `frontend/tests/tv14-session-restore.test.cjs` (3 checks): the stored id is sent after a refresh, a new id is written back, and reused. Full backend suite: **156 passed** (was 147, +9); frontend tv01/tv02/tv03/tv14 all PASS.

Live model validation (real DeepSeek):

- Session A built the full pre-refresh state: "我很怕黑，从小就怕。记住这件事。" → memory written (`['Player提到自己从小怕黑']`); "是谁把我们抓来这里的？" → SIG_ASK_CAPTOR → `EV_POC_CLAUDE_APPEARS` committed (`claude_has_appeared` flag + completed_events); 12 turns / 26 messages total.
- Refresh: a brand-new orchestrator (fresh SessionStore, NarrativeState, MemoryStore — the only shared thing is the JSON files, exactly like a backend restart) over the same repository.
- Session B: the same session_id was restored (26 messages, scene `binding_room`, flag + completed event present). The fear statement was **out of the 20-message Recent window** yet still in DeepSeek's `memory_context` — proving the restore came from the Memory scope, not the recent conversation. Asked "你记得我告诉过你的事吗？" DeepSeek recalled: "我记得你说过你怕黑来着？是吧？". Re-triggering SIG_ASK_CAPTOR evaluated to `noop` (event does not re-fire). A new message continued the session (message_count=13). Claude addressed directly got no DeepSeek memory (prompt had no "怕黑") and answered in persona.

Finding during this TV: the restore is validated at the process level, not the object level — a fresh orchestrator over the same repository is the honest simulation of a page refresh / backend restart. The restore-first resolution means a known session is reloaded from disk on each turn; correct for the validation phase, noted as a limitation below.

Failures: None in the final run.

Known limitations:

- Storage is the JSON-file fixture, not PostgreSQL (docs/02 §23 target); the `SessionRepository` interface is the swap point.
- One file per session under `backend/data/` (gitignored); no TTL/cleanup for abandoned sessions yet.
- A provider-failed turn is not persisted — the player's failed message is lost across a refresh (failure semantics are TV-15's scope).
- Per-session `current_scene` is currently restored into the orchestrator's single shared `Scene`; true per-session scenes are the docs/02 §21 target, deferred.
- The frontend restore depends on `localStorage`; private-mode browsers degrade to "the session lasts for the page load" (guarded, non-fatal).

Evidence: `validation-results/TV-14/response-samples.md`, harness `run_live_validation.py`, passing automated suites (backend 156, frontend tv01-04).

Conclusion: PASS — history, scene, character, narrative flag, completed-event non-replay, and character-scoped memory all survive a process-level refresh, and the game continues normally. Next validation: TV-15 (Failure Recovery).
