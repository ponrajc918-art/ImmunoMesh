# Evidence summary — ImmunoMesh v1.0.0-research

Every number below was read from `results/final/_seeds/seed_200.json … seed_207.json` or the tables
generated from them, and was independently recomputed (see "How these numbers were verified").
All data are **synthetic traffic from this repository's own simulator**. Nothing here is a
real-world, industrial-network or physical-hardware result.

## 1. Research question and contribution
*Can an unsupervised detector trained only on a device's normal behaviour, combined with
explanation, per-device trust, peer agreement and a simulated response policy, detect and contain
anomalous devices in a small edge/industrial network — and what does each layer contribute?*

The contribution is an integrated, reproducible software prototype and an honest ablation of its
layers on controlled synthetic traffic — not a claim of state-of-the-art detection.

## 2. System
| Stage | What it does | Key parameters (from `run_manifest.json`) |
|---|---|---|
| Simulator | Flow records for 9 devices (4 cameras, 3 sensors, 2 PLCs) with injected data-quality faults | missing 0.5 %, duplicates 0.3 %, invalid 0.2 % |
| Cleaning / scaling | Dedup, invalid-row removal, median imputation, one-hot + z-score; fitted on the anomaly-free training period only | — |
| 15 features | `packet_rate, byte_rate, log_packets, log_bytes, duration_s, conn_freq, failed_ratio, dest_diversity, dport_diversity, src_dst_freq, protocol_share, new_destination, pkt_rate_dev, byte_rate_dev, burst_indicator` (causal 10 s window per device) | window 10 s |
| Detector | Isolation Forest; score = −`score_samples`; threshold = 0.99 quantile of **training** scores | 200 trees, max_samples 256 |
| Evidence | SHAP `TreeExplainer` attribution plus robust z-score vs. the device-type baseline; a flow is *corroborated* if top-5 attributions are backed by deviations | z ≥ 3, strength ≥ 0.3 |
| Trust | Per-device score; falls with severity and recent repeats, recovers geometrically | λ_pen 0.35, λ_rec 0.10, γ 0.5, history 6 |
| Peer consensus | Each device has its own Isolation Forest (80 % subsample, different seed) observing other devices' flows with probability 0.5; trust-weighted | ω 0.3, visibility 0.5 |
| Response (simulated) | NORMAL→SUSPICIOUS→HIGH_RISK→QUARANTINED→RECOVERING→RESTORED; a software state only | cooldown 6 epochs, escalation ×2 |

Attack types: traffic spike, port scan, brute force, exfiltration, protocol irregularity. Per seed in
E3, 2 devices are attacked in 2 windows of 60 s each within a 900 s evaluation period (4 attack
windows per seed, 32 across 8 seeds). Training and evaluation traffic use different RNG seeds.

