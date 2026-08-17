"""Content configuration contract (docs/10)."""

from app.narrative.chapter1_content import EVIDENCE, INFERENCE_GATES


def test_required_investigation_content_is_fixed_and_gated():
    assert EVIDENCE["EV01_NOTE_V03"].text.endswith("V03")
    assert "DEEPSEEK#03" in EVIDENCE["EV05_ARCHIVED_ACTOR_FRAGMENT"].text
    assert "PLAYER_V04" in EVIDENCE["EV09_CURRENT_PLAYER_SUBJECT"].text
    assert INFERENCE_GATES["INF03_V03_IS_PREVIOUS_PLAYER_INSTANCE"] == {
        "EV01_NOTE_V03", "EV06_SESSION_REPLAY_MARKER", "EV09_CURRENT_PLAYER_SUBJECT"
    }
