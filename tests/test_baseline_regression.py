"""Guards the frozen Phase 1-5 preliminary baseline (seed 42, synthetic)."""
import json, inspect
from pathlib import Path
import pytest
from immunomesh.config import load_config
from immunomesh.pipeline import run_detection_pipeline
from immunomesh.simulation.traffic import generate_traffic
from immunomesh.schema import T_START

FROZEN = json.loads((Path(__file__).parent / "data" / "baseline_phase5_seed42.json").read_text())


def assert_frozen_value(actual, expected):
    """Compare deterministic structure exactly and computed floats tolerantly."""
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key, value in expected.items():
            assert_frozen_value(actual[key], value)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=1e-12, abs=1e-12)
    else:
        assert actual == expected


@pytest.mark.parametrize("intensity", ["high", "low"])
def test_frozen_baseline_unchanged(intensity):
    cfg = load_config(overrides={"simulation": {"intensity": intensity}})
    m = run_detection_pipeline(cfg)["metrics"]
    for k in ("detection", "per_attack_recall", "threshold", "train_flows", "eval_flows"):
        assert_frozen_value(m[k], FROZEN[intensity][k])

def test_t_start_matches_simulator():
    assert inspect.signature(generate_traffic).parameters["t_start"].default == T_START
