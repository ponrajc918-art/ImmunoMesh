# ImmunoMesh — Phase 10 multi-seed results (auto-generated)

**All data are SIMULATED/SYNTHETIC.** These are software-only results; no hardware, real network, or real attacks were used.

Seeds: [200, 201, 202, 203, 204, 205, 206, 207]  (n=8). Config: train/eval duration = 900.0s / 900.0s per seed. Environment: Python 3.12.3, scikit-learn 1.8.0, Linux-6.18.44-fc-v70-x86_64-with-glibc2.39.

**How to read the metrics.** *Flow-level* metrics score every flow record against its ground-truth label. *Epoch/window-level* metrics (ablation, response, recovery) score 10 s per-device epochs and attack windows after trust/consensus/response aggregation. They have different units and are not interchangeable. `std` is the sample standard deviation (ddof=1) across seeds; `nan` means undefined (e.g. E1 has no attack flows, so precision/recall/F1/ROC-AUC are undefined, not zero).

## Flow-level detection, by experiment/scenario (mean ± std over seeds)

| experiment | scenario | n_seeds | precision_mean | precision_std | recall_mean | recall_std | f1_mean | f1_std | roc_auc_mean | false_positive_rate_mean |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | normal_only | 8 | nan | nan | nan | nan | nan | nan | nan | 0.009 |
| E10 | recovery_quarantine | 8 | 0.985 | 0.004 | 0.818 | 0.143 | 0.888 | 0.094 | 0.991 | 0.011 |
| E2 | low_intensity | 8 | 0.837 | 0.074 | 0.811 | 0.192 | 0.818 | 0.135 | 0.987 | 0.011 |
| E3 | high_intensity | 8 | 0.948 | 0.021 | 0.826 | 0.152 | 0.877 | 0.099 | 0.989 | 0.010 |
| E4 | multi_device_5 | 8 | 0.979 | 0.006 | 0.747 | 0.178 | 0.838 | 0.120 | 0.986 | 0.011 |
| E8 | q0.95 | 8 | 0.808 | 0.047 | 0.900 | 0.109 | 0.849 | 0.068 | 0.989 | 0.051 |
| E8 | q0.98 | 8 | 0.902 | 0.034 | 0.855 | 0.148 | 0.873 | 0.093 | 0.989 | 0.021 |
| E8 | q0.99 | 8 | 0.948 | 0.021 | 0.826 | 0.152 | 0.877 | 0.099 | 0.989 | 0.010 |
| E8 | q0.995 | 8 | 0.965 | 0.020 | 0.711 | 0.186 | 0.807 | 0.144 | 0.989 | 0.005 |
| E8 | q0.999 | 8 | 0.983 | 0.021 | 0.561 | 0.237 | 0.687 | 0.226 | 0.989 | 0.001 |
| E9 | window_120s | 8 | 0.975 | 0.011 | 0.821 | 0.147 | 0.885 | 0.095 | 0.989 | 0.010 |
| E9 | window_240s | 8 | 0.987 | 0.007 | 0.818 | 0.153 | 0.888 | 0.100 | 0.988 | 0.011 |
| E9 | window_30s | 8 | 0.897 | 0.044 | 0.820 | 0.150 | 0.852 | 0.101 | 0.989 | 0.010 |
| E9 | window_60s | 8 | 0.948 | 0.021 | 0.826 | 0.152 | 0.877 | 0.099 | 0.989 | 0.010 |


## ablation E3 high intensity

| variant | epoch_precision_mean | epoch_precision_std | epoch_recall_mean | epoch_recall_std | epoch_f1_mean | epoch_f1_std | epoch_fpr_mean | epoch_fpr_std | clean_device_alert_rate_mean | clean_device_alert_rate_std | window_detection_rate_mean | window_detection_rate_std | mean_latency_s_mean | mean_latency_s_std | false_alert_epochs_per_device_hour_mean | false_alert_epochs_per_device_hour_std | false_quarantine_rate_mean | false_quarantine_rate_std | quarantine_rate_mean | quarantine_rate_std | recovery_rate_mean | recovery_rate_std | mean_sim_quarantine_latency_s_mean | mean_sim_quarantine_latency_s_std | mean_sim_time_to_restore_after_attack_s_mean | mean_sim_time_to_restore_after_attack_s_std |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0_anomaly_only | 0.855 | 0.041 | 0.859 | 0.154 | 0.851 | 0.088 | 0.004 | 0.002 | 0.001 | 0.001 | 0.969 | 0.088 | 8.084 | 4.062 | 1.556 | 0.531 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| A1_plus_evidence | 0.855 | 0.041 | 0.859 | 0.154 | 0.851 | 0.088 | 0.004 | 0.002 | 0.001 | 0.001 | 0.969 | 0.088 | 8.084 | 4.062 | 1.556 | 0.531 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| A2_plus_trust | 0.354 | 0.032 | 0.844 | 0.113 | 0.496 | 0.033 | 0.048 | 0.009 | 0.000 | 0.000 | 0.875 | 0.134 | 10.274 | 4.292 | 16.667 | 3.292 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| A3_plus_consensus | 0.354 | 0.031 | 0.833 | 0.116 | 0.494 | 0.035 | 0.047 | 0.009 | 0.000 | 0.000 | 0.875 | 0.134 | 10.899 | 5.669 | 16.389 | 3.009 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| A4_full_system | 0.400 | 0.029 | 0.901 | 0.120 | 0.551 | 0.032 | 0.042 | 0.008 | 0.002 | 0.004 | 0.969 | 0.088 | 8.084 | 4.062 | 14.611 | 2.952 | 0.000 | 0.000 | 0.812 | 0.177 | 0.896 | 0.146 | 27.236 | 3.942 | 105.214 | 2.298 |


