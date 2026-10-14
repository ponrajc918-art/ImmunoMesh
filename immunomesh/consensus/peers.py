"""Peer observation + trust-weighted consensus (Phase 8).

Simulated distributed monitoring. Every monitored device hosts a local monitor: its own
Isolation Forest trained on a different random 80% subsample of the baseline (different
seed). When observer p watches target d, each flow of d is visible to p with probability
`visibility` (seeded Bernoulli), and p's opinion is its OWN model's flags on the visible flows.

    o_{p,d}(t)    = flagged visible flows / visible flows          (observers with >=1 visible flow)
    peer_support  = sum_p w_p o_{p,d}(t) / sum_p w_p ,   w_p = trust of p at the previous epoch
    consensus     = (1 - omega) * a_self(t) + omega * peer_support
    agreement     = share of observers whose local verdict (o_p >= a_min) equals the consensus verdict

Limitations (documented): peers share the feature pipeline and baseline distribution, so
their opinions are correlated; no peer compromise, message loss, or network delay is modelled.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from immunomesh.config import Config
from immunomesh.detection.isolation_forest import AnomalyDetector


class PeerObservers:
    def __init__(self, cfg: Config, devices: list[str]) -> None:
        self.cfg, self.devices = cfg, devices
        self.models: dict[str, AnomalyDetector] = {}
        self.sub_scores_: dict[str, np.ndarray] = {}

    def fit(self, Xtr: pd.DataFrame) -> "PeerObservers":
        for i, dev in enumerate(self.devices):
            s = self.cfg.seed * 7919 + i + 1
            rng = np.random.default_rng(s)
            idx = rng.choice(len(Xtr), int(0.8 * len(Xtr)), replace=False)
            sub = Xtr.iloc[np.sort(idx)]
            self.models[dev] = AnomalyDetector(self.cfg.detector, seed=s).fit(sub)
            self.sub_scores_[dev] = self.models[dev].score(sub)
        return self

    def flags(self, X: pd.DataFrame, quantile: float | None = None) -> np.ndarray:
        """(n_flows, n_devices) boolean flags, column j = opinion of device j's local monitor.

        quantile: optionally re-derive each monitor's threshold from its own training scores
        (used by threshold-sweep experiments so peers follow the same operating point)."""
        cols = []
        for d in self.devices:
            thr = self.models[d].threshold_ if quantile is None else float(np.quantile(self.sub_scores_[d], quantile))
            cols.append(self.models[d].score(X) > thr)
        return np.column_stack(cols)


def build_observations(peer_flags: np.ndarray, flow_dev: np.ndarray, flow_epoch: np.ndarray,
                       n_dev: int, n_epochs: int, visibility: float, seed: int):
    """vis[p,d,t], flg[p,d,t]: visible and flagged flow counts observer p has of target d in epoch t."""
    rng = np.random.default_rng(seed * 104729 + 17)
    vis = np.zeros((n_dev, n_dev, n_epochs)); flg = np.zeros((n_dev, n_dev, n_epochs))
    for d in range(n_dev):
        m = flow_dev == d
        ep, pf = flow_epoch[m], peer_flags[m]
        for p in range(n_dev):
            if p == d:
                continue
            seen = rng.random(m.sum()) < visibility
            vis[p, d] = np.bincount(ep[seen], minlength=n_epochs)
            flg[p, d] = np.bincount(ep[seen & pf[:, p]], minlength=n_epochs)
    return vis, flg


def consensus_for(d: int, t: int, vis, flg, weights: np.ndarray, a_self: float, omega: float, a_min: float):
    """Return (peer_support, consensus_score, agreement) for target d in epoch t."""
    v, f = vis[:, d, t], flg[:, d, t]
    obs_mask = v > 0
    obs_mask[d] = False
    if not obs_mask.any():
        return 0.0, a_self, float("nan")
    o = f[obs_mask] / v[obs_mask]
    w = weights[obs_mask]
    support = float((w * o).sum() / w.sum()) if w.sum() > 0 else float(o.mean())
    c = (1 - omega) * a_self + omega * support
    agree = float(np.mean((o >= a_min) == (c >= a_min)))
    return support, c, agree
