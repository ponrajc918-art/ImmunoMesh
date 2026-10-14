"""Phase 10: multi-seed experiment suite (Experiments 1-10, ablation, model comparison, thresholds).

Every number is computed by the implemented pipeline. Per-seed results are checkpointed as JSON
(resumable). Seeds, configuration and environment are recorded in run_manifest.json.

Experiment map (see docs/EXPERIMENTS.md):
 E1 normal only | E2 low-intensity anomalies | E3 high-intensity | E4 multiple anomalous devices (5)
 E5/E6 trust+consensus enabled (A3) vs disabled (A1) | E7 response enabled (A4) vs disabled (A3)
 E8 threshold sweep | E9 anomaly-proportion sweep (window length) | E10 recovery/quarantine scenario
 Ablation A0..A4 is run on every scenario; model comparison (IF/OCSVM/LOF) on E2 and E3.
"""
from __future__ import annotations
import dataclasses, json, logging, platform, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import roc_curve
from immunomesh.config import load_config
from immunomesh.evaluation.metrics import detection_metrics, per_attack_recall
from immunomesh.detection.baselines import score_models
from immunomesh.experiments.scenario import (prepare_seed, prepare_scenario, run_variant, rethreshold, ABLATION)

log = logging.getLogger("immunomesh.final")
FINAL_SEEDS = list(range(200, 210))
QUANTILES = [0.95, 0.98, 0.99, 0.995, 0.999]
PROPORTION_WINDOWS = [30, 60, 120, 240]
FPR_GRID = np.linspace(0, 1, 101)
HIST_BINS = np.linspace(0.3, 0.9, 61)


def _flow_row(sd, exp, scen, seed, extra=None):
    p = sd.ev["pred"]
    m = detection_metrics(p.label, p.is_anomaly, p.anomaly_score)
    m.update({"experiment": exp, "scenario": scen, "seed": seed,
              "anomalous_flow_share": float(p.label.mean()), "per_attack_recall": per_attack_recall(p.attack_type, p.is_anomaly)})
    m.update(extra or {})
    return m


def _mesh_rows(sc, sd, exp, scen, seed, variants=ABLATION, extra=None):
    rows = []
    for name, ov in variants.items():
        r = run_variant(sc, sd, ov)
        row = {"experiment": exp, "scenario": scen, "variant": name, "seed": seed, **r["metrics"], **(extra or {})}
        rows.append(row)
    return rows


