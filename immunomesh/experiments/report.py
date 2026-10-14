"""Phase 10 report generator: reads results/final/_seeds/*.json (from `immunomesh.cli final`) and
writes tables/, figures/, and RESULTS.md. Every number here is aggregated straight from those files."""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from immunomesh.experiments.common import md_table
from immunomesh.experiments.final import FPR_GRID, HIST_BINS

pd.set_option("display.float_format", lambda x: f"{x:.3f}")


def load_seeds(out_dir: str | Path) -> list[dict]:
    files = sorted((Path(out_dir) / "_seeds").glob("seed_*.json"))
    if not files:
        raise FileNotFoundError(f"no seed results under {out_dir}/_seeds — run `python -m immunomesh.cli final` first")
    return [json.loads(f.read_text()) for f in files]


def build_report(out_dir: str | Path = "results/final") -> Path:
    out = Path(out_dir); tdir = out / "tables"; fdir = out / "figures"
    tdir.mkdir(exist_ok=True); fdir.mkdir(exist_ok=True)
    seeds = load_seeds(out)
    manifest = json.loads((out / "run_manifest.json").read_text()) if (out / "run_manifest.json").exists() else {}
    flow = pd.DataFrame([r for s in seeds for r in s["flow_rows"]])
    mesh = pd.DataFrame([r for s in seeds for r in s["mesh_rows"]])
    comp = pd.DataFrame([r for s in seeds for r in s["extra"].get("model_comparison", [])])
    n_seeds = len(seeds)

    # --- Flow-level detection by scenario ---
    agg_cols = ["precision", "recall", "f1", "roc_auc", "false_positive_rate", "false_negative_rate"]
    # Precision/recall/F1 are undefined (not zero) when a scenario has no positive flows (E1,
    # normal-only); the per-seed JSON stores 0.0 via zero_division=0, so mask them here.
    fm = flow.copy()
    no_pos = fm["n_anomalous_flows"] == 0
    fm.loc[no_pos, ["precision", "recall", "f1"]] = np.nan
    g = fm.groupby(["experiment", "scenario"])[agg_cols].agg(["mean", "std"])
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    g = g.reset_index()
    g.insert(2, "n_seeds", fm.groupby(["experiment", "scenario"]).size().to_numpy())
    g.to_csv(tdir / "flow_detection_by_scenario.csv", index=False)

    # --- Ablation study, per scenario ---
    mesh_cols = ["epoch_precision", "epoch_recall", "epoch_f1", "epoch_fpr", "clean_device_alert_rate",
                "window_detection_rate", "mean_latency_s", "false_alert_epochs_per_device_hour"]
    resp_cols = ["false_quarantine_rate", "quarantine_rate", "recovery_rate",
                "mean_sim_quarantine_latency_s", "mean_sim_time_to_restore_after_attack_s"]
    for exp, scen in [("E3", "high_intensity"), ("E2", "low_intensity"), ("E4", "multi_device_5"), ("E10", "recovery_quarantine")]:
        m = mesh[(mesh.experiment == exp) & (mesh.scenario == scen)]
        if not len(m): continue
        cols = mesh_cols + [c for c in resp_cols if c in m.columns]
        a = m.groupby("variant")[cols].agg(["mean", "std"])
        a.columns = [f"{x}_{y}" for x, y in a.columns]
        order = ["A0_anomaly_only", "A1_plus_evidence", "A2_plus_trust", "A3_plus_consensus", "A4_full_system"]
        a = a.reindex(order).reset_index()
        a.to_csv(tdir / f"ablation_{exp}_{scen}.csv", index=False)

    # --- Model comparison ---
    if len(comp):
        cm = comp.groupby(["scenario", "model"])[["precision", "recall", "f1", "roc_auc", "fit_s", "score_s"]].agg(["mean", "std"])
        cm.columns = [f"{a}_{b}" for a, b in cm.columns]
        cm.reset_index().to_csv(tdir / "model_comparison.csv", index=False)

    # --- Threshold analysis (E8) ---
    e8f = flow[flow.experiment == "E8"].copy()
    e8m = mesh[mesh.experiment == "E8"].copy()
    if len(e8f):
        tf = e8f.groupby("quantile")[["precision", "recall", "f1", "false_positive_rate"]].mean().reset_index()
        tm = e8m.groupby(["quantile", "variant"])[["epoch_precision", "epoch_recall", "epoch_fpr", "false_alert_epochs_per_device_hour"]].mean().reset_index()
        tf.to_csv(tdir / "threshold_analysis_flow.csv", index=False)
        tm.to_csv(tdir / "threshold_analysis_mesh.csv", index=False)

    # --- Proportion / window-length sweep (E9) ---
    e9 = flow[flow.experiment == "E9"]
    if len(e9):
        e9.groupby("scenario")[["precision", "recall", "f1", "anomalous_flow_share"]].agg(["mean", "std"]).pipe(
            lambda d: (d.set_axis([f"{a}_{b}" for a, b in d.columns], axis=1))).reset_index().to_csv(tdir / "window_length_sweep.csv", index=False)

    # --- Per-attack recall (E3, high intensity) ---
    rows = []
    for s in seeds:
        for r in s["flow_rows"]:
            if r["experiment"] == "E3":
                for atk, d in r["per_attack_recall"].items():
                    rows.append({"seed": r["seed"], "attack": atk, "recall": d["recall"], "flows": d["flows"]})
    par = pd.DataFrame(rows)
    if len(par):
        # Each seed only samples some attack types, so n_seeds < 8 for most attacks: report it.
        par.groupby("attack").agg(n_seeds=("recall", "count"), mean_recall=("recall", "mean"),
                                  std_recall=("recall", "std"), min_recall=("recall", "min"),
                                  max_recall=("recall", "max"), mean_flows=("flows", "mean")
                                  ).reset_index().to_csv(tdir / "per_attack_recall_E3.csv", index=False)

    # --- Figures ---
    _fig_score_hist(seeds, fdir)
    _fig_roc(seeds, fdir)
    _fig_ablation_bar(mesh, fdir)
    _fig_threshold_tradeoff(e8f, fdir)
    _fig_per_attack(par, fdir)
    _fig_contributions(seeds, fdir)

    _write_results_md(out, manifest, n_seeds, g, tdir, fdir)
    return out


