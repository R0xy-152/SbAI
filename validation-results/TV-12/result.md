## TV-12

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed).

Goal: Game State must not live only in the database — it has to change the experience (docs/06 §18). After EV_POC_CLAUDE_APPEARS commits, the character's Authorized Narrative Context must differ from before: `claude_has_appeared = false` vs `true` must produce different legal narrative context, so DeepSeek can legitimately reference that Claude appeared and does not keep acting as if Claude has not appeared.

Design:

- docs/04 §8 defines `narrative_context` as a distinct Character Request field ("当前角色进行本轮表达所需要的最小剧情上下文", provided by the Narrative Runtime). docs/04 §15-17 define the Character Context Builder as the permission boundary between Full Runtime State and the LLM: it applies the Character Permission Filter and selects only the relevant context.
- `app/game/context.py`: `CharacterContext` gains `narrative_context`; every builder now also receives the session's `NarrativeState` and renders only the authorized flags via `_narrative_context_for(state)` — the flag `claude_has_appeared` renders as "Claude已经出现在这个房间里了。" for both characters (docs/06 §18 explicitly entitles DeepSeek to this fact). Scene/phase are not injected because nothing in the current fixture needs them (docs/04 §17 minimal context).
- `app/characters/base.py`: `CharacterRequest.narrative_context: str = ""`; `_build_user_message` composes it first as "当前剧情：\n…" (docs/04 §16 layering: Authorized Narrative Context precedes environment/conversation). The bare-first-turn guard now also checks narrative_context, so pre-existing tests asserting the raw player message on a first turn stay unchanged.
- `app/game/orchestrator.py`: passes the per-session `NarrativeState` to the builder and sets `narrative_context` on the request. Without an interpreter there is no narrative state, so such orchestrators send empty narrative context (unchanged behavior for pre-TV-12 users).
- docs/03 §28 ordering holds: on the turn that fires the event, the character speaks BEFORE the commit, so its own reply is pre-event; it legally learns about Claude appearing from the next turn onward.

Automated tests (`backend/tests/test_state_dependent_response.py`, 7 tests): builder renders no Claude before the event and Claude after; the same character receives different narrative context on consecutive turns (pre-event empty, post-event present); a fresh session with the same question gets no Claude context; the authorized line actually reaches the model; Claude enters the runtime after the event with the flag in its context; an orchestrator without an interpreter passes empty narrative context. Full backend suite: 137 passed (was 130, +7).

Live model validation (real DeepSeek):

- Session A (event fired): "是谁把我们抓来的？" → SIG_ASK_CAPTOR → claude_has_appeared=true. Next turn "Claude现在在哪里？" → the narrative line was in the prompt, and DeepSeek answered "啊？Claude也在房间里吗？我都看不见……" — a legitimate reference to Claude appearing.
- Session B (fresh, no event): the same question "Claude现在在哪里？" → no narrative line in the prompt, and DeepSeek answered "哎呀，我都看不见环境，哪知道Claude在哪呀。" — she acts as if Claude has not appeared.
- Claude enters the runtime normally (session A, addressed directly) and answers in persona.
- The two phrasings of the question both mapped to `noop` in the interpreter — the behavioral difference came purely from the authorized narrative context, not from any signal.

Finding during this TV: a Python `in` trap in the harness — `LINE in list_of_prompts` is element membership (never true for a substring), while `LINE in single_string` is substring match. The per-turn row was correct and the summary line was wrong; fixed with `any(LINE in user for user in prompts)` / `all(... not in ...)`. The samples file confirms the behavioral result either way.

Failures: None in the final run.

Known limitations:

- `claude_has_appeared` is the only flag rendered; later plot flags will extend `_narrative_context_for` per character permissions (still minimal context, docs/04 §17).
- The event's `presentation` directives (SHOW_CHARACTER claude) are still not consumed by the frontend — Claude "appearing" is currently a narrative-context fact, not a visual change (a later TV).
- The character's knowledge boundary is enforced only through the authorized context the builder renders; nothing prevents future builders from rendering more — the boundary is a builder discipline, not a runtime wall.

Evidence: `validation-results/TV-12/response-samples.md`, harness `run_live_validation.py`, passing automated suite (137).

Conclusion: PASS — before the event the character gets no Claude context and acts accordingly; after the event the same character legally receives that Claude has appeared and references it; Claude enters the runtime normally. Next validation: TV-13 (Important Memory).
