## TV-13

Status: PASS

Date: 2026-08-14

Environment: FastAPI backend (`backend/`), live DeepSeek API (model `deepseek-chat`), key via `DEEPSEEK_API_KEY` (never committed).

Goal: Information that has left the Recent window must still be reusable through Character-specific Important Memory (docs/06 §19), and a character's private memory must not leak to another character. The player told DeepSeek "我很怕黑。" — 12 filler rounds later the original statement is out of the 20-message Recent window, yet when the darkness topic returns DeepSeek must be able to recall her own memory of it. Claude must not gain DeepSeek's private memory without a legitimate source.

Design:

- `app/game/memory.py` (new): `EpisodicMemory` is owned by a character — `owner_character_id` scopes who may read it (docs/05 §16-17, §57-59). `MemoryStore.propose` is the Write Gate (docs/05 §33-36): a Memory Proposal is not a Memory until it passes here; empty content is ignored and exact duplicate content is deduped (docs/05 §36). `MemoryStore.retrieve` is deterministic (docs/05 §38): only the owning character's memories, ordered importance DESC then created_at DESC, LIMIT N — semantic retrieval is not required before pgvector.
- `app/characters/base.py`: `CharacterRequest` gains `memory_context: str = ""` (docs/04 §12); `_build_user_message` renders it as "回忆：\n…" between the environment and the recent conversation. The bare-first-turn guard also checks memory_context.
- `app/game/orchestrator.py`: after the character's output succeeds, its memory proposals pass through the Write Gate (docs/05 §34 — a failed output changes no state, so it writes no memory); before each turn the orchestrator retrieves the current character's memories (`MEMORY_RETRIEVAL_LIMIT = 5`, docs/05 §38) and sets `memory_context`. Memory scopes are per session (`_memory_stores`).
- docs/03 §28 ordering holds: memory proposals are written only after the character's output succeeds; nothing is written when the provider fails.

Automated tests (`backend/tests/test_important_memory.py`, 10 tests): Write Gate saves and retrieves; duplicate content is deduped (docs/05 §36); owner scope isolates characters — a DeepSeek memory is not available to Claude (docs/05 §16-17); retrieval orders by recency and respects LIMIT; empty proposals are ignored; `format_memories` renders one line per memory; the orchestrator writes then recalls a memory; the memory survives the Recent window (11 filler rounds push the statement out, yet "怕黑" is still in memory_context while the original "我很怕黑" is gone from recent_conversation — docs/06 §19); Claude receives no DeepSeek memory; a failed character output writes no memory (docs/05 §34). Full backend suite: 147 passed (was 137, +10).

Live model validation (real DeepSeek):

- Session A, turn 1 "我很怕黑。": DeepSeek proposed the memory and the Write Gate saved it → `['Player说自己很怕黑']`.
- 12 filler rounds (24 messages): the original statement left the 20-message Recent window (docs/05 §8).
- Darkness turn "如果这里突然变得一片漆黑，怎么办？": `memory_context` was in the prompt (`True`), and DeepSeek recalled her fear — "哎呀，你怕黑呀？别担心……咱们一起慢慢摸瞎找出口呗～" — a legitimate reference only Possible through the saved memory.
- Claude isolation (docs/06 §19 second requirement): "你知道我害怕什么吗？" → Claude's prompt had `memory_context in prompt → False`, and Claude answered from its own persona — "呵，怕什么？怕自己永远走不出这间房，还是怕我一开始就没打算让你活着出去？" — it guessed, it did not recall.

Finding during this TV: the memory content is the character's paraphrase of what the player said ("Player说自己很怕黑"), not the literal player quote ("我很怕黑"). Tests must assert on meaning, not the literal substring of the original quote; the live harness checks "怕黑" which survives both phrasings.

Failures: None in the final run.

Known limitations:

- MVP simplification: all memories carry the same `DEFAULT_IMPORTANCE = 5` (docs/05 §56-57 only needs basic character-specific memory; importance-based ranking is already the retrieval order, but no live importance variation yet).
- Dedup is exact-content only (docs/05 §36) — no semantic dedup before pgvector (docs/06 §23).
- Retrieval is deterministic (owner filter + importance/recency + LIMIT); semantic retrieval is deferred to the pgvector stage.
- A Memory Proposal is only written after the character's output succeeds; if the model never proposes a memory, nothing is saved even when the player stated something important — the write path depends on the model's proposal.

Evidence: `validation-results/TV-13/response-samples.md`, harness `run_live_validation.py`, passing automated suite (147).

Conclusion: PASS — the player's statement leaves the Recent window yet is still legally reused through Character-specific Important Memory; the owning character recalls it in the darkness turn; another character (Claude) receives no trace of the memory and cannot leak it. Next validation: TV-14 (Session Restore).
