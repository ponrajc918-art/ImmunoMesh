"""Detection metrics computed from labels + detector outputs (Phase 5).

The detector is unsupervised (trained without labels); labels are used ONLY here, to
measure how well its decisions match the simulator's ground truth.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.metrics import (confusion_matrix, precision_score, recall_score, f1_score,
                             roc_auc_score, average_precision_score)


def detection_metrics(y_true, y_pred, scores) -> dict:
    y_true, y_pred = np.asarray(y_true).astype(int), np.asarray(y_pred).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    m = {
        "n_flows": int(len(y_true)), "n_anomalous_flows": int(y_true.sum()),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else float("nan"),
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else float("nan"),
    }
    if len(np.unique(y_true)) == 2:  # AUC undefined with a single class
        m["roc_auc"] = float(roc_auc_score(y_true, scores))
        m["average_precision"] = float(average_precision_score(y_true, scores))
    else:
        m["roc_auc"] = None
        m["average_precision"] = None
    return m


def per_attack_recall(attack_type, y_pred) -> dict:
    df = pd.DataFrame({"a": np.asarray(attack_type), "p": np.asarray(y_pred).astype(int)})
    df = df[df.a != "none"]
    return {a: {"flows": int(len(g)), "recall": float(g.p.mean())} for a, g in df.groupby("a")}
