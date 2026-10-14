# Experiments (Phase 10)

Run with `python -m immunomesh.cli final [--seeds ...] [--train-s S] [--eval-s S]`, then
`python -m immunomesh.cli report` to build tables/figures/RESULTS.md from the checkpointed
per-seed JSON files in `results/final/_seeds/`.

| ID | Scenario | What it tests |
|---|---|---|
| E1 | normal traffic only | false-positive behaviour with zero attacks |
| E2 | normal + low-intensity anomalies | detection under a subtle attacker |
| E3 | normal + high-intensity anomalies | main detection scenario; used for the ablation, model comparison, ROC and evidence figures |
| E4 | multiple (5) anomalous devices | detection when many devices are attacked concurrently |
| E5/E6 | trust+consensus enabled (ablation A3) vs disabled (A1) | effect of trust/consensus, read off the ablation tables |
| E7 | response enabled (A4) vs disabled (A3) | effect of the response/quarantine layer, read off the ablation tables |
| E8 | decision-threshold quantile sweep (0.95 .. 0.999) on the E3 scenario | precision/recall/FPR trade-off; peers re-derive their own threshold at the same quantile |
| E9 | attack window length swept (30s/60s/120s/240s) at fixed intensity | sensitivity to anomaly duration/proportion |
| E10 | 3 anomalous devices, 3 windows each, 90s windows | dedicated quarantine/recovery scenario for response metrics |

Ablation variants (run on every mesh scenario): A0 anomaly-detection only, A1 +evidence
corroboration, A2 +trust, A3 +peer consensus, A4 full system (+response). Component switches
live in `MeshConfig` (`use_evidence/use_trust/use_consensus/use_response`); `use_consensus`
and `use_response` both require `use_trust=True` (this is enforced and tested).

Model comparison (Isolation Forest vs One-Class SVM vs Local Outlier Factor,
`immunomesh/detection/baselines.py`) is run on E2 and E3, same feature matrix, same
threshold-quantile protocol.

All scenarios and all metrics come from `immunomesh/experiments/final.py` — nothing here is
hand-computed. See `docs/RESULTS_PRELIMINARY_SEED42.md` for the earlier single-seed Phase 5
baseline and `results/final/RESULTS.md` for the multi-seed Phase 10 results.