def _fig_score_hist(seeds, fdir):
    normal = np.zeros(len(HIST_BINS) - 1); attack = np.zeros(len(HIST_BINS) - 1); thr = []
    for s in seeds:
        h = s["extra"].get("score_hist")
        if h: normal += np.array(h["normal"]); attack += np.array(h["attack"]); thr.append(h["threshold"])
    if not thr: return
    fig, ax = plt.subplots(figsize=(7, 4))
    centers = (np.array(HIST_BINS[:-1]) + np.array(HIST_BINS[1:])) / 2
    ax.bar(centers, normal, width=np.diff(HIST_BINS), alpha=.6, label="normal flows (true label)")
    ax.bar(centers, attack, width=np.diff(HIST_BINS), alpha=.6, label="attack flows (true label)")
    ax.axvline(np.mean(thr), color="k", ls="--", label=f"mean threshold ({np.mean(thr):.3f})")
    ax.set_xlabel("anomaly score"); ax.set_ylabel("flow count (summed over seeds)")
    ax.set_title("Anomaly score distribution — Experiment 3 (high intensity)"); ax.legend()
    fig.tight_layout(); fig.savefig(fdir / "score_distribution_E3.png", dpi=130); plt.close(fig)


def _fig_roc(seeds, fdir):
    curves = {}
    for s in seeds:
        roc = s["extra"].get("roc")
        if roc:
            for model, tpr in roc.items(): curves.setdefault(model, []).append(tpr)
    if not curves: return
    fig, ax = plt.subplots(figsize=(6, 5))
    for model, arrs in curves.items():
        m = np.mean(arrs, axis=0)
        ax.plot(FPR_GRID, m, label=f"{model} (mean over {len(arrs)} seeds)")
    ax.plot([0, 1], [0, 1], "k:", lw=1)
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("ROC — Experiment 3 (high intensity), model comparison"); ax.legend()
    fig.tight_layout(); fig.savefig(fdir / "roc_comparison_E3.png", dpi=130); plt.close(fig)


