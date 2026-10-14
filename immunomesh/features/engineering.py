"""Cybersecurity feature engineering (Phase 4).

All windowed features use ONLY past flows of the same source device (causal window of
`window_s` seconds ending at the current flow), so no future information leaks in.

Feature | formula | why | security relevance
packet_rate     packets / duration              flow intensity             floods, spikes
byte_rate       bytes / duration                data throughput            exfiltration, floods
log_packets     log1p(packets)                  tames heavy tail           volume anomalies
log_bytes       log1p(bytes)                    tames heavy tail           volume anomalies
duration_s      flow duration                   flow shape                 scans (very short), exfil (long)
conn_freq       #flows by device in window      connection frequency       scans, brute force, spikes
failed_ratio    failed / flows in window        auth/connect failures      brute force, scans
dest_diversity  #unique dst in window           fan-out                    scanning, lateral movement
dport_diversity #unique dst ports in window     port fan-out               port scans
src_dst_freq    #flows of same (src,dst) pair   pair repetition            brute force, C2 beaconing
protocol_share  share of window flows w/ same protocol   protocol mix       protocol irregularity
new_destination 1 if dst unseen in baseline     destination novelty        exfil, unusual peers
pkt_rate_dev    robust z of packet_rate vs device baseline (median/MAD, from training)
byte_rate_dev   robust z of byte_rate vs device baseline
burst_indicator max(|pkt_rate_dev|, |byte_rate_dev|) > 3  -> 1 else 0
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from immunomesh.schema import ENGINEERED


def _robust_stats(x: pd.Series) -> tuple[float, float]:
    med = float(x.median())
    mad = float((x - med).abs().median()) * 1.4826
    return med, max(mad, 1e-6 * max(abs(med), 1.0))


class FeatureEngineer:
    def __init__(self, window_s: float = 10.0) -> None:
        self.window_s = window_s
        self.baseline_: dict | None = None

    @staticmethod
    def _rates(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["packet_rate"] = out["packet_count"] / out["duration_s"]
        out["byte_rate"] = out["byte_count"] / out["duration_s"]
        return out

    def fit(self, clean_train: pd.DataFrame) -> "FeatureEngineer":
        d = self._rates(clean_train)
        base = {"dev": {}, "known_dst": {}}
        for dev, g in d.groupby("src_id"):
            base["dev"][dev] = {"pkt": _robust_stats(np.log1p(g["packet_rate"])),
                                "byte": _robust_stats(np.log1p(g["byte_rate"]))}
            base["known_dst"][dev] = set(g["dst_id"].unique())
        self.baseline_ = base
        return self

    def transform(self, clean: pd.DataFrame) -> pd.DataFrame:
        if self.baseline_ is None:
            raise RuntimeError("FeatureEngineer must be fit first")
        d = self._rates(clean).sort_values("timestamp", kind="stable").reset_index(drop=True)
        n = len(d)
        cols = {k: np.zeros(n) for k in ["conn_freq", "failed_ratio", "dest_diversity",
                                         "dport_diversity", "src_dst_freq", "protocol_share"]}
        for dev, idx in d.groupby("src_id").indices.items():
            ts = d["timestamp"].to_numpy()[idx]
            dst = d["dst_id"].to_numpy()[idx]
            dport = d["dst_port"].to_numpy()[idx]
            proto = d["protocol"].to_numpy()[idx]
            fail = d["failed_conn"].to_numpy()[idx].astype(float)
            left = 0
            for i in range(len(idx)):
                while ts[left] < ts[i] - self.window_s:
                    left += 1
                sl = slice(left, i + 1)
                w = i - left + 1
                r = idx[i]
                cols["conn_freq"][r] = w
                cols["failed_ratio"][r] = fail[sl].sum() / w
                cols["dest_diversity"][r] = len(set(dst[sl]))
                cols["dport_diversity"][r] = len(set(dport[sl]))
                cols["src_dst_freq"][r] = (dst[sl] == dst[i]).sum()
                cols["protocol_share"][r] = (proto[sl] == proto[i]).sum() / w
        for k, v in cols.items():
            d[k] = v
        d["log_packets"] = np.log1p(d["packet_count"])
        d["log_bytes"] = np.log1p(d["byte_count"])
        lp, lb = np.log1p(d["packet_rate"]), np.log1p(d["byte_rate"])
        pdv, bdv = np.zeros(n), np.zeros(n)
        newd = np.zeros(n)
        for dev, idx in d.groupby("src_id").indices.items():
            b = self.baseline_["dev"].get(dev)
            if b is None:  # unseen device: no baseline -> neutral deviation
                continue
            pdv[idx] = (lp.to_numpy()[idx] - b["pkt"][0]) / b["pkt"][1]
            bdv[idx] = (lb.to_numpy()[idx] - b["byte"][0]) / b["byte"][1]
            known = self.baseline_["known_dst"][dev]
            newd[idx] = (~d["dst_id"].iloc[idx].isin(known)).astype(float).to_numpy()
        d["pkt_rate_dev"] = np.clip(pdv, -50, 50)
        d["byte_rate_dev"] = np.clip(bdv, -50, 50)
        d["new_destination"] = newd
        d["burst_indicator"] = (np.maximum(np.abs(d["pkt_rate_dev"]), np.abs(d["byte_rate_dev"])) > 3).astype(float)
        assert all(c in d.columns for c in ENGINEERED)
        return d
