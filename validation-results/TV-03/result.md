## TV-03

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`, Python 3.12.9 venv) + static frontend (`frontend/`). Backend validated in-process with pytest/TestClient and over real HTTP with httpx.

Goal: Verify the minimal Frontend ↔ Backend communication chain with a fixed mock response and correct session association (docs/06 §9). No LLM is called at this stage.

Test cases:

1. `POST /api/chat` with a message and no session id creates a session and returns `session_id`, `character_id`, a mock `dialogue`, and `message_count`.
2. A second request reusing the same `session_id` stays in the same session and `message_count` increments.
3. An unknown/expired client `session_id` is not trusted: a fresh session with a newly generated id is returned.
4. Ten consecutive requests in one session all return 200 and `message_count` reaches 10.
5. A blank/whitespace-only message is rejected with 400.
6. Frontend: a submit sends the message to `/api/chat`, clears the input, shows the backend reply, and remembers `session_id` for the next request.
7. Frontend: while a request is in flight, the input and send button are disabled and the button shows `思考中…` (waiting state).
8. Frontend: a network failure restores the submitted text and shows a retry prompt; retrying then succeeds.
9. Frontend: ten consecutive submits all succeed without UI getting stuck.
10. Backend serves the static frontend (e.g. `http://localhost:8000/frontend/index.html`) so the round trip can be validated in a browser.

Observed result: All automated checks pass — `pytest`: 6 passed; `node frontend/tests/tv01-send.test.cjs`, `tv02-presentation.test.cjs`, `tv03-roundtrip.test.cjs`: all PASS. A live HTTP smoke test (httpx, proxy bypassed) confirmed 10/10 requests succeed, session association holds, the static page loads (200), blank messages return 400, and the mock dialogue bytes are valid UTF-8.

Failures: None in the backend/frontend code. Two environment quirks were identified and worked around during validation (see Known limitations).

Known limitations:

- Sessions are held in an in-memory store only; a backend restart loses them. Persistence is deferred to TV-14 (Session Restore).
- The response is a deterministic mock (`build_mock_reply`); it is a TV fixture, not production dialogue. TV-04 will replace it with a real DeepSeek call.
- The `tv01-send.test.cjs` was updated for the new async round-trip behavior introduced by TV-03 (TV-01's local mock reply is superseded).
- Environment quirks found while validating on this machine: (a) Git Bash passes non-ASCII command-line args to curl in the local codepage, mangling Chinese payloads — tests use httpx/pytest instead; (b) a system proxy intercepts localhost traffic for Python httpx clients — live HTTP tests use `httpx.Client(trust_env=False)`. Browsers bypass the proxy for localhost, so the in-browser flow is unaffected.

Evidence: `backend/tests/test_chat.py`, `frontend/tests/tv03-roundtrip.test.cjs`; run commands:

- `cd backend && .venv/Scripts/python -m pytest tests/ -q`
- `node frontend/tests/tv01-send.test.cjs && node frontend/tests/tv02-presentation.test.cjs && node frontend/tests/tv03-roundtrip.test.cjs`
- Serve: `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8000`, then open `http://localhost:8000/frontend/index.html`.

Conclusion: PASS — the Frontend ↔ Backend round trip works over real HTTP with correct session association, waiting state, and recoverable retry. Next validation: TV-04 (Single Character Generation).