## 3. Experimental design
Seeds 200–207; 900 s training and 900 s evaluation per seed. Scenarios: E1 normal only, E2 low
intensity, E3 high intensity, E4 five devices attacked, E8 threshold sweep, E9 attack-window-length
sweep, E10 recovery/quarantine (3 devices × 3 windows × 90 s). E8 and E9 reuse the same trained
detector and evaluation data per seed, so they are sensitivity analyses, not independent experiments.
Ablation variants A0–A4 add evidence, trust, consensus and response in turn. No hyper-parameter was
tuned on these results; parameters were fixed in `config/default.yaml` before the experiments (this is
the author's statement — no commit history was available to the reviewer to confirm it).

## 4. Flow-level detection (each flow vs. ground truth; mean ± sample std over 8 seeds)
| Scenario | Precision | Recall | F1 | ROC-AUC | False-positive rate |
|---|---|---|---|---|---|
| E2 low intensity | 0.837 ± 0.074 | 0.811 ± 0.192 | 0.818 ± 0.135 | 0.987 | 0.011 |
| E3 high intensity | 0.948 ± 0.021 | 0.826 ± 0.152 | 0.877 ± 0.099 | 0.989 | 0.010 |
| E4 five devices attacked | 0.979 ± 0.006 | 0.747 ± 0.178 | 0.838 ± 0.120 | 0.986 | 0.011 |
| E10 recovery/quarantine | 0.985 ± 0.004 | 0.818 ± 0.143 | 0.888 ± 0.094 | 0.991 | 0.011 |
| E1 normal only | undefined (no positives) | — | — | — | 0.009 |

**Per-attack recall, E3** (per seed, then summarised over the seeds in which the attack occurred):

| Attack | seeds with attack | mean | std | min–max |
|---|---|---|---|---|
| port scan | 5 | 1.000 | 0.000 | 1.00–1.00 |
| protocol irregularity | 6 | 0.979 | 0.029 | 0.94–1.00 |
| brute force | 6 | 0.804 | 0.279 | 0.26–1.00 |
| traffic spike | 4 | 0.674 | 0.464 | 0.00–0.99 |
| **exfiltration** | **4** | **0.285** | 0.197 | 0.10–0.49 |

Exfiltration is the clear weak point. Its estimate rests on 4 seeds, and traffic spike is bimodal, so
these per-attack numbers are indicative only.

Threshold sensitivity (E3, flow-level): raising the quantile from 0.95 to 0.999 moves precision
0.808→0.983, recall 0.900→0.561 and FPR 0.051→0.001. Window length (30→240 s): recall stays ≈0.82
while precision rises 0.897→0.987 as the attack share of flows rises 0.11→0.52; this is a prevalence
effect, not a better detector.

## 5. Model comparison (E3, flow-level; same quantile protocol)
| Model | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| Isolation Forest | 0.948 | 0.826 | 0.877 | 0.989 |
| Local Outlier Factor | 0.938 | 0.992 | 0.964 | 0.998 |
| One-Class SVM | 0.912 | 1.000 | 0.954 | 0.999 |

Paired per-seed differences vs. Isolation Forest (n = 8): at high intensity LOF has higher recall, F1
and ROC-AUC in 8/8 seeds and lower precision in 7/8 (mean −0.010); OCSVM has higher recall and ROC-AUC
in 8/8 and F1 in 6/8. At low intensity only recall is consistently higher (OCSVM 8/8, LOF 6/8); F1 is
higher in 4–5 of 8 seeds. **Isolation Forest is not the best detector here.** It remains the core
detector because the SHAP `TreeExplainer` evidence layer and the peer monitors were built on it, not
because it scores best. No significance test was run; per-attack recall was not computed for LOF/OCSVM.

## 6. Epoch/window-level results (10 s per-device epochs; **not comparable with §4**)
| E3 variant | Epoch precision | Epoch recall | Epoch F1 | Attack windows detected | Mean latency (simulated s) |
|---|---|---|---|---|---|
| A0 anomaly only | 0.855 | 0.859 | 0.851 | 0.969 | 8.1 |
| A1 + evidence | 0.855 | 0.859 | 0.851 | 0.969 | 8.1 |
| A2 + trust | 0.354 | 0.844 | 0.496 | 0.875 | 10.3 |
| A3 + consensus | 0.354 | 0.833 | 0.494 | 0.875 | 10.9 |
| A4 full system | 0.400 | 0.901 | 0.551 | 0.969 | 8.1 |

A0 and A1 are identical: evidence corroboration changed no alert decision. Adding trust lowers epoch
precision because alerts persist while trust recovers after an attack; the response layer partly
restores it. Trust/consensus/response are operational layers and are not optimised for per-epoch F1.
**E10 (full system):** attack windows detected 0.944 ± 0.119; windows contained by simulated
quarantine 0.819 ± 0.156; of those, restored 0.824 ± 0.149; false quarantines 0.000; mean
simulated time to quarantine 25.6 s and to restore after the attack ends 117 s; clean-device alert
rate 0.003. (Epoch precision for the same run is 0.499 against flow-level precision 0.985 — the two
levels measure different things.) "Quarantine" and "restore" are state changes in software; no network
action occurs.

## 7. Reproducibility
`python -m immunomesh.cli final --seeds 200 … 207 --train-s 900 --eval-s 900` then
`python -m immunomesh.cli report` (see `docs/REPRODUCIBILITY.md`). Verified in this audit: seed 200
re-run from scratch in a fresh venv with newer scikit-learn/numpy/shap reproduced the stored result
exactly (1,422 numeric cells, max difference 0.0); the headline table was independently recomputed
from the raw per-seed JSON and matched to 1e-16; the full suite passes in a venv built from the
complete `requirements-lock.txt`. This is repeatability on one OS/architecture, not independent
replication, and seeds 201–207 were not re-run in the fresh environment.

## 8. HIL loopback test (scope)
`results/hil/` is a real packet-capture run on the build machine's loopback interface with locally
generated TCP connections (2,640 packets, 264 flows). It validates the capture→flow→audit data path
only. It involved no Raspberry Pi, IP camera or managed switch, no attack traffic and no ground
truth, so it reports no detection metrics, and the detector there was fitted on a handful of flows.
The live runtime uses detection and trust only; consensus, response and enforcement are not wired in.

## 9. Threats to validity
- **Synthetic, self-authored data:** the attacks, normal profiles and the 15 features were designed
  by the same author; results show behaviour on this generator, not on real networks (no domain shift).
- **Small effective sample:** 8 seeds; per-seed std is large (recall std 0.14–0.19); 4 attack windows
  per seed; flows within a window are strongly correlated, so seeds are the right unit of analysis.
  No confidence intervals or significance tests were computed.
- **Uneven attack coverage per seed** (§4 table) limits per-attack conclusions.
- **Shared-pipeline peers:** peer monitors use the same features and baseline distribution, so their
  agreement is not independent evidence.
- **Threshold chosen by training-score quantile**, so FPR on normal traffic is set by design rather than
  tuned; the 0.99 choice was fixed a priori, but sensitivity (E8) shows large recall changes.
- **Same-code repeatability:** reruns share code, platform and seeds; they do not test replication.
- **Simulated response time** measures software epochs, not network or device behaviour.

## 10. Claims this evidence supports / does not support
Supports: on controlled synthetic traffic, over 8 seeds, the prototype detects most attack flows with
high precision and ~1 % false positives, detects port scans and protocol irregularities almost
perfectly, and detects exfiltration poorly; the trust/consensus/response layers trade epoch precision
for persistence and containment in simulation; LOF and OCSVM outperform Isolation Forest on recall.
Does **not** support: real-world or industrial accuracy, physical Raspberry Pi/camera/switch
validation, detection of real attacks, production readiness, or superiority over other IDS methods.