def _fig_ablation_bar(mesh, fdir):
    m = mesh[(mesh.experiment == "E3") & (mesh.scenario == "high_intensity")]
    if not len(m): return
    order = ["A0_anomaly_only", "A1_plus_evidence", "A2_plus_trust", "A3_plus_consensus", "A4_full_system"]
    g = m.groupby("variant")[["epoch_precision", "epoch_recall", "epoch_f1"]].agg(["mean", "std"]).reindex(order)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(order)); w = 0.25
    for i, metric in enumerate(["epoch_precision", "epoch_recall", "epoch_f1"]):
        ax.bar(x + (i - 1) * w, g[(metric, "mean")], w, yerr=g[(metric, "std")].fillna(0), capsize=3, label=metric)
    ax.set_xticks(x); ax.set_xticklabels([o.split("_", 1)[1] for o in order], rotation=20)
    ax.set_title("Ablation study — epoch-level metrics (Experiment 3, high intensity)"); ax.legend()
    fig.tight_layout(); fig.savefig(fdir / "ablation_E3.png", dpi=130); plt.close(fig)


def _fig_threshold_tradeoff(e8f, fdir):
    if not len(e8f): return
    g = e8f.groupby("quantile")[["precision", "recall", "false_positive_rate"]].mean().reset_index()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(g["quantile"], g.precision, "o-", label="precision")
    ax.plot(g["quantile"], g.recall, "o-", label="recall")
    ax.plot(g["quantile"], g.false_positive_rate, "o-", label="false positive rate")
    ax.set_xlabel("decision-threshold quantile (of training scores)"); ax.set_title("Threshold sensitivity — Experiment 8")
    ax.legend(); fig.tight_layout(); fig.savefig(fdir / "threshold_sensitivity_E8.png", dpi=130); plt.close(fig)


def _fig_per_attack(par, fdir):
    if not len(par): return
    g = par.groupby("attack").recall.agg(["mean", "std"]).reset_index()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(g.attack, g["mean"], yerr=g["std"].fillna(0), capsize=4)
    ax.set_ylabel("recall"); ax.set_title("Per-attack-type recall — Experiment 3 (high intensity)")
    plt.xticks(rotation=20); fig.tight_layout(); fig.savefig(fdir / "per_attack_recall_E3.png", dpi=130); plt.close(fig)


def _fig_contributions(seeds, fdir):
    rows = []
    for s in seeds:
        for kind, d in s["extra"].get("contributions_e3", {}).items():
            for feat, v in d["mean_contribution"].items():
                rows.append({"kind": kind, "feature": feat, "v": v})
    if not rows: return
    df = pd.DataFrame(rows).groupby(["kind", "feature"]).v.mean().reset_index()
    top_feats = df.groupby("feature").v.mean().abs().sort_values(ascending=False).head(8).index
    piv = df[df.feature.isin(top_feats)].pivot(index="feature", columns="kind", values="v").fillna(0)
    fig, ax = plt.subplots(figsize=(8, 5))
    piv.plot(kind="barh", ax=ax)
    ax.set_xlabel("mean SHAP contribution toward anomalous"); ax.set_title("Evidence: top feature contributions by attack type (E3)")
    fig.tight_layout(); fig.savefig(fdir / "evidence_contributions_E3.png", dpi=130); plt.close(fig)


