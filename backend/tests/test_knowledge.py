"""Knowledge ledger tests (who-knows-what)."""

from __future__ import annotations

from app.characters.base import CharacterResponse
from app.game.evidence import EV01_NOTE_V03
from app.game.knowledge import KnowledgeLedger, KnowledgeService
from app.game.orchestrator import GameOrchestrator
from app.game.state.session import SessionStore
from app.persistence.repository import JsonSessionRepository, PersistedSession


class _Runtime:
    character_id = "deepseek"

    def respond(self, request):
        return CharacterResponse(character_id=self.character_id, dialogue="……")

    def safe_fallback(self):
        return CharacterResponse(character_id=self.character_id, dialogue="……")


# ---- ledger unit ----


def test_record_and_knows():
    ledger = KnowledgeLedger()
    assert ledger.knows("deepseek", "F001") is False
    assert ledger.record("deepseek", "F001", "narrative_reveal", 3) is True
    assert ledger.knows("deepseek", "F001") is True


def test_known_facts():
    ledger = KnowledgeLedger()
    ledger.record("deepseek", "F001", "narrative_reveal", 1)
    ledger.record("deepseek", "F002", "presented_evidence", 2)
    assert ledger.known_facts("deepseek") == frozenset({"F001", "F002"})


def test_entries_track_source_and_turn():
    ledger = KnowledgeLedger()
    ledger.record("claude", "F004", "presented_evidence", 5)
    entries = ledger.entries("claude", "F004")
    assert len(entries) == 1
    assert entries[0].source == "presented_evidence"
    assert entries[0].turn == 5


def test_record_is_idempotent():
    ledger = KnowledgeLedger()
    assert ledger.record("deepseek", "F001", "presented_evidence", 2) is True
    assert ledger.record("deepseek", "F001", "presented_evidence", 2) is False
    assert len(ledger.entries("deepseek", "F001")) == 1


def test_snapshot_round_trip():
    ledger = KnowledgeLedger()
    ledger.record("deepseek", "F001", "presented_evidence", 2)
    ledger.record("claude", "F004", "narrative_reveal", 1)
    restored = KnowledgeLedger.from_snapshot(ledger.snapshot())
    assert restored.knows("deepseek", "F001")
    assert restored.knows("claude", "F004")
    assert restored.entries("deepseek", "F001")[0].turn == 2


def test_service_isolates_sessions():
    service = KnowledgeService()
    service.ledger_for("s1").record("deepseek", "F001", "narrative_reveal", 1)
    assert service.ledger_for("s2").knows("deepseek", "F001") is False


# ---- persistence ----


def test_persisted_session_round_trip(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    repo.save(
        PersistedSession(
            session_id="s1",
            knowledge={
                "deepseek": {"F001": [{"source": "presented_evidence", "turn": 2}]}
            },
        )
    )
    loaded = repo.load("s1")
    assert loaded.knowledge["deepseek"]["F001"][0]["source"] == "presented_evidence"


def test_legacy_snapshot_without_knowledge_loads_empty(tmp_path):
    repo = JsonSessionRepository(tmp_path)
    repo.save(PersistedSession(session_id="legacy"))
    loaded = repo.load("legacy")
    assert loaded.knowledge == {}


# ---- orchestrator wiring ----


def _orchestrator():
    return GameOrchestrator(SessionStore(), {"deepseek": _Runtime()})


def test_present_evidence_records_knowledge():
    orchestrator = _orchestrator()
    session_id = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session_id)
    state.revealed_facts.add("FIRST_IMPOSSIBLE_EVENT_RESOLVED")
    state.chapter1.acquired_evidence.add(EV01_NOTE_V03)
    state.chapter1.available_characters.add("deepseek")

    orchestrator.present_evidence(session_id, "deepseek", EV01_NOTE_V03)

    ledger = orchestrator._knowledge.ledger_for(session_id)
    assert ledger.knows("deepseek", EV01_NOTE_V03) is True
    # Not auto-shared to another character (docs/05 §51).
    assert ledger.knows("claude", EV01_NOTE_V03) is False


def test_presented_evidence_reads_from_ledger():
    """_presented_evidence_for 以知识账本为 who-knows-what 权威来源。"""
    orchestrator = _orchestrator()
    session_id = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session_id)
    state.revealed_facts.add("FIRST_IMPOSSIBLE_EVENT_RESOLVED")
    state.chapter1.acquired_evidence.add(EV01_NOTE_V03)
    state.chapter1.available_characters.add("deepseek")
    orchestrator.present_evidence(session_id, "deepseek", EV01_NOTE_V03)

    presented = orchestrator._presented_evidence_for(session_id, "deepseek")
    assert [item["evidence_id"] for item in presented] == [EV01_NOTE_V03]
    # 未被告知的角色仍拿不到该证据。
    assert orchestrator._presented_evidence_for(session_id, "claude") == []


def test_presented_evidence_falls_back_to_legacy_map():
    """账本为空（旧快照）时回退到叙事状态里的 presented_evidence 映射。"""
    orchestrator = _orchestrator()
    session_id = orchestrator._sessions.get_or_create(None).session_id
    state = orchestrator._state.state_for(session_id)
    state.chapter1.acquired_evidence.add(EV01_NOTE_V03)
    state.chapter1.presented_evidence.setdefault(EV01_NOTE_V03, set()).add("deepseek")

    presented = orchestrator._presented_evidence_for(session_id, "deepseek")
    assert [item["evidence_id"] for item in presented] == [EV01_NOTE_V03]
