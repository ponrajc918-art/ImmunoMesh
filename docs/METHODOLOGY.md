# Methodology

All experiments in this document and in `results/final/` use SIMULATED/SYNTHETIC data generated
by `immunomesh.simulation.traffic`. No physical hardware and no real attacks are involved in any
of these experiments or their reported metrics.

This project separately contains a real-network integration layer
(`immunomesh/integration/`, `docs/REAL_NETWORK_GUIDE.md`) that does capture and process real
packets — exercised so far only by a loopback HIL self-test (`results/hil/`), not a physical
deployment, and not used to produce any detection-performance metric in this document.

## Pipeline
Simulated flows → `DataCleaner` (Phase 3) → `FeatureEngineer` (Phase 4, causal windowed
features) → `FeatureMatrixBuilder` (Phase 3, one-hot + z-score) → `AnomalyDetector`
(Isolation Forest, Phase 5) → `EvidenceGenerator` (SHAP + baseline deviation, Phase 6) →
epoch aggregation → `TrustEngine` (Phase 7) → peer consensus (Phase 8) → `ResponseEngine`
(Phase 9) → `AuditStore` (Phase 9) → dashboard / experiments (Phase 10).

Every preprocessing/feature/detector/evidence component is **fit only on the anomaly-free
training period** and applied unchanged to evaluation data — no evaluation data leaks into
fitting.

## Mathematical formulation

**Anomaly score**: `anomaly_score = -IsolationForest.score_samples(x)` (higher = more anomalous).
**Threshold**: the `detector.threshold_quantile` (default 0.99) quantile of the TRAINING
scores. **Confidence**: `|score - threshold| / (threshold - median(train scores))`, clipped to [0,1].

**Evidence** (Phase 6): for a flagged flow, `contribution_i = -SHAP_i(IsolationForest)`
(SHAP explains expected isolation path length, which is *decreasing* in anomaly score, so the
sign is flipped for "contribution toward anomalous"). Each engineered feature also gets a
robust z-score against its device-type (or optionally device-type+service) training baseline:
`z = (x - median) / max(1.4826*MAD, 0.5*std)`. A flow is **corroborated** when the top-k
SHAP-attributed features are backed (|z| >= z_threshold) for at least `min_strength` (default
0.3) of their summed positive contribution.

**Trust** (Phase 7), per device per epoch, severity `s` in [0,1]:
```
suspicious (s>0):  T <- max(0, T - lambda_pen * s * (1 + gamma * k))     k = # suspicious epochs in last H
clean (s=0):        T <- T + lambda_rec * (1 - T)
```
Risk band: LOW (T ≥ alert_trust) / MEDIUM (≥ t_high) / HIGH (≥ t_quar) / CRITICAL.

**Peer consensus** (Phase 8): each device also runs its own Isolation Forest trained on an
80% subsample of the (same) baseline with a different seed. An observer sees each flow of
another device with probability `visibility` (default 0.5) and reports its own flag rate
`o_{p,d}`. `peer_support = Σ w_p·o_{p,d} / Σ w_p` (weights = each peer's trust at the previous
epoch). `consensus = (1-ω)·a_self + ω·peer_support`.

**Response** (Phase 9): a 6-state machine (NORMAL → SUSPICIOUS → HIGH_RISK → QUARANTINED →
RECOVERING → RESTORED → NORMAL) driven by detection, evidence confirmation, trust and
(optionally) the consensus gate. See `immunomesh/response/engine.py` docstring for the exact
transition table. **Quarantine only changes a software state field** — no network interface,
firewall rule, or real device is touched.

## Experimental methodology
- Environment/software versions and seeds are written to `results/final/run_manifest.json` by
  every `immunomesh.cli final` run.
- Simulator, cleaner, features, detector, evidence, trust, consensus and response parameters
  are fixed in `config/default.yaml` **before** any results were examined; the only
  configuration values discovered from data are the standard-scaler statistics and the
  Isolation Forest's training-score threshold, both fit strictly on the training period.
- Evaluation metrics (Phase 5 flow-level, Phase 10 epoch/window/response-level) are defined in
  `immunomesh/evaluation/` and computed only from the implemented pipeline's outputs plus the
  simulator's ground-truth labels — never invented or estimated by hand.
- Multi-seed results (`immunomesh.cli final`) use independent seeds per run; per-seed results
  are checkpointed so a run can be resumed.
