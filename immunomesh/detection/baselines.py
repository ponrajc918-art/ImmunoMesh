"""Comparison detectors (Phase 10): One-Class SVM and Local Outlier Factor.

Same protocol as the Isolation Forest: fit on the anomaly-free training matrix, score = higher is
more anomalous, threshold = quantile of the model's own training scores. OCSVM is fit on a random
subsample (kernel cost); LOF uses novelty=True so it can score unseen data.
"""
from __future__ import annotations
import time, warnings
warnings.filterwarnings("ignore", message="X does not have valid feature names")
import numpy as np
import pandas as pd
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor


def score_models(Xtr: pd.DataFrame, Xev: pd.DataFrame, seed: int, ocsvm_n: int = 3000, lof_k: int = 35) -> dict:
    out = {}
    sub = Xtr.sample(min(ocsvm_n, len(Xtr)), random_state=seed)
    t = time.perf_counter(); m = OneClassSVM(nu=0.01, gamma="scale").fit(sub); fit_s = time.perf_counter() - t
    t = time.perf_counter(); s_ev = -m.decision_function(Xev); score_s = time.perf_counter() - t
    out["OneClassSVM"] = {"train": -m.decision_function(Xtr), "eval": s_ev, "fit_s": fit_s, "score_s": score_s}
    t = time.perf_counter(); l = LocalOutlierFactor(n_neighbors=lof_k, novelty=True).fit(Xtr); fit_s = time.perf_counter() - t
    t = time.perf_counter(); s_ev = -l.score_samples(Xev); score_s = time.perf_counter() - t
    out["LocalOutlierFactor"] = {"train": -l.score_samples(Xtr), "eval": s_ev, "fit_s": fit_s, "score_s": score_s}
    return out
