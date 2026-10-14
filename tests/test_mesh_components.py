import numpy as np, pytest
from immunomesh.config import MeshConfig
from immunomesh.trust.engine import TrustEngine
from immunomesh.response.engine import ResponseEngine
from immunomesh.consensus.peers import consensus_for
from immunomesh.storage.audit import AuditStore

def test_trust_formula_hand_computed():
    te = TrustEngine(MeshConfig(), ["a"])
    assert te.update("a", 1.0) == pytest.approx(0.65)            # 1 - 0.35*1*(1+0.5*0)
    assert te.update("a", 1.0) == pytest.approx(0.125)           # 0.65 - 0.35*1*(1+0.5*1)
    assert te.update("a", 0.0) == pytest.approx(0.125 + 0.1 * 0.875)
    assert te.risk_level(0.9) == "LOW" and te.risk_level(0.6) == "MEDIUM"
    assert te.risk_level(0.4) == "HIGH" and te.risk_level(0.1) == "CRITICAL"

def test_trust_bounds_and_monotone_recovery():
    te = TrustEngine(MeshConfig(), ["a"])
    for _ in range(10): te.update("a", 1.0)
    assert te.trust["a"] == 0.0
    prev = 0.0
    for _ in range(50):
        T = te.update("a", 0.0); assert prev <= T <= 1.0; prev = T

def test_consensus_hand_computed():
    vis = np.zeros((3, 3, 1)); flg = np.zeros((3, 3, 1))
    vis[:, 0, 0] = [0, 4, 2]; flg[:, 0, 0] = [0, 2, 2]
    sup, c, ag = consensus_for(0, 0, vis, flg, np.array([1.0, 1.0, 0.5]), 0.4, 0.3, 0.3)
    assert sup == pytest.approx((1.0 * 0.5 + 0.5 * 1.0) / 1.5)
    assert c == pytest.approx(0.7 * 0.4 + 0.3 * sup) and ag == 1.0

def test_consensus_no_observers_falls_back_to_self():
    sup, c, ag = consensus_for(0, 0, np.zeros((2, 2, 1)), np.zeros((2, 2, 1)), np.ones(2), 0.5, 0.3, 0.3)
    assert c == 0.5 and np.isnan(ag)

def test_response_full_lifecycle():
    cfg = MeshConfig(cooldown_epochs=2, recover_clean_epochs=2, probation_epochs=2, clear_epochs=2)
    r = ResponseEngine(cfg, ["a"])
    seq = []
    def st(susp, conf, trust, cons=None): seq.append(r.step("a", susp, conf, trust, cons)[1:])
    st(True, False, 0.9);   assert seq[-1] == ("SUSPICIOUS", "SUSPICION_RAISED")
    st(True, True, 0.4);    assert seq[-1] == ("HIGH_RISK", "HIGH_RISK_DECLARED")
    st(True, True, 0.2);    assert seq[-1] == ("QUARANTINED", "QUARANTINE_STARTED")
    st(False, False, 0.6);  assert r.dev["a"].state == "QUARANTINED"      # cooldown not elapsed
    st(False, False, 0.7);  assert r.dev["a"].state == "QUARANTINED"
    st(False, False, 0.8);  assert seq[-1] == ("RECOVERING", "RECOVERY_STARTED")
    st(False, False, 0.8);  st(False, False, 0.9)
    assert seq[-1] == ("RESTORED", "RESTORED")
    st(False, False, 0.9);  assert seq[-1] == ("NORMAL", "RETURNED_TO_NORMAL")

def test_response_escalation_on_failed_recovery():
    cfg = MeshConfig(cooldown_epochs=1, recover_clean_epochs=1, probation_epochs=3)
    r = ResponseEngine(cfg, ["a"])
    for args in [(True, True, 0.4), (True, True, 0.4), (True, True, 0.1)]: r.step("a", *args, None)
    assert r.dev["a"].state == "QUARANTINED"
    r.step("a", False, False, 0.9, None); r.step("a", False, False, 0.9, None)
    assert r.dev["a"].state == "RECOVERING"
    r.step("a", True, True, 0.9, None)
    assert r.dev["a"].state == "QUARANTINED" and r.dev["a"].cooldown == 2   # 1 * escalation_factor 2

def test_consensus_gate_blocks_quarantine():
    cfg = MeshConfig()
    r = ResponseEngine(cfg, ["a"])
    r.step("a", True, True, 0.4, 0.9); r.step("a", True, True, 0.4, 0.9)
    assert r.dev["a"].state == "HIGH_RISK"
    r.step("a", True, True, 0.1, 0.05)     # trust low but consensus below gate
    assert r.dev["a"].state == "HIGH_RISK"

def test_audit_store_roundtrip():
    a = AuditStore()
    a.register_experiment("e1", 1, {"x": 1})
    a.log_events("e1", [{"ts": 1.0, "device": "d", "event_type": "X", "trust": np.float64(0.5), "details": "{}"}])
    ev = a.events("e1")
    assert len(ev) == 1 and ev.iloc[0].trust == 0.5 and ev.iloc[0].experiment_id == "e1"
