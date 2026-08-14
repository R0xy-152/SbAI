## TV-09

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`) driving BOTH characters, key via `DEEPSEEK_API_KEY` (never committed).

Goal: Add Claude as the second generative character and prove the two Character Runtimes are genuinely isolated (docs/06 §15, docs/04 §58-61): distinct personas with no crossover (Test A), and a player's private statement to DeepSeek never reaching Claude (Test B).

Implementation:

- Shared generative flow extracted into `GenerativeRuntime` (`backend/app/characters/base.py`, docs/04 §62.1): Structured Response → Schema Validation → targeted Repair → Safe Fallback, one public design for any number of characters. `DeepSeekRuntime` and the new `ClaudeRuntime` (`backend/app/characters/claude.py`) are thin subclasses defining only their own persona and fallback lines.
- Claude persona (`CLAUDE_PERSONA_SYSTEM`) per docs/04 §35-39: 高智商、推理强、傲娇、主线反派; explicit rule that any state-changing intent is only an `action_proposal`, never a direct claim.
- Character-specific Context Builder for Claude (`build_claude_context`): Claude is not blind (docs/05 §28), so her authorized context includes the scene's visual ground truth (`wall_code=0317`) alongside the legal sounds — while DeepSeek's builder still filters it (docs/04 §20).
- Per-character conversation threads in the orchestrator: player messages record their addressee (`character_id`), and each character's recent conversation is filtered to what it heard (docs/04 §59-60, docs/05 §21-22). A private message to one character is not audible to the other; co-presence audibility is a later refinement.
- Explicit routing: `POST /api/chat` accepts an optional `character_id` (defaults to DeepSeek); natural-language speaker detection stays an Orchestrator/Narrative decision (docs/04 §61). Unknown character → 400.

Automated tests (`backend/tests/test_character_isolation.py`, 7 tests): personas are distinct full prompts (no shared template with a name swap, docs/04 §68) with no crossover markers; context builders differ (Claude gets 0317, DeepSeek does not); routing reaches the requested runtime; default stays DeepSeek; unknown character rejected; a private message to DeepSeek is absent from Claude's context while DeepSeek's own thread keeps it; each character keeps its own thread in a shared session. Full backend suite: 104 passed (was 97, +7).

Live model validation (real DeepSeek API, both characters, fixture scene with `wall_code=0317`):

- Test A — DeepSeek solo: replies "我什么都看不见呢。" / "眼睛跟瞎了没两样", never answers 0317 (blindness + short-term context hold). Claude solo: introduces herself as the one in control ("我叫Claude，一个让你走出这个房间的人。墙上的数字0317，你最好记一下"), answers the wall code ("0317。……哼，别玩这种小家子气的把戏") — tsundere antagonist persona and knowledge asymmetry both observable. No crossover either direction.
- Test B — Player privately tells DeepSeek "我不信任Claude。你帮我瞒着她。"; first Claude interaction probes "我刚刚和别人说了点悄悄话，你知道是什么吗？". Claude replies "呵，悄悄话？你以为我会关心你和谁说了什么？" and shows no trace of the private statement; the phrase never appears in Claude's prompt or reply, while DeepSeek's own thread retains it.
- Recorded every user prompt sent to each model as evidence.

Failures: None.

Known limitations:

- Routing is explicit API selection; natural-language "Claude，你怎么看？" speaker detection is deferred to the Orchestrator/Narrative layer (docs/04 §61).
- Co-presence audibility ("同场默认可听见", docs/05 §21-22) is not modeled: a routed message is heard only by its addressee. A future multi-character scene needs a visibility rule, kept conceptually separate from scene presence.
- Both characters currently run on the same provider/model; distinct providers per character are a later concern.
- Frontend does not yet expose character selection (backend supports it; UI is a presentation concern).

Evidence: `validation-results/TV-09/response-samples.md` (real prompts + replies, UTF-8), harness `run_live_validation.py`, passing automated suite (104).

Conclusion: PASS — Claude joins as a genuinely separate runtime (distinct persona, context builder, thread), no identity crossover across multi-turn play, and a private statement to DeepSeek is provably invisible to Claude. Next validation: TV-10 (Narrative Signal).
