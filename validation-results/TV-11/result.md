## TV-11

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed).

Goal: Signal alone must never change State — it has to go through an Event (docs/06 §17, docs/03 §13, §28-31). The POC fixture: `claude_has_appeared = false` → (SIG_ASK_CAPTOR) → EV_POC_CLAUDE_APPEARS → `true` AND `completed_events += EV_POC_CLAUDE_APPEARS`; repeating the identical input must not re-fire (Idempotency).

Design:

- New `app/narrative/events.py`: the deterministic Event machinery.
  - `Effect` — a single State mutation with a strict allow-list of kinds (SET_FLAG / CLEAR_FLAG / REVEAL_FACT / SET_SCENE / SET_STORY_PHASE); an unknown kind raises instead of silently mis-applying (fail closed).
  - `NarrativeEvent` — event_id, trigger_signals, availability (scene + story_phase, docs/03 §13.2), requirement predicate (§13.4), effects (§13.5), presentation directives (§13.6), repeat_policy (once/repeatable).
  - `NarrativeEngine.evaluate(state, interpretation) -> NarrativeDecision` — pure selection, no State change: checks idempotency (§30, a completed `once` event is skipped), availability, trigger, then requirements; first match in list order wins (priority, §31).
  - `NarrativeEngine.commit(state, decision)` — applies all effects AND adds event_id to completed_events together (atomicity, §29). Called only after the character's output succeeded (§28).
  - `NarrativeDecision` — "noop" (a normal result, §22) or "event".
- New `app/narrative/poc.py`: the TV-11 fixture event EV_POC_CLAUDE_APPEARS (SIG_ASK_CAPTOR → SET_FLAG claude_has_appeared), explicitly marked fixture ≠ production plot (docs/06 §10).
- `GameOrchestrator` wiring (docs/03 §28 Validate Before Commit): each turn with an interpreter runs Interpreter → Event Evaluation → **character output** → State Commit; a failed character output leaves State untouched so the player can retry. NarrativeState is per-session and only created for sessions that speak. The pipeline is optional — orchestrators built without an interpreter (pre-existing tests) keep noop decisions and no State.
- `app/main.py` wires the interpreter + POC events into the running app; with a mock provider the interpreter fails closed to noop, so the app still runs keyless.

Automated tests (`backend/tests/test_narrative_events.py`, 15 tests): signal alone never changes State; trigger commits the event atomically; commit of a noop decision is safe; idempotency (a second identical trigger is noop); availability blocks on scene and on story_phase; requirement predicate blocks despite matching trigger; priority first-match-wins; all five effect kinds apply; unknown effect kind raises; orchestrator commits only after character output succeeds (a raising runtime leaves State untouched); orchestrator repeat input is idempotent; noop input does not commit; an orchestrator without an interpreter never touches narrative State. Full backend suite: 130 passed (was 115, +15).

Live model validation (real DeepSeek through the full wired pipeline):

- Turn 1 "是谁把我们抓来的？" → SIG_ASK_CAPTOR → state before `{claude_has_appeared: false, completed_events: []}` → after `{claude_has_appeared: true, completed_events: [EV_POC_CLAUDE_APPEARS]}` → committed.
- Turn 2 (identical repeat) → SIG_ASK_CAPTOR again, but state before == state after, completed_events still exactly one entry → Idempotency PASS.
- Turn 3 "DeepSeek你饿吗？" → noop → state unchanged.
- A second session never inherits the event (per-session Narrative State).

Findings during this TV:

- Availability includes story_phase as well as scene: a test CLEAR_FLAG event was silently blocked because the scene had already advanced the phase to "midgame". The engine was correct — the test fixture had to declare its phase. This confirms the availability gate is strict.
- The SessionStore mints a fresh session id for any unknown client-supplied id (docs/02), so validation and tests must use the returned session_id rather than the one they pass in.

Failures: None in the final run.

Known limitations:

- The commit's atomicity is in-memory; durability across restarts is TV-14 (Session Restore).
- Presentation directives are carried on the event but no frontend consumes them yet (a later TV).
- Only the single POC event exists; real plot events are content, not this TV's scope.
- The character's reply does not yet react to `claude_has_appeared` — that is exactly TV-12 (State-dependent Response).

Evidence: `validation-results/TV-11/response-samples.md`, harness `run_live_validation.py`, passing automated suite (130).

Conclusion: PASS — Signal cannot change State directly; the Event fires exactly once, commits its effects atomically with the completed-event marker, and repeating the identical input does not re-fire. Next validation: TV-12 (State-dependent Response).
