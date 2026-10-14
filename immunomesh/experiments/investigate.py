"""Scientific investigation of weak brute-force recall (preliminary seed-42 baseline).

Does NOT modify the simulator or detector. Uses independent seeds (default 100..109) so
conclusions are not fitted to seed 42. Every number in the written summary is computed here.

Questions:
 Q1 Ranking vs thresholding: is brute force poorly *ranked* (low AUC) or just below the
    operating threshold (high AUC, low recall)?
 Q2 Is recall lower during window ramp-up (causal windowed features need time to fill)?
 Q3 Does recall depend on the attacked device type?
 Q4 What sets the threshold? Composition of the training-score tail (benign DNS/NTP flows,
    cold start).
 Q5 What does the model attribute brute-force flows to (SHAP) vs port scan?
 Q6 Does a service-level evidence baseline separate false positives from attacks?
"""
from __future__ import annotations
import dataclasses, json, logging
from pathlib import Path
import numpy as np
import pandas as pd
from immunomesh.config import load_config, ALL_ATTACKS
from immunomesh.pipeline import fit_baseline, evaluate_scenario
from immunomesh.simulation.traffic import generate_traffic
from immunomesh.evaluation.metrics import detection_metrics
from immunomesh.evidence.explainer import EvidenceGenerator
from immunomesh.experiments.common import md_table, mean_std
from immunomesh.schema import T_START, ENGINEERED

log = logging.getLogger("immunomesh.investigate")
QS = [0.90, 0.95, 0.99, 0.999]
FEATS = ["conn_freq", "failed_ratio", "dest_diversity", "dport_diversity", "src_dst_freq",
         "byte_rate", "packet_rate", "duration_s", "pkt_rate_dev", "byte_rate_dev"]


def run(seeds=range(100, 110), out_dir="results/investigations/brute_force", shap_seeds=3):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    per_run, tails, bf_rows, shap_rows, ev_rows = [], [], [], [], []
    for si, seed in enumerate(seeds):
        cfg = load_config(overrides={"seed": seed})
        ctx = fit_baseline(cfg)
        s_tr = ctx.det.score(ctx.Xtr)
        thr = ctx.det.threshold_
        thr_q = {q: float(np.quantile(s_tr, q)) for q in QS}
        tf = ctx.train_f.copy(); tf["score"] = s_tr
        tf["cold"] = (tf.timestamp - tf.groupby("src_id").timestamp.transform("min")) < cfg.features.window_s
        tail = tf[tf.score > thr]
        aux = tf.dst_port.isin([53, 123])
        tails.append({"seed": seed, "n_train": len(tf), "n_tail": len(tail),
                      "tail_frac_dns_ntp": float(tail.dst_port.isin([53, 123]).mean()),
                      "all_frac_dns_ntp": float(aux.mean()),
                      "tail_frac_cold_start": float(tail.cold.mean()), "all_frac_cold_start": float(tf.cold.mean()),
                      "threshold": thr})
        eg_plain = EvidenceGenerator(ctx.det, cfg.evidence).fit(ctx.train_f)
        eg_svc = EvidenceGenerator(ctx.det, dataclasses.replace(cfg.evidence, baseline_by_service=True)).fit(ctx.train_f)
        base_med = ctx.train_f.groupby("device_type")[FEATS].median()
        for inten in ("low", "high"):
            for atk in ALL_ATTACKS:
                sim = dataclasses.replace(cfg.simulation, intensity=inten, attack_types=[atk])
                raw = generate_traffic(sim, seed=seed + 1, with_anomalies=True)
                ev = evaluate_scenario(cfg, ctx, raw)
                f, p, X = ev["eval_f"], ev["pred"], ev["Xev"]
                m = detection_metrics(p.label, p.is_anomaly, p.anomaly_score)
                a = f[f.label == 1].copy()
                a["score"] = p.anomaly_score[f.label == 1].to_numpy()
                a["det"] = p.is_anomaly[f.label == 1].to_numpy()
                # window offset + attacked device
                offs = []
                for _, r in a.iterrows():
                    o = np.nan
                    for kind, t0, t1 in ev["windows"].get(r.src_id, []):
                        rel = r.timestamp - T_START
                        if t0 <= rel < t1:
                            o = rel - t0
                    offs.append(o)
                a["offset"] = offs
                normal = p[f.label == 0].anomaly_score.to_numpy()
                row = {"seed": seed, "intensity": inten, "attack": atk, "n_attack_flows": len(a),
                       "recall_thr": m["recall"], "precision": m["precision"], "auc": m["roc_auc"],
                       "recall_first10s": float(a[a.offset < 10].det.mean()) if (a.offset < 10).any() else np.nan,
                       "recall_after10s": float(a[a.offset >= 10].det.mean()) if (a.offset >= 10).any() else np.nan,
                       "median_attack_score": float(a.score.median()), "threshold": thr}
                for q in QS:
                    row[f"recall_q{q}"] = float((a.score > thr_q[q]).mean())
                    row[f"fpr_q{q}"] = float((normal > thr_q[q]).mean())
                for dt, g in a.groupby("device_type"):
                    row[f"recall_{dt}"] = float(g.det.mean()); row[f"n_{dt}"] = len(g)
                per_run.append(row)
                if atk == "brute_force":
                    for dt, g in a.groupby("device_type"):
                        d = {"seed": seed, "intensity": inten, "device_type": dt, "n": len(g)}
                        for ft in FEATS:
                            d[f"bf_{ft}"] = float(g[ft].median()); d[f"base_{ft}"] = float(base_med.loc[dt, ft])
                        bf_rows.append(d)
                if atk in ("brute_force", "port_scan") and si < shap_seeds:
                    idx = np.where(f.label.to_numpy() == 1)[0][:400]
                    C = eg_plain.contributions(X.iloc[idx])
                    for name, v in C.mean().items():
                        shap_rows.append({"seed": seed, "intensity": inten, "attack": atk, "feature": name, "mean_contribution": float(v)})
                if atk in ("brute_force", "port_scan", "traffic_spike") and inten == "high":
                    for mode, eg in (("device_type_baseline", eg_plain), ("service_baseline", eg_svc)):
                        E, _ = eg.explain(f, X, p)
                        if len(E):
                            E["kind"] = np.where(E.label == 1, "attack", "false_positive")
                            for kind, g in E.groupby("kind"):
                                ev_rows.append({"seed": seed, "attack_scenario": atk, "mode": mode, "kind": kind,
                                                "n": len(g), "corroborated_rate": float(g.corroborated.mean()),
                                                "mean_strength": float(g.evidence_strength.mean())})
        log.info("investigation seed %s done", seed)
    R = pd.DataFrame(per_run); T = pd.DataFrame(tails); B = pd.DataFrame(bf_rows)
    S = pd.DataFrame(shap_rows); V = pd.DataFrame(ev_rows)
    for name, df in [("per_run", R), ("train_tail", T), ("bf_features", B), ("shap", S), ("evidence_baseline_compare", V)]:
        df.to_csv(out / f"{name}.csv", index=False)
    summarize(R, T, B, S, V, out, list(seeds))
    return R, T, B, S, V


