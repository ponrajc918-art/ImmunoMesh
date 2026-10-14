"""Phases 2-5 end-to-end: simulate -> clean -> features -> matrix -> detect -> evaluate.

Refactored (Phase 6+) into fit_baseline() + evaluate_scenario() so experiments can reuse a
trained detector across scenarios. run_detection_pipeline() reproduces the frozen Phase 5
baseline exactly (guarded by tests/test_baseline_regression.py).
"""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import yaml
from immunomesh.config import Config
from immunomesh.simulation.traffic import generate_traffic
from immunomesh.preprocessing.cleaner import DataCleaner
from immunomesh.preprocessing.matrix import FeatureMatrixBuilder
from immunomesh.features.engineering import FeatureEngineer
from immunomesh.detection.isolation_forest import AnomalyDetector
from immunomesh.evaluation.metrics import detection_metrics, per_attack_recall

log = logging.getLogger("immunomesh.pipeline")


@dataclass
class TrainedContext:
    cleaner: DataCleaner
    fe: FeatureEngineer
    mb: FeatureMatrixBuilder
    det: AnomalyDetector
    train_f: pd.DataFrame
    Xtr: pd.DataFrame
    rep_train: dict


def fit_baseline(cfg: Config, train_raw: pd.DataFrame | None = None) -> TrainedContext:
    """Generate the anomaly-free training period (seed = cfg.seed) and fit every stage on it."""
    if train_raw is None:
        train_raw = generate_traffic(cfg.simulation, seed=cfg.seed, with_anomalies=False)
    cleaner = DataCleaner().fit(train_raw)
    train_clean, rep = cleaner.transform(train_raw)
    fe = FeatureEngineer(cfg.features.window_s).fit(train_clean)
    train_f = fe.transform(train_clean)
    mb = FeatureMatrixBuilder().fit(train_f)
    Xtr = mb.transform(train_f)
    det = AnomalyDetector(cfg.detector, seed=cfg.seed).fit(Xtr)
    return TrainedContext(cleaner, fe, mb, det, train_f, Xtr, rep)


def evaluate_scenario(cfg: Config, ctx: TrainedContext, eval_raw: pd.DataFrame,
                      threshold: float | None = None) -> dict:
    """Apply a fitted context to one evaluation flow table."""
    eval_clean, rep_eval = ctx.cleaner.transform(eval_raw)
    eval_f = ctx.fe.transform(eval_clean)
    Xev = ctx.mb.transform(eval_f)
    pred = ctx.det.predict(Xev, meta=eval_f, threshold=threshold)
    pred["label"] = eval_f["label"].to_numpy()
    pred["attack_type"] = eval_f["attack_type"].to_numpy()
    return {"eval_f": eval_f, "Xev": Xev, "pred": pred, "rep_eval": rep_eval,
            "windows": eval_raw.attrs.get("attack_windows", {})}


def run_detection_pipeline(cfg: Config, out_dir: str | Path | None = None) -> dict:
    t0 = time.perf_counter()
    ctx = fit_baseline(cfg)
    eval_raw = generate_traffic(cfg.simulation, seed=cfg.seed + 1, with_anomalies=True)
    ev = evaluate_scenario(cfg, ctx, eval_raw)
    pred, eval_f, windows = ev["pred"], ev["eval_f"], ev["windows"]
    det = ctx.det
    elapsed = time.perf_counter() - t0

    metrics = {
        "note": "SIMULATED/SYNTHETIC data; software results only, no hardware or real traffic.",
        "seed": cfg.seed,
        "train_flows": len(ctx.train_f), "eval_flows": len(eval_f),
        "threshold": det.threshold_,
        "cleaning": {"train": ctx.rep_train, "eval": ev["rep_eval"]},
        "detection": detection_metrics(pred["label"], pred["is_anomaly"], pred["anomaly_score"]),
        "per_attack_recall": per_attack_recall(pred["attack_type"], pred["is_anomaly"]),
        "attack_windows": {d: [list(w) for w in ws] for d, ws in windows.items()},
        "wall_time_s_this_machine": round(elapsed, 2),
    }
    if out_dir:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "config.yaml").write_text(yaml.safe_dump(cfg.to_dict()))
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        pred.to_csv(out / "predictions.csv", index=False)
        det.save(out / "detector.joblib")
    return {"metrics": metrics, "pred": pred, "eval_features": eval_f, "detector": det,
            "context": ctx, "eval_out": ev}
