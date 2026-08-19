"""Script Event Schema fail-closed validation tests (docs/12 §36-37, §40.1).

A Script Sequence that references anything the runtime cannot resolve — unknown
event type, missing required field, nonexistent dialogue node / condition /
animation / transition target, or a chatgpt unlock — must fail at load time with
script_id + step index (docs/12 §37), never silently half-load.
"""

from __future__ import annotations

import pytest

from app.script.chapter1 import build_script_registry
from app.script.conditions import CONDITION_REGISTRY, evaluate_condition
from app.script.registry import ScriptRegistry
from app.script.schema import ScriptLoadError, load_sequences


def test_authorized_chapter_one_registry_builds():
    registry = build_script_registry()
    assert len(registry.get("CH01_INCIDENT_0317").steps) == 10
    assert len(registry.triggers()) == 4
    assert "CHATGPT_ARRIVAL_LINE" in registry._dialogue_nodes


def test_unknown_event_type_fails_closed_with_script_and_step():
    with pytest.raises(ScriptLoadError, match=r"\[script:DUMMY step:1\] unknown event type"):
        load_sequences([{
            "script_id": "DUMMY",
            "steps": [
                {"type": "narrative_gate", "condition": "CT01_CONFIRMED"},
                {"type": "teleport", "to": "anywhere"},
            ],
        }])


def test_missing_required_field_fails_closed():
    with pytest.raises(ScriptLoadError, match=r"\[script:DUMMY step:0\] missing required field"):
        load_sequences([{
            "script_id": "DUMMY",
            "steps": [{"type": "character_show", "emotion": "neutral"}],
        }])


def test_duplicate_script_id_fails_closed():
    with pytest.raises(ScriptLoadError, match="duplicate script_id"):
        load_sequences([
            {"script_id": "DUPLICATE", "steps": []},
            {"script_id": "DUPLICATE", "steps": []},
        ])


def test_unknown_character_reference_fails_closed():
    with pytest.raises(ScriptLoadError, match="unknown character 'godzilla'"):
        ScriptRegistry(
            load_sequences([{
                "script_id": "BAD_CHAR",
                "steps": [{"type": "character_show", "character": "godzilla"}],
            }]),
            dialogue_nodes={},
            triggers=[],
        )


def test_unknown_dialogue_node_reference_fails_closed():
    with pytest.raises(ScriptLoadError, match="unknown node 'NOPE'"):
        ScriptRegistry(
            load_sequences([{
                "script_id": "BAD_NODE",
                "steps": [{"type": "script_dialogue", "character": "claude", "node": "NOPE"}],
            }]),
            dialogue_nodes={},
            triggers=[],
        )


def test_unknown_animation_reference_fails_closed():
    with pytest.raises(ScriptLoadError, match="unknown animation 'warp'"):
        ScriptRegistry(
            load_sequences([{
                "script_id": "BAD_ANIM",
                "steps": [
                    {"type": "character_show", "character": "claude", "animation": "warp"}
                ],
            }]),
            dialogue_nodes={},
            triggers=[],
        )


def test_unknown_gate_condition_fails_closed():
    with pytest.raises(ScriptLoadError, match="unknown condition 'NEVER'"):
        ScriptRegistry(
            load_sequences([{
                "script_id": "BAD_GATE",
                "steps": [{"type": "narrative_gate", "condition": "NEVER"}],
            }]),
            dialogue_nodes={},
            triggers=[],
        )


def test_unknown_phase_transition_target_fails_closed():
    with pytest.raises(ScriptLoadError, match="unknown to 'WARP_ZONE'"):
        ScriptRegistry(
            load_sequences([{
                "script_id": "BAD_PHASE",
                "steps": [{"type": "phase_transition", "to": "WARP_ZONE"}],
            }]),
            dialogue_nodes={},
            triggers=[],
        )


def test_chatgpt_unlock_is_forbidden():
    """docs/12 §33: chatgpt availability belongs to the deduction runtime alone;
    a Script Content that tries to unlock him fails at load time."""
    with pytest.raises(ScriptLoadError, match="unknown target 'chatgpt'"):
        ScriptRegistry(
            load_sequences([{
                "script_id": "BAD_UNLOCK",
                "steps": [{"type": "unlock", "target": "chatgpt"}],
            }]),
            dialogue_nodes={},
            triggers=[],
        )


def test_unknown_trigger_condition_fails_closed():
    with pytest.raises(ScriptLoadError, match="unknown trigger condition"):
        ScriptRegistry(
            load_sequences([]),
            dialogue_nodes={},
            triggers=[("NEVER", "MISSING")],
        )


def test_unknown_script_in_trigger_fails_closed():
    with pytest.raises(ScriptLoadError, match="references unknown script"):
        ScriptRegistry(
            load_sequences([]),
            dialogue_nodes={},
            triggers=[("CT01_CONFIRMED", "MISSING")],
        )


def test_evaluate_condition_unknown_id_fails_closed():
    with pytest.raises(ScriptLoadError, match="unknown condition"):
        evaluate_condition("NOPE", None)  # type: ignore[arg-type]


def test_condition_registry_has_the_expected_predicates():
    assert set(CONDITION_REGISTRY) == {
        "INCIDENT_0317_READY",
        "GPT_ARRIVAL_READY",
        "DOUBAO_ARRIVAL_READY",
        "INF03_ACCEPTED",
        "CT01_CONFIRMED",
        "INF01_COMPLETE",
    }
