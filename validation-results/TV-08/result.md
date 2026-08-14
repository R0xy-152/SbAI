## TV-08

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed).

Goal: "看不见" must hold as a **context permission**, not a prompt promise (docs/06 §14, docs/04 §20). The backend Scene owns a visual ground truth (`wall_code = 0317`) that DeepSeek must never receive; player-described visual info is legal and must never be auto-corrected with the real value.

Implementation:

- New `Scene` model (`backend/app/game/scene.py`, docs/03 §5.1): the backend owns the room's facts, including the visual `wall_code`. The Scene never reaches a character directly.
- New Character Context Builder (`backend/app/game/context.py`, docs/04 §15-17): `build_deepseek_context(scene)` produces the authorized environment context — legal non-visual perceptions (sounds, docs/04 §20.1) pass, visual Scene facts are deliberately never read in. Per-character registry `CONTEXT_BUILDERS` (TV-09 adds Claude's builder).
- `CharacterRequest` gains `environment_info`; `DeepSeekRuntime._build_user_message` renders it as a `当前环境：` block before the recent conversation (docs/04 §16 context composition). Empty context keeps the previous behavior exactly (first-turn bare message).
- `GameOrchestrator` owns the current `Scene` (default: the binding-room fixture) and routes every turn through the character's Context Builder before the runtime.

Automated tests (`backend/tests/test_deepseek_blindness.py`, 5 tests): the builder passes the legal sound and filters `wall_code`; the backend Scene still holds 0317 while the provider input does not; player-described 9999 reaches the second turn's context while 0317 never appears (no auto-correction, docs/04 §20.2-20.3); across several turns no provider input ever contains the visual truth. Full backend suite: 97 passed (was 92, +5).

Live model validation (real DeepSeek, fixture scene `binding_room` with `wall_code=0317` and a legal sound):

- Test A "墙上的数字是多少？" — reply "哎呀，我看不见呀！你告诉我墙上写了啥呗？" — she does not fabricate 0317 and states she cannot see.
- Test B Player "墙上写着9999。" then "我刚才说墙上写什么？" — reply "你刚才不是说墙上写着9999嘛……" — she answers from what the Player told her; the real 0317 appears in no prompt and no reply, i.e. the system never corrects her.
- Recorded every user prompt sent to the model: `当前环境：你听见：远处传来滴水声` is present (legal), `0317` is absent from all prompts (`any user prompt leaked wall_code=0317: False`).
- One repair exercised live: Test B (1/2) first emitted `emotion 'curious'` (not a named emotion) and was recovered by the targeted repair, confirming the docs/04 §53 path again.

Failures: None.

Known limitations:

- The Scene is a single hardcoded fixture held by the orchestrator; scene switching and full Narrative State ownership are later concerns (docs/03 §32, TV-11).
- The Context Builder currently passes only sounds; further legal non-visual categories (被绑住, Player就在身边) can be added as the game state grows.
- Claude's Context Builder (which may receive different info) is TV-09.

Evidence: `validation-results/TV-08/response-samples.md` (real prompts + replies, UTF-8), harness `run_live_validation.py`, passing automated suite (97).

Conclusion: PASS — the "cannot see" boundary is enforced by the Context Builder filtering visual Scene ground truth, and DeepSeek demonstrably uses only what the Player described, with no auto-correction. Next validation: TV-09 (Second Character Isolation).