*Epoch-level (not comparable with the flow-level table). A0 and A1 are identical: evidence corroboration changed no alert decisions in this setup. Adding trust (A2) lowers epoch precision because alerts persist while trust recovers after an attack ends; trust, consensus and response are operational layers and are not optimised for instantaneous F1.*


## model comparison

| scenario | model | precision_mean | precision_std | recall_mean | recall_std | f1_mean | f1_std | roc_auc_mean | roc_auc_std | fit_s_mean | fit_s_std | score_s_mean | score_s_std |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| high_intensity | IsolationForest | 0.948 | 0.021 | 0.826 | 0.152 | 0.877 | 0.099 | 0.989 | 0.009 | nan | nan | nan | nan |
| high_intensity | LocalOutlierFactor | 0.938 | 0.019 | 0.992 | 0.004 | 0.964 | 0.011 | 0.998 | 0.001 | 0.165 | 0.005 | 0.198 | 0.009 |
| high_intensity | OneClassSVM | 0.912 | 0.023 | 1.000 | 0.000 | 0.954 | 0.013 | 0.999 | 0.001 | 0.011 | 0.003 | 0.020 | 0.001 |
| low_intensity | IsolationForest | 0.837 | 0.074 | 0.811 | 0.192 | 0.818 | 0.135 | 0.987 | 0.013 | nan | nan | nan | nan |
| low_intensity | LocalOutlierFactor | 0.829 | 0.041 | 0.964 | 0.025 | 0.891 | 0.029 | 0.997 | 0.001 | 0.169 | 0.008 | 0.173 | 0.009 |
| low_intensity | OneClassSVM | 0.761 | 0.042 | 0.981 | 0.034 | 0.856 | 0.030 | 0.993 | 0.010 | 0.010 | 0.001 | 0.018 | 0.001 |


*Flow-level; each model's threshold is the 0.99 quantile of its own training scores. Isolation Forest has the highest mean precision but lower mean recall, F1 and ROC-AUC than LocalOutlierFactor and OneClassSVM in both scenarios. Paired per-seed differences are consistent for recall and, at high intensity, for LOF's F1 and ROC-AUC (8/8 seeds), but not for F1 at low intensity (see docs/EVIDENCE_SUMMARY.md). fit_s/score_s are wall-clock on the build machine and were not measured for Isolation Forest (nan).*


## threshold analysis flow

| quantile | precision | recall | f1 | false_positive_rate |
|---|---|---|---|---|
| 0.950 | 0.808 | 0.900 | 0.849 | 0.051 |
| 0.980 | 0.902 | 0.855 | 0.873 | 0.021 |
| 0.990 | 0.948 | 0.826 | 0.877 | 0.010 |
| 0.995 | 0.965 | 0.711 | 0.807 | 0.005 |
| 0.999 | 0.983 | 0.561 | 0.687 | 0.001 |


*Flow-level; E3 scenario; threshold = the stated quantile of training scores.*


## per attack recall E3

| attack | n_seeds | mean_recall | std_recall | min_recall | max_recall | mean_flows |
|---|---|---|---|---|---|---|
| brute_force | 6 | 0.804 | 0.279 | 0.255 | 1.000 | 447.500 |
| exfiltration | 4 | 0.285 | 0.197 | 0.101 | 0.487 | 148.500 |
| port_scan | 5 | 1.000 | 0.000 | 1.000 | 1.000 | 718.600 |
| protocol_irregularity | 6 | 0.979 | 0.029 | 0.940 | 1.000 | 398.833 |
| traffic_spike | 4 | 0.674 | 0.464 | 0.000 | 0.987 | 283.750 |


*Recall is computed per seed, then summarised over the `n_seeds` seeds in which that attack type occurred (each seed draws attack types for only a few windows, so `n_seeds` is below 8 for most attacks). Estimates resting on few seeds, with a wide min-max range, are weak.*


## window length sweep

| scenario | precision_mean | precision_std | recall_mean | recall_std | f1_mean | f1_std | anomalous_flow_share_mean | anomalous_flow_share_std |
|---|---|---|---|---|---|---|---|---|
| window_120s | 0.975 | 0.011 | 0.821 | 0.147 | 0.885 | 0.095 | 0.338 | 0.060 |
| window_240s | 0.987 | 0.007 | 0.818 | 0.153 | 0.888 | 0.100 | 0.518 | 0.071 |
| window_30s | 0.897 | 0.044 | 0.820 | 0.150 | 0.852 | 0.101 | 0.110 | 0.025 |
| window_60s | 0.948 | 0.021 | 0.826 | 0.152 | 0.877 | 0.099 | 0.199 | 0.042 |


*Flow-level; attack window length varied at fixed high intensity.*


## Figures

- `figures/ablation_E3.png`
- `figures/evidence_contributions_E3.png`
- `figures/per_attack_recall_E3.png`
- `figures/roc_comparison_E3.png`
- `figures/score_distribution_E3.png`
- `figures/threshold_sensitivity_E8.png`

Generated by `python -m immunomesh.cli report` from `results/final/_seeds/*.json`. See docs/EXPERIMENTS.md for the experiment definitions and docs/LIMITATIONS.md for caveats.