def _write_results_md(out, manifest, n_seeds, flow_table, tdir, fdir) -> None:
    L = ["# ImmunoMesh — Phase 10 multi-seed results (auto-generated)\n",
         "**All data are SIMULATED/SYNTHETIC.** These are software-only results; no hardware, real network, or real attacks were used.\n",
         f"Seeds: {manifest.get('seeds')}  (n={n_seeds}). "
         f"Config: train/eval duration = {manifest.get('base_config', {}).get('simulation', {}).get('train_duration_s')}s / "
         f"{manifest.get('base_config', {}).get('simulation', {}).get('eval_duration_s')}s per seed. "
         f"Environment: Python {manifest.get('python')}, scikit-learn {manifest.get('sklearn')}, {manifest.get('platform')}.\n",
         "**How to read the metrics.** *Flow-level* metrics score every flow record against its ground-truth "
         "label. *Epoch/window-level* metrics (ablation, response, recovery) score 10 s per-device epochs and attack "
         "windows after trust/consensus/response aggregation. They have different units and are not interchangeable. "
         "`std` is the sample standard deviation (ddof=1) across seeds; `nan` means undefined (e.g. E1 has no attack "
         "flows, so precision/recall/F1/ROC-AUC are undefined, not zero).\n",
         "## Flow-level detection, by experiment/scenario (mean ± std over seeds)\n",
         md_table(flow_table[["experiment", "scenario", "n_seeds", "precision_mean", "precision_std", "recall_mean", "recall_std",
                              "f1_mean", "f1_std", "roc_auc_mean", "false_positive_rate_mean"]])]
    notes = {
        "ablation_E3_high_intensity": "Epoch-level (not comparable with the flow-level table). A0 and A1 are identical: evidence "
            "corroboration changed no alert decisions in this setup. Adding trust (A2) lowers epoch precision because alerts "
            "persist while trust recovers after an attack ends; trust, consensus and response are operational layers and are "
            "not optimised for instantaneous F1.",
        "model_comparison": "Flow-level; each model's threshold is the 0.99 quantile of its own training scores. Isolation "
            "Forest has the highest mean precision but lower mean recall, F1 and ROC-AUC than LocalOutlierFactor and OneClassSVM in "
            "both scenarios. Paired per-seed differences are consistent for recall and, at high intensity, for LOF's F1 and "
            "ROC-AUC (8/8 seeds), but not for F1 at low intensity (see docs/EVIDENCE_SUMMARY.md). fit_s/score_s are wall-clock "
            "on the build machine and were not measured for Isolation Forest (nan).",
        "per_attack_recall_E3": "Recall is computed per seed, then summarised over the `n_seeds` seeds in which that attack "
            "type occurred (each seed draws attack types for only a few windows, so `n_seeds` is below 8 for most attacks). "
            "Estimates resting on few seeds, with a wide min-max range, are weak.",
        "threshold_analysis_flow": "Flow-level; E3 scenario; threshold = the stated quantile of training scores.",
        "window_length_sweep": "Flow-level; attack window length varied at fixed high intensity.",
    }
    for f in ["ablation_E3_high_intensity", "model_comparison", "threshold_analysis_flow", "per_attack_recall_E3", "window_length_sweep"]:
        p = tdir / f"{f}.csv"
        if p.exists():
            L += [f"\n## {f.replace('_', ' ')}\n", md_table(pd.read_csv(p)), f"\n*{notes[f]}*\n"]
    figs = sorted(fdir.glob("*.png"))
    if figs:
        L.append("\n## Figures\n")
        L += [f"- `figures/{p.name}`" for p in figs]
    L.append("\nGenerated by `python -m immunomesh.cli report` from `results/final/_seeds/*.json`. "
             "See docs/EXPERIMENTS.md for the experiment definitions and docs/LIMITATIONS.md for caveats.")
    (out / "RESULTS.md").write_text("\n".join(L))


if __name__ == "__main__":
    build_report()
