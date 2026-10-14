# Phase status
| Phase | Status | Key files | Tests |
|---|---|---|---|
| 1 Architecture & config | complete | config.py, schema.py, logging_utils.py, cli.py | test_phases_1_5.py |
| 2 Traffic simulation | complete (frozen) | simulation/traffic.py | test_phases_1_5.py, test_baseline_regression.py |
| 3 Preprocessing | complete (frozen) | preprocessing/cleaner.py, preprocessing/matrix.py | test_phases_1_5.py |
| 4 Feature engineering | complete (frozen) | features/engineering.py | test_phases_1_5.py |
| 5 Anomaly detection | complete (frozen baseline) | detection/isolation_forest.py, evaluation/metrics.py | test_phases_1_5.py, test_baseline_regression.py |
| 6 Evidence & explainability | complete | evidence/explainer.py; investigation: experiments/investigate.py | test_phase6_9_integration.py |
| 7 Trust | complete | trust/engine.py | test_mesh_components.py |
| 8 Peer consensus | complete | consensus/peers.py | test_mesh_components.py |
| 9 Response, quarantine, recovery, audit | complete | response/engine.py, storage/audit.py, mesh/engine.py | test_mesh_components.py, test_phase6_9_integration.py |
| 10 Dashboard, multi-seed experiments, ablation, model comparison | complete | dashboard/, experiments/final.py, experiments/report.py | test_dashboard_data.py |

Phases 1-5 are **frozen**: `tests/test_baseline_regression.py` fails the suite if the
simulator, cleaner, features, or detector output changes for seed 42. Any future change to
those modules must update `tests/data/baseline_phase5_seed42.json` deliberately and explain why
in this file.

Known limitation carried from the investigation (not fixed, by design — see
`docs/LIMITATIONS.md`): brute-force / low-rate attacks against low-baseline-rate device types
are ranked well (AUC ≈0.98) but under-detected at the fixed global threshold.

Run order: `pytest` → `python -m immunomesh.cli demo` → `python -m immunomesh.cli dashboard`
→ `python -m immunomesh.cli final` → `python -m immunomesh.cli report`.

## Real-network integration layer (additive, Phases 1-10 untouched)

Built as an adapter layer around the frozen core — see `docs/hardware/architecture.md` for the
full map and `docs/REAL_NETWORK_GUIDE.md` for how to use it. Summary:

| Area | Status | Notes |
|---|---|---|
| Packet capture | real, tested | stdlib AF_PACKET; verified against real loopback traffic in this environment |
| Flow aggregation + schema mapping | real, tested | documented mapping in capture/flow.py and docs/hardware/packet_capture.md |
| Device discovery (ARP/mDNS/DHCP-observation) | real (ARP), honest UNSUPPORTED (mDNS without zeroconf) | passive only, no active scanning |
| Device classification/registry | real, tested | heuristic from observed ports |
| Live runtime (BASELINE_COLLECTION -> MONITORING) | real, tested | reuses fit_baseline/evaluate_scenario unmodified |
| Supervisor (health states) | tested with fault injection | process never crashes on a bad cycle |
| Switch adapters | dry_run real; snmp/ssh honest skeletons, UNSUPPORTED by default | no physical switch was available to verify a real adapter |
| AP adapter | interface only | UnconfiguredAccessPointAdapter always UNSUPPORTED — no AP hardware available |
| Camera adapters | real, tested | RTSP banner probe + ONVIF WS-Discovery, both verified to honestly report no-camera-found |
| Enforcement (policy/executor/verification/rollback) | fully tested with a fake switch | OBSERVE_ONLY/DRY_RUN/ENFORCE gating, confirmation requirement, rollback on failed verification all exercised |
| CLI (doctor/discover/capture/monitor/edge/devices/capabilities/dry-run/enforce/status/setup) | all run for real in this environment | see docs/hardware/deployment.md |
| Dashboard Live Network tab | real, tested | reads results/live or results/hil only, never simulation data |
| HIL self-test | run for real (loopback only) | results/hil/RESULTS.md; explicitly NOT a physical-hardware claim |

Existing commands (`run`, `demo`, `final`, `report`) and all 27 original tests were re-verified
unchanged after this work (see the final development report).
