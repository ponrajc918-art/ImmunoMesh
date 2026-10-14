# Architecture

## Modules
- `config.py` / `config/default.yaml`: typed, validated configuration (Simulation, Feature,
  Detector, Evidence, Mesh); every run saves its resolved config.
- `schema.py`: shared column names, engineered-feature list, simulator clock origin.
- `simulation/traffic.py`: labelled synthetic flow generator — 3 device types, 5 attack types,
  low/high intensity, seeded, with injected data-quality issues.
- `preprocessing/cleaner.py`, `preprocessing/matrix.py`: cleaning + quality report; one-hot +
  z-score encoding fit on training data only.
- `features/engineering.py`: 15 causal windowed cybersecurity features (documented in-module).
- `detection/isolation_forest.py`: training, scoring, quantile threshold, confidence,
  persistence. `detection/baselines.py`: One-Class SVM / LOF for comparison (Phase 10).
- `evidence/explainer.py`: SHAP model attribution + baseline-deviation corroboration (Phase 6).
- `trust/engine.py`: per-device trust score and risk band (Phase 7).
- `consensus/peers.py`: simulated peer monitors + trust-weighted consensus (Phase 8).
- `response/engine.py`: 6-state simulated response/quarantine/recovery machine (Phase 9).
- `storage/audit.py`: SQLite audit log of events and per-epoch records (Phase 9).
- `mesh/engine.py`: ties evidence + trust + consensus + response together at epoch granularity;
  ablation switches live in `MeshConfig`.
- `evaluation/metrics.py` (flow-level), `evaluation/mesh_metrics.py` (epoch/window/response
  level): all reported metrics.
- `experiments/`: `scenario.py` (reusable seed/scenario/variant runner), `investigate.py`
  (Phase 6 brute-force investigation), `final.py` (Phase 10 multi-seed experiment suite),
  `report.py` (tables/figures/RESULTS.md), `demo.py` (one instrumented run for the dashboard).
- `dashboard/`: `data.py` (data layer, no UI logic) + `app.py` (Streamlit UI, Overview /
  Detection / Evidence / Trust & consensus / Response / Audit / Experiments tabs).
- `pipeline.py`: Phase 2-5 `fit_baseline`/`evaluate_scenario` (reused by everything above) and
  the original `run_detection_pipeline` (kept for the frozen Phase 5 regression test).
- `cli.py`: `run` (Phase 2-5), `demo`, `dashboard`, `investigate`, `final`, `report`.

## Data flow
```
generate_traffic (train, anomaly-free) ─┐
                                        ├─▶ fit_baseline() ─▶ TrainedContext (cleaner, feature
generate_traffic (eval, w/ attacks)  ───┘                    engineer, matrix builder, detector)
                                                                      │
                                        evaluate_scenario(ctx, eval_raw) ─▶ predictions
                                                                      │
                                        EvidenceGenerator.explain() ─▶ evidence table
                                                                      │
                          flow_arrays() + run_mesh() (epoch aggregation, trust, consensus,
                                        response) ─▶ epoch table + audit events
                                                                      │
                          evaluation/mesh_metrics.py ─▶ metrics ─▶ report.py / dashboard
```