def run_seed(seed: int, base_overrides: dict | None = None) -> dict:
    t0 = time.perf_counter()
    cfg = load_config(overrides={"seed": seed, **(base_overrides or {})})
    sc = prepare_seed(cfg)
    flow, mesh, extra = [], [], {}

    scenarios = [("E1", "normal_only", {}, False), ("E2", "low_intensity", {"intensity": "low"}, True),
                 ("E3", "high_intensity", {"intensity": "high"}, True),
                 ("E4", "multi_device_5", {"intensity": "high", "anomalous_device_count": 5}, True)]
    scenarios += [("E9", f"window_{w}s", {"intensity": "high", "window_length_s": float(w)}, True) for w in PROPORTION_WINDOWS]
    scenarios += [("E10", "recovery_quarantine", {"intensity": "high", "windows_per_device": 3,
                                                  "window_length_s": 90.0, "anomalous_device_count": 3}, True)]
    e3 = None
    for exp, name, ov, anom in scenarios:
        sd = prepare_scenario(sc, ov, with_anomalies=anom)
        flow.append(_flow_row(sd, exp, name, seed))
        mesh += _mesh_rows(sc, sd, exp, name, seed)
        if exp in ("E2", "E3"):  # model comparison on identical data
            y = sd.ev["pred"]["label"].to_numpy()
            comp = {"IsolationForest": {"train": sc.train_scores, "eval": sd.ev["pred"]["anomaly_score"].to_numpy(),
                                        "fit_s": None, "score_s": None}}
            comp.update(score_models(sc.ctx.Xtr, sd.ev["Xev"], seed))
            for model, d in comp.items():
                thr = float(np.quantile(d["train"], cfg.detector.threshold_quantile))
                m = detection_metrics(y, d["eval"] > thr, d["eval"])
                m.update({"experiment": exp, "scenario": name, "seed": seed, "model": model,
                          "fit_s": d["fit_s"], "score_s": d["score_s"]})
                extra.setdefault("model_comparison", []).append(m)
                if exp == "E3":
                    fpr, tpr, _ = roc_curve(y, d["eval"])
                    extra.setdefault("roc", {})[model] = np.interp(FPR_GRID, fpr, tpr).tolist()
        if exp == "E3":
            e3 = sd
            p = sd.ev["pred"]
            extra["score_hist"] = {"bins": HIST_BINS.tolist(), "threshold": sc.ctx.det.threshold_,
                                   "normal": np.histogram(np.clip(p.anomaly_score[p.label == 0], 0.3, 0.9), HIST_BINS)[0].tolist(),
                                   "attack": np.histogram(np.clip(p.anomaly_score[p.label == 1], 0.3, 0.9), HIST_BINS)[0].tolist()}
            E, C = sd.evidence, sd.shap_C
            if len(E):
                contrib = {}
                kinds = np.where(E.label == 1, E.attack_type, "false_positive")
                feats = [c for c in C.columns if c != "row"]
                for k in np.unique(kinds):
                    contrib[k] = {"n": int((kinds == k).sum()),
                                  "mean_contribution": C.loc[kinds == k, feats].mean().to_dict(),
                                  "corroborated_rate": float(E.corroborated[kinds == k].mean())}
                extra["contributions_e3"] = contrib
    # E8 threshold sweep on E3 data
    for q in QUANTILES:
        sd = rethreshold(sc, e3, q)
        flow.append(_flow_row(sd, "E8", f"q{q}", seed, {"quantile": q}))
        mesh += _mesh_rows(sc, sd, "E8", f"q{q}", seed, {k: ABLATION[k] for k in ("A0_anomaly_only", "A4_full_system")}, {"quantile": q})
    log.info("seed %s done in %.1fs", seed, time.perf_counter() - t0)
    return {"seed": seed, "flow_rows": flow, "mesh_rows": mesh, "extra": extra, "seconds": time.perf_counter() - t0}


def run_all(seeds=FINAL_SEEDS, out_dir="results/final", base_overrides=None) -> Path:
    out = Path(out_dir); (out / "_seeds").mkdir(parents=True, exist_ok=True)
    for s in seeds:
        f = out / "_seeds" / f"seed_{s}.json"
        if f.exists():
            log.info("seed %s already done (checkpoint)", s); continue
        res = run_seed(s, base_overrides)
        f.write_text(json.dumps(res, default=_json))
    cfg = load_config(overrides=base_overrides or {})

    # Scenario IDs are derived from what the checkpointed seed files actually contain, never
    # hand-typed — so the manifest can never silently drift from what was really executed.
    scenario_ids = sorted({(r["experiment"], r["scenario"]) for s in seeds
                          for r in json.loads((out / "_seeds" / f"seed_{s}.json").read_text())["flow_rows"]})
    ablation_variants = sorted({r["variant"] for s in seeds
                               for r in json.loads((out / "_seeds" / f"seed_{s}.json").read_text())["mesh_rows"]})
    seed_files = sorted(str(p) for p in (out / "_seeds").glob("seed_*.json"))
    generated_at = datetime.now(timezone.utc).isoformat()

    (out / "run_manifest.json").write_text(json.dumps({
        "generated_at": generated_at,
        "seeds": list(seeds), "base_config": cfg.to_dict(), "quantiles": QUANTILES, "proportion_windows": PROPORTION_WINDOWS,
        "scenario_ids": [f"{e}:{s}" for e, s in scenario_ids], "ablation_variants": ablation_variants,
        "python": sys.version.split()[0], "sklearn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__,
        "platform": platform.platform(),
        "per_seed_result_files": seed_files,
        "output_locations": {"per_seed_raw_results": str(out / "_seeds"), "aggregated_tables": str(out / "tables"),
                             "figures": str(out / "figures"), "summary_report": str(out / "RESULTS.md"),
                             "dashboard_demo_run": str(out / "demo")},
        "note": "All data SIMULATED/SYNTHETIC. Software-only results; no hardware or real traffic."}, indent=2, default=_json))
    return out


def _json(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, np.ndarray): return o.tolist()
    raise TypeError(type(o))


if __name__ == "__main__":
    from immunomesh.logging_utils import setup_logging
    setup_logging("results/final/run.log")
    run_all()
