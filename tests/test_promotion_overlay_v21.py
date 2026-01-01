from __future__ import annotations

from pathlib import Path

import pytest

from aal_core.ers.effects_store import EffectStore, record_effect
from aal_core.governance.promotion_policy import PromotionPolicy
from aal_core.runtime.promotion_overlay import PromotionOverlay
from abx_runes.tuning.portfolio.optimizer import build_portfolio


def _write_promotions(tmp_path: Path, items: list[dict]) -> None:
    p = PromotionPolicy(items=items)
    path = tmp_path / ".aal" / "promotions.json"
    p.save(path)


def test_overlay_baseline_scoped_and_deterministic_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_promotions(
        tmp_path,
        items=[
            {
                "module_id": "m",
                "knob": "k",
                "value": 2,
                "baseline_signature": {"b": "2", "a": "1"},
            }
        ],
    )
    monkeypatch.chdir(tmp_path)
    overlay = PromotionOverlay.load(bias_weight=0.2)

    # keying is deterministic regardless of signature dict insertion order
    assert overlay.get_promoted_value(module_id="m", knob="k", baseline_signature={"a": "1", "b": "2"}) == 2
    assert overlay.get_promoted_value(module_id="m", knob="k", baseline_signature={"a": "2", "b": "2"}) is None


def test_overlay_ignores_revoked_items(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_promotions(
        tmp_path,
        items=[
            {
                "module_id": "m",
                "knob": "k",
                "value": 1,
                "baseline_signature": {"a": "1"},
                "revoked_at_idx": 10,
            },
            {
                "module_id": "m",
                "knob": "k",
                "value": 2,
                "baseline_signature": {"a": "1"},
                "revoked_at_idx": None,
            },
        ],
    )
    monkeypatch.chdir(tmp_path)
    overlay = PromotionOverlay.load(bias_weight=0.2)
    assert overlay.get_promoted_value(module_id="m", knob="k", baseline_signature={"a": "1"}) == 2


def test_optimizer_bias_prefers_promoted_candidate_when_baseline_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_promotions(
        tmp_path,
        items=[
            {
                "module_id": "mod.alpha",
                "knob": "mode",
                "value": "b",
                "baseline_signature": {"a": "1"},
            }
        ],
    )
    monkeypatch.chdir(tmp_path)

    store = EffectStore()
    baseline = {"a": "1"}

    # Equal deltas: without bias, tie-break would pick "a" (str order).
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="a",
        baseline_signature=baseline,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 100.0},
    )
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="b",
        baseline_signature=baseline,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 100.0},
    )

    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "mod.alpha",
        "knobs": [{"name": "mode", "kind": "enum", "enum_values": ["a", "b"], "default": "a", "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.mode"}],
    }

    applied, notes = build_portfolio(effects_store=store, tuning_envelope=env, baseline_signature=baseline)
    assert applied["mode"] == "b"
    assert notes["promotion_knobs_selected"] == 1


def test_optimizer_bias_does_not_apply_when_baseline_mismatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_promotions(
        tmp_path,
        items=[
            {
                "module_id": "mod.alpha",
                "knob": "mode",
                "value": "b",
                "baseline_signature": {"a": "1"},
            }
        ],
    )
    monkeypatch.chdir(tmp_path)

    store = EffectStore()
    baseline = {"a": "2"}  # does not match promotion

    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="a",
        baseline_signature=baseline,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 100.0},
    )
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="b",
        baseline_signature=baseline,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 100.0},
    )

    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "mod.alpha",
        "knobs": [{"name": "mode", "kind": "enum", "enum_values": ["a", "b"], "default": "a", "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.mode"}],
    }

    applied, notes = build_portfolio(effects_store=store, tuning_envelope=env, baseline_signature=baseline)
    assert applied["mode"] == "a"
    assert notes["promotion_knobs_selected"] == 0


def test_promoted_defaults_fill_missing_assignments_when_baseline_matches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_promotions(
        tmp_path,
        items=[
            {
                "module_id": "mod.alpha",
                "knob": "mode",
                "value": "fast",
                "baseline_signature": {"bucket": "x"},
            }
        ],
    )
    monkeypatch.chdir(tmp_path)

    store = EffectStore()  # no stats recorded
    baseline = {"bucket": "x"}
    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "mod.alpha",
        "knobs": [{"name": "mode", "kind": "enum", "enum_values": ["fast", "safe"], "default": "safe", "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.mode"}],
    }

    applied, notes = build_portfolio(effects_store=store, tuning_envelope=env, baseline_signature=baseline)
    assert applied["mode"] == "fast"
    assert notes["promoted_defaults_applied"] == ["mode"]
    assert "mode" not in notes["excluded"]

