"""Evidence & explainability for flagged flows (Phase 6).

Two independent lines of evidence per flagged flow:
 1. Model attribution: SHAP TreeExplainer on the fitted Isolation Forest. SHAP values here
    explain the model's *expected isolation path length* (monotone DEcreasing in anomaly
    score), so a contribution toward anomaly is  c_i = -phi_i  (shorter path = more
    anomalous). Sum(phi)+expected_value reproduces the mean path length; it is NOT additive
    on the anomaly-score scale, only rank-consistent with it.
 2. Baseline deviation: robust z-score of each raw engineered feature vs the anomaly-free
    training baseline of the same device type:  z = (x - median) / max(1.4826*MAD, 0.5*std, eps).
    This does not depend on the model at all.

A flow is *corroborated* when the top-k attributed features are backed by baseline deviations:
    strength = sum_{i in top-k, |z_i|>=z_thr} c_i / sum_{i in top-k} c_i  (positive c only)
    corroborated  <=>  strength >= min_strength
The corroboration flag is the "evidence confirmation" used by trust and response (Phases 7-9).
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
import shap
from immunomesh.config import EvidenceConfig
from immunomesh.schema import ENGINEERED

TEMPLATES = {
    "packet_rate": "Packet rate {dir} device baseline",
    "pkt_rate_dev": "Packet rate {dir} device baseline",
    "byte_rate": "Byte rate {dir} device baseline",
    "byte_rate_dev": "Byte rate {dir} device baseline",
    "log_packets": "Packets per flow {dir} baseline",
    "log_bytes": "Bytes per flow {dir} baseline",
    "duration_s": "Flow duration {dir} baseline",
    "conn_freq": "Connection frequency {dir} baseline",
    "failed_ratio": "Failed-connection ratio {dir} baseline",
    "dest_diversity": "Destination diversity {dir} baseline",
    "dport_diversity": "Destination-port diversity {dir} baseline",
    "src_dst_freq": "Repeated connections to same destination {dir} baseline",
    "protocol_share": "Protocol mix {dir} baseline (share of flows with this protocol)",
    "new_destination": "Destination never seen in baseline for this device",
    "burst_indicator": "Burst behaviour {dir} baseline",
}


class EvidenceGenerator:
    def __init__(self, detector, cfg: EvidenceConfig) -> None:
        self.det, self.cfg = detector, cfg
        self.explainer = shap.TreeExplainer(detector.model)
        self.base_: dict[str, pd.DataFrame] = {}
        self.service_base_: dict[tuple, pd.DataFrame] = {}
        self.known_protocols_: dict[str, set] = {}

    @staticmethod
    def _baseline(g: pd.DataFrame) -> pd.DataFrame:
        med = g[ENGINEERED].median()
        mad = (g[ENGINEERED] - med).abs().median() * 1.4826
        scale = np.maximum(mad, 0.5 * g[ENGINEERED].std(ddof=0)).clip(lower=1e-6)
        return pd.DataFrame({"median": med, "scale": scale})

    def fit(self, train_f: pd.DataFrame) -> "EvidenceGenerator":
        for dtype, g in train_f.groupby("device_type"):
            self.base_[dtype] = self._baseline(g)
            self.known_protocols_[dtype] = set(g["protocol"].unique())
        if self.cfg.baseline_by_service:
            for key, g in train_f.groupby(["device_type", "dst_port"]):
                if len(g) >= self.cfg.min_service_n:
                    self.service_base_[key] = self._baseline(g)
        return self

    def _z(self, feats: pd.DataFrame) -> pd.DataFrame:
        z = pd.DataFrame(0.0, index=feats.index, columns=ENGINEERED)
        for dtype, g in feats.groupby("device_type"):
            b = self.base_[dtype]
            z.loc[g.index, ENGINEERED] = ((g[ENGINEERED] - b["median"]) / b["scale"]).to_numpy()
        for key, b in self.service_base_.items():  # override where a service-level baseline exists
            g = feats[(feats["device_type"] == key[0]) & (feats["dst_port"] == key[1])]
            if len(g):
                z.loc[g.index, ENGINEERED] = ((g[ENGINEERED] - b["median"]) / b["scale"]).to_numpy()
        return z

    def contributions(self, X: pd.DataFrame) -> pd.DataFrame:
        """Contribution toward 'anomalous' per model feature = -SHAP(path length)."""
        sv = self.explainer.shap_values(X.to_numpy())
        return pd.DataFrame(-sv, index=X.index, columns=X.columns)

    def explain(self, feats: pd.DataFrame, X: pd.DataFrame, pred: pd.DataFrame,
                only_flagged: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Return (evidence table, contribution matrix) for flagged (or all) flows.

        feats/X/pred must share the same positional order (as produced by evaluate_scenario).
        """
        sel = np.where(pred["is_anomaly"].to_numpy() == 1)[0] if only_flagged else np.arange(len(pred))
        if len(sel) == 0:
            return pd.DataFrame(), pd.DataFrame()
        f = feats.iloc[sel].reset_index(drop=True)
        Xs = X.iloc[sel].reset_index(drop=True)
        p = pred.iloc[sel].reset_index(drop=True)
        C = self.contributions(Xs)
        Z = self._z(f)
        k, zt = self.cfg.top_k, self.cfg.z_threshold
        recs = []
        for i in range(len(f)):
            c = C.iloc[i]
            top = c.sort_values(ascending=False).head(k)
            top = top[top > 0]
            tot = float(top.sum())
            backed, feats_out, stmts = 0.0, [], []
            for name, contrib in top.items():
                entry = {"feature": name, "contribution": round(float(contrib), 4)}
                dev = False
                if name in ENGINEERED:
                    z = float(Z.iloc[i][name])
                    entry.update(value=round(float(f.iloc[i][name]), 4), robust_z=round(z, 2))
                    dev = abs(z) >= zt
                    if dev:
                        stmts.append(TEMPLATES[name].format(dir="above" if z > 0 else "below"))
                else:  # one-hot column, e.g. protocol=ICMP: check baseline vocabulary
                    col, val = name.split("=")
                    if f.iloc[i][col] == val:
                        entry["value"] = val
                        if col == "protocol" and val not in self.known_protocols_[f.iloc[i]["device_type"]]:
                            dev = True
                            stmts.append(f"Protocol {val} never observed for {f.iloc[i]['device_type']} baseline")
                entry["deviates"] = bool(dev)
                if dev:
                    backed += float(contrib)
                feats_out.append(entry)
            strength = backed / tot if tot > 0 else 0.0
            recs.append({
                "device": p.iloc[i]["device"], "timestamp": p.iloc[i]["timestamp"],
                "anomaly_score": float(p.iloc[i]["anomaly_score"]),
                "confidence": float(p.iloc[i]["confidence"]),
                "model": "IsolationForest", "top_features": json.dumps(feats_out),
                "statements": json.dumps(list(dict.fromkeys(stmts))),
                "evidence_strength": round(strength, 4),
                "corroborated": bool(strength >= self.cfg.min_strength),
                "attack_type": p.iloc[i].get("attack_type", None),
                "label": int(p.iloc[i].get("label", -1)),
                "row": int(sel[i]),
            })
        return pd.DataFrame(recs), C.assign(row=sel)


def format_evidence(rec: pd.Series, threshold: float | None = None) -> str:
    stm = json.loads(rec["statements"]) or ["(no baseline deviation among top model features)"]
    return (f"Event: Device {rec['device']}\nDetection: Anomalous\nEvidence:\n"
            + "\n".join(f"  - {s}" for s in stm)
            + f"\nModel: {rec['model']}\nScore: {rec['anomaly_score']:.4f}"
            + (f" (threshold {threshold:.4f})" if threshold is not None else "")
            + f"\nEvidence strength: {rec['evidence_strength']:.2f}"
            + f" ({'corroborated' if rec['corroborated'] else 'uncorroborated'})")
