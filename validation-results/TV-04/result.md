## TV-04

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`, Python 3.12.9 venv), live DeepSeek API (model `deepseek-chat`), key supplied via the `DEEPSEEK_API_KEY` environment variable (never committed to the repo).

Goal: Verify the first generative character link — Player → Backend → Character Runtime → Provider → Model → Response (docs/06 §10). No other systems (narrative, memory, Claude) are required yet.

Test cases:

1. 10 different natural-language inputs through the live DeepSeek API via `DeepSeekRuntime.respond`.
2. All replies must be usable (non-empty text).
3. No persistent empty returns.
4. Provider failures must be identifiable (ProviderError), not silent.
5. A model call failure must not leave the backend unrecoverable.

Observed result:

- 10/10 requests returned usable replies; 0 empty, 0 provider errors, 0 crashes. Median latency ~1.0s per turn.
- Persona held across all 10 varied inputs: DeepSeek stayed cute, repeatedly stated she cannot see and asked the player to describe the environment, referenced the Token-snacking trait (input 3), showed laziness (inputs 1-2), and did not fabricate any visual information she was not told.
- Provider and validation paths are covered by automated tests: `backend/tests/test_provider_deepseek.py` (6 tests, using `httpx.MockTransport`, no network/key) and `backend/tests/test_character_deepseek.py` (12 tests with the deterministic mock provider).

Failures: None.

Known limitations:

- Only the current player message is sent; multi-turn recent context arrives with TV-07.
- The reply is free-form text; structured Character Response output is TV-05.
- One mild persona wobble (input 10 responded as if the player had asked repeatedly) — non-blocking.
- Outbound HTTPS to api.deepseek.com works through the machine's system proxy; localhost still requires `trust_env=False` for Python httpx clients (see TV-03 record).

Evidence: live run output; `validation-results/TV-04/response-samples.md` (10 full replies, UTF-8). Reproduce: `cd backend && DEEPSEEK_API_KEY=... .venv/Scripts/python -m uvicorn app.main:app --port 8000`, then POST to `/api/chat`; or run the character-runtime tests.

Conclusion: PASS — the single-character generation chain works end-to-end with a real model and the DeepSeek persona is stable. Next validation: TV-05 (Structured Character Response).
