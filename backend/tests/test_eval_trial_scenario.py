"""P0-2 eval scenario: prompt versions, fixtures, responder message building."""

from __future__ import annotations

import pytest

from app.eval.trial.scenario import (
    AGREEMENT_TEXT,
    EVIDENCE_FIXTURES,
    FORBIDDEN_VISIBLE_TEXT,
    PROMPT_VERSIONS,
    ChatReplyRequest,
    TrialChatResponder,
    validate_scenario,
)
from app.trial.content import EVIDENCE_IDS


def test_prompt_versions_differ_and_v2_adds_rules():
    validate_scenario()
    assert PROMPT_VERSIONS["v1"] != PROMPT_VERSIONS["v2"]
    for clause in ("无证据不确认", "否定≠承认", "不提前泄露", "接住细节", "执行约定", "不编造"):
        assert clause in PROMPT_VERSIONS["v2"]
        assert clause not in PROMPT_VERSIONS["v1"]


def test_scenario_never_leaks_forbidden_visible_text():
    for version_id, prompt in PROMPT_VERSIONS.items():
        assert FORBIDDEN_VISIBLE_TEXT not in prompt


def test_evidence_fixtures_match_game_registry():
    assert {item["evidence_id"] for item in EVIDENCE_FIXTURES} == set(EVIDENCE_IDS)
    assert all(4 <= len(item["title"]) <= 5 for item in EVIDENCE_FIXTURES)


def test_agreement_fixture_is_the_doc_example():
    assert AGREEMENT_TEXT == "不记得时先承认，不用读来的文字假装回忆。"


def test_responder_builds_user_message_with_state():
    responder = TrialChatResponder(object(), "v1")
    message = responder.build_user_message(
        ChatReplyRequest(
            player_message="那晚你去了哪里？",
            evidence_ids=("TRIAL_EV_MEMORY_GAP",),
            agreement_active=True,
            recent_conversation=(("player", "在吗"), ("DeepSeek", "在……")),
        )
    )
    assert "记忆断层" in message
    assert "已达成约定" in message and AGREEMENT_TEXT in message
    assert "在吗" in message and "在……" in message
    assert message.endswith("Player 现在说：那晚你去了哪里？")


def test_responder_rejects_unknown_version():
    with pytest.raises(ValueError, match="unknown prompt version"):
        TrialChatResponder(object(), "v9")
