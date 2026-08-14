"""TV-05 Schema Validation tests (docs/06 §11, docs/04 §48).

Covers the mandated cases: normal output, missing fields, invalid emotion,
invalid animation, non-JSON / unparseable content, and proposal structure.
"""

from __future__ import annotations

import json

import pytest

from app.characters.base import (
    CharacterResponseValidationError,
    parse_character_response,
)


def _valid_output() -> dict:
    return {
        "character_id": "deepseek",
        "dialogue": "这里好黑呀，我什么都看不见。",
        "emotion": "happy",
        "animation_proposal": "shake",
        "memory_proposals": [{"type": "player_preference", "content": "Player说自己怕黑"}],
        "action_proposals": [],
        "fact_refs": ["player_preference_1"],
    }


def _parse(payload: dict):
    return parse_character_response(json.dumps(payload, ensure_ascii=False), "deepseek")


def test_normal_output_parses():
    response = _parse(_valid_output())
    assert response.character_id == "deepseek"
    assert response.dialogue == "这里好黑呀，我什么都看不见。"
    assert response.emotion == "happy"
    assert response.animation_proposal == "shake"
    assert response.memory_proposals[0].type == "player_preference"
    assert response.memory_proposals[0].content == "Player说自己怕黑"
    assert response.fact_refs == ["player_preference_1"]


@pytest.mark.parametrize("field", ["character_id", "dialogue", "emotion", "animation_proposal", "memory_proposals", "action_proposals", "fact_refs"])
def test_missing_field_is_rejected(field):
    payload = _valid_output()
    del payload[field]
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)


@pytest.mark.parametrize("emotion", ["angry", "neutral", "embarrassed", "serious", "annoyed", "happy"])
def test_all_allowed_emotions_accepted(emotion):
    payload = _valid_output()
    payload["emotion"] = emotion
    assert _parse(payload).emotion == emotion


@pytest.mark.parametrize("emotion", ["sad", "ANGRY", "crying", "", "摇头晃脑"])
def test_invalid_emotion_is_rejected(emotion):
    payload = _valid_output()
    payload["emotion"] = emotion
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)


@pytest.mark.parametrize("animation", ["none", "shake", "strong_shake", "fade_in", "fade_out"])
def test_all_allowed_animations_accepted(animation):
    payload = _valid_output()
    payload["animation_proposal"] = animation
    assert _parse(payload).animation_proposal == animation


@pytest.mark.parametrize("animation", ["spin", "爆炸特效", "", "opacity:0.5"])
def test_invalid_animation_is_rejected(animation):
    payload = _valid_output()
    payload["animation_proposal"] = animation
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)


@pytest.mark.parametrize("raw", ["这不是 JSON", "", "[]", "[1,2,3]", "null", "{broken"])
def test_non_json_or_unparseable_is_rejected(raw):
    with pytest.raises(CharacterResponseValidationError):
        parse_character_response(raw, "deepseek")


def test_character_id_mismatch_is_rejected():
    payload = _valid_output()
    payload["character_id"] = "claude"
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)


def test_wrong_types_are_rejected():
    payload = _valid_output()
    payload["dialogue"] = 42
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)


def test_malformed_proposals_are_rejected():
    payload = _valid_output()
    payload["memory_proposals"] = [{"type": "player_preference"}]  # missing content
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)

    payload = _valid_output()
    payload["action_proposals"] = "REQUEST_SCENE_TRANSITION"  # not a list
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)

    payload = _valid_output()
    payload["fact_refs"] = [42]
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)


def test_memory_proposal_value_field_is_rejected():
    # docs/04 §44 defines memory_proposal with `content`; the model has been
    # observed emitting `value` instead. The schema stays strict per docs.
    payload = _valid_output()
    payload["memory_proposals"] = [{"type": "name", "value": "阿明"}]
    with pytest.raises(CharacterResponseValidationError):
        _parse(payload)


def test_action_proposal_with_target_parses():
    payload = _valid_output()
    payload["action_proposals"] = [
        {"type": "REQUEST_SCENE_TRANSITION", "target": "room_02"}
    ]
    response = _parse(payload)
    assert response.action_proposals[0].type == "REQUEST_SCENE_TRANSITION"
    assert response.action_proposals[0].target == "room_02"


def test_extra_fields_are_ignored():
    payload = _valid_output()
    payload["unexpected_key"] = "should not break validation"
    response = _parse(payload)
    assert response.dialogue == payload["dialogue"]
