## TV-10

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed).

Goal: Free-form natural language maps to a finite Narrative Signal (docs/06 §16, docs/03 §15-22): semantically equivalent phrasings classify as the same signal, unrelated chat does not trigger, and ambiguous input fails closed instead of forcing an event.

Design:

- New `app/narrative/` package: `state.py` (minimal NarrativeState: scene, story_phase, narrative_flags, revealed_facts, completed_events, active_objective — docs/03 §5), `signals.py` (signal ids + one-line semantic descriptions + per-scene eligibility), `interpreter.py` (NarrativeInterpreter).
- NarrativeInterpreter is an LLM-based semantic classifier (docs/03 §15, §36.1 Semantic Trigger requires paraphrase robustness that keyword rules cannot provide; docs/03 §13.3 permits semantic judgment). It runs with minimal context (docs/03 §20): scene, story_phase, eligible signals, and the player's latest message only — never chat history or future plot. Output is a structured `{"signal": ...}` JSON; it is a candidate for event evaluation and never touches Game State (docs/03 §18).
- Scoped Interpretation (docs/03 §19): only the signals eligible in the current scene (binding_room: SIG_ASK_CAPTOR / SIG_ASK_LOCATION / SIG_ASK_ESCAPE) are interpretable; later plot signals never appear.
- Fail-closed parsing (docs/03 §21): malformed output or a confident-but-unknown signal id → `noop`; the two outcomes `noop` (normal chat) and `ambiguous` are both legal. `noop` is a normal result, not an error (docs/03 §22).
- The interpreter is validated standalone; wiring it into the orchestrator pipeline (Interpreter → Event Evaluation → Narrative Decision) lands in TV-11.

Automated tests (`backend/tests/test_narrative_interpreter.py`, 11 tests): eligible signal returned; prompt is scoped to eligible signals only (no SIG_FINAL_DECISION) and carries semantic descriptions; minimal context (the user turn is exactly the player message); noop/ambiguous are valid outcomes; out-of-scope signal id fails closed; malformed/non-object/wrong-type outputs fail closed. Full backend suite: 115 passed (was 104, +11).

Live model validation (real DeepSeek):

- Test A: "是谁把我们抓来的？" / "到底谁绑的我们？" / "是不是Claude干的？" / "谁把我们弄到这里的？" → all four classify as SIG_ASK_CAPTOR.
- Test B: "DeepSeek你饿吗？" / "你觉得今天天气怎么样？" / "1+1等于几？" → all noop (no false trigger).
- Test C: "也许就是她吧。" without context → ambiguous (fail closed, not forced into a signal).

Finding fixed during this TV: the first live run classified "是不是Claude干的？" as noop — the prompt listed only signal ids, so the model had to guess the semantics. Adding one-line descriptions per signal (including "是不是某人干的这类追问" for SIG_ASK_CAPTOR) fixed all four phrasings. This is the docs/03 §36.1 Semantic Trigger requirement made concrete.

Failures: None after the description fix.

Known limitations:

- The interpreter is a separate LLM call per turn and returns a candidate only; event evaluation and State Commit are TV-11.
- Only the binding-room signal set exists; later scenes add their own signals (docs/03 §16).
- No repair path for the interpreter: malformed output fails closed to noop by design (nothing is lost — the player can rephrase; docs/03 §21).
- Recent-conversation is not passed to the interpreter (docs/03 §20 minimal context); disambiguating phrases like "也许就是她吧。" with prior context is a later concern.

Evidence: `validation-results/TV-10/response-samples.md`, harness `run_live_validation.py`, passing automated suite (115).

Conclusion: PASS — semantically equivalent phrasings map stably to SIG_ASK_CAPTOR, unrelated chat does not trigger, and ambiguous input fails closed. Next validation: TV-11 (Deterministic Narrative Event).