def summarize(R, T, B, S, V, out: Path, seeds) -> None:
    L = [f"# Brute-force recall investigation (auto-generated)\n\nSYNTHETIC data. Seeds: {seeds}. Single-attack scenarios "
         "(attack_types=[X]) so each attack is isolated. Mean ± std over seeds. Detector/simulator unmodified.\n"]
    g = R.groupby(["intensity", "attack"]).agg(recall=("recall_thr", "mean"), recall_sd=("recall_thr", "std"),
                                              auc=("auc", "mean"), auc_sd=("auc", "std"),
                                              r_first10=("recall_first10s", "mean"), r_after10=("recall_after10s", "mean")).reset_index()
    L += ["## Q1/Q2 Recall at the training-quantile-0.99 threshold vs ranking quality (AUC), and ramp-up\n", md_table(g)]
    q = R.groupby(["intensity", "attack"])[[f"recall_q{x}" for x in QS] + [f"fpr_q{x}" for x in QS]].mean().reset_index()
    L += ["\n## Threshold sensitivity (recall / FPR on normal flows at training-score quantiles)\n", md_table(q)]
    dt = R.groupby(["intensity", "attack"])[[c for c in R.columns if c.startswith("recall_") and c.split("_")[1] in ("camera", "sensor", "plc")]].mean().reset_index()
    L += ["\n## Q3 Recall by attacked device type (NaN = never attacked in those seeds)\n", md_table(dt)]
    L += ["\n## Q4 What is in the training-score tail that sets the threshold?\n", md_table(T.drop(columns=["seed"]).mean().to_frame("mean over seeds").reset_index())]
    bfm = B.groupby(["intensity", "device_type"])[[c for c in B.columns if c.startswith(("bf_", "base_"))]].median().reset_index()
    L += ["\n## Brute-force flow feature medians vs baseline medians (same device type)\n", md_table(bfm)]
    if len(S):
        sm = S.groupby(["attack", "feature"]).mean_contribution.mean().reset_index()
        top = sm.sort_values("mean_contribution", ascending=False).groupby("attack").head(6)
        L += ["\n## Q5 Mean SHAP contribution toward anomalous (path-length units), top 6 per attack (all attack flows)\n", md_table(top)]
    if len(V):
        vm = V.groupby(["mode", "kind"]).agg(n=("n", "sum"), corroborated_rate=("corroborated_rate", "mean"), mean_strength=("mean_strength", "mean")).reset_index()
        L += ["\n## Q6 Evidence corroboration: device-type baseline vs service-level baseline (high intensity)\n", md_table(vm)]
    (out / "summary.md").write_text("\n".join(L))


if __name__ == "__main__":
    from immunomesh.logging_utils import setup_logging
    setup_logging()
    run()
