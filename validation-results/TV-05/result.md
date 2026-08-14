## TV-05

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via the `DEEPSEEK_API_KEY` environment variable (never committed). Structured output requested with `response_format={"type": "json_object"}`.

Goal: The generative character must reliably form a Structured Character Response (docs/06 §11): `character_id`, `dialogue`, `emotion`, `animation_proposal`, `memory_proposals`, `action_proposals`, `fact_refs` (docs/04 §40). Valid output is accepted; invalid output is rejected / repaired / fallen back — never presented raw (docs/04 §48, §53-54).

Implementation:

- `CharacterResponse` is now the full structured type with allow-lists for Named Emotion (`neutral|happy|annoyed|angry|embarrassed|serious`) and Named Animation (`none|shake|strong_shake|fade_in|fade_out`) (docs/04 §42-43).
- `parse_character_response` performs Schema Validation: required fields, types, character_id match, allowed emotion/animation, proposal structure (docs/04 §48).
- `DeepSeekRuntime` asks the model for strict JSON, parses it, and on a validation failure repairs once (docs/04 §53), then falls back to a story-neutral safe line on the second failure (docs/04 §54).
- Provider failures (timeout / HTTP / empty) propagate as a recoverable 503 at the API boundary instead of a fabricated reply (docs/04 §55).

Automated tests: `backend/tests/test_character_validation.py` (mandated cases — normal output, missing field per each of the 7 fields, invalid emotion, invalid animation, non-JSON/unparseable, wrong types, malformed proposals), `test_character_deepseek.py` (repair-once, fallback, character_id mismatch, provider failure), `test_chat.py` (API returns 503 on provider failure; invalid model output never reaches the player). Full suite: 79 passed.

Live model validation (real DeepSeek, 10 natural-language inputs):

- first-try valid: 9 / 10
- repaired after retry: 1 / 10
- safe fallback: 0 / 10
- provider errors: 0
- structural failures: 0 (every accepted response had allowed emotion/animation, correct character_id, non-empty dialogue)
- Persona held throughout; input 4 ("我叫阿明，你呢？") correctly proposed a `player_name` memory instead of fabricating it, showing the structured fields carry real signal.
- Repro: `DEEPSEEK_API_KEY=... .venv/Scripts/python validation-results/TV-05/run_live_validation.py` (writes `response-samples.md`).

Failures: None.

Known limitations:

- `memory_proposals` / `action_proposals` are validated and carried but not yet consumed by any Memory or Narrative system (their consumption is later TVs).
- The frontend does not yet receive `emotion` / `animation_proposal`; the structured fields flow to the player only as dialogue for now. Wiring them into the presentation layer is a later TV.
- Repair/fallback decisions are deterministic; no exponential backoff or token-budget limits yet (fine at this stage).

Evidence: `validation-results/TV-05/response-samples.md` (10 full structured replies, UTF-8), the run harness `run_live_validation.py`, and the passing automated suite above.

Conclusion: PASS — the character link now stably produces validated structured responses end to end, and invalid output cannot leak to the player. Next validation: TV-06 (Validate Before Present) — prove that a bad model output never enters official History / Game State / Memory.
