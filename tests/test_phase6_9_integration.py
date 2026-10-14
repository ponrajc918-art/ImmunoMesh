"""End-to-end integration checks for evidence (P6), trust (P7), consensus (P8), response (P9)."""
import numpy as np, pandas as pd, pytest
from immunomesh.config import load_config
from immunomesh.experiments.scenario import prepare_seed, prepare_scenario, run_variant, ABLATION

@pytest.fixture(scope="module")
def sc_sd():
    cfg = load_config(overrides={"simulation": {"train_duration_s": 400, "eval_duration_s": 400}})
    sc = prepare_seed(cfg)
    return sc, prepare_scenario(sc)

def test_evidence_only_corroborated_flows_marked(sc_sd):
    sc, sd = sc_sd
    assert len(sd.evidence) == int(sd.ev["pred"].is_anomaly.sum())
    assert sd.evidence.evidence_strength.between(0, 1).all()

def test_mesh_deterministic(sc_sd):
    sc, sd = sc_sd
    r1 = run_variant(sc, sd, ABLATION["A4_full_system"])
    r2 = run_variant(sc, sd, ABLATION["A4_full_system"])
    pd.testing.assert_frame_equal(r1["epochs"], r2["epochs"])

def test_ablation_switches_change_behaviour(sc_sd):
    sc, sd = sc_sd
    a0 = run_variant(sc, sd, ABLATION["A0_anomaly_only"])
    a4 = run_variant(sc, sd, ABLATION["A4_full_system"])
    assert np.isnan(a0["epochs"]["trust"]).all()
    assert not np.isnan(a4["epochs"]["trust"]).all()
    assert a0["metrics"].get("quarantine_events") is None
    assert "quarantine_events" in a4["metrics"]

def test_consensus_requires_trust_raises():
    from dataclasses import replace
    cfg = load_config()
    with pytest.raises(ValueError):
        replace(cfg.mesh, use_trust=False, use_consensus=True)
        from immunomesh.mesh.engine import run_mesh
        run_mesh(replace(cfg, mesh=replace(cfg.mesh, use_trust=False, use_consensus=True)), [], {}, {}, 1)

def test_response_state_space_valid(sc_sd):
    sc, sd = sc_sd
    r = run_variant(sc, sd, ABLATION["A4_full_system"])
    assert set(r["epochs"].state.unique()) <= {"NORMAL", "SUSPICIOUS", "HIGH_RISK", "QUARANTINED", "RECOVERING", "RESTORED"}

def test_audit_events_reference_valid_states(sc_sd):
    sc, sd = sc_sd
    r = run_variant(sc, sd, ABLATION["A4_full_system"])
    ev = pd.DataFrame(r["events"])
    if len(ev):
        assert ev.event_type.isin(["ANOMALY_DETECTED", "SUSPICION_RAISED", "HIGH_RISK_DECLARED", "QUARANTINE_STARTED",
                                   "SUSPICION_CLEARED", "DE_ESCALATED", "RECOVERY_STARTED", "RESTORED",
                                   "RECOVERY_FAILED_REQUARANTINE", "RETURNED_TO_NORMAL"]).all()
