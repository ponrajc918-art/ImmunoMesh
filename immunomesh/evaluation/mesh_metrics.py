"""Operational metrics from mesh epoch tables + attack windows (all simulated-time, software only)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from immunomesh.schema import T_START


def epoch_metrics(ep: pd.DataFrame, E: float, col: str = "alert", attacked: set | None = None) -> dict:
    y, p = ep["truth_attack"].to_numpy(), ep[col].to_numpy()
    tp, fp = int((y & p).sum()), int((~y & p).sum())
    fn, tn = int((y & ~p).sum()), int((~y & ~p).sum())
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if tp and prec == prec and rec == rec and (prec + rec) else 0.0
    ndev = ep["device"].nunique()
    hours = ep["epoch"].nunique() * E / 3600.0
    extra = {}
    if attacked is not None:
        clean = ep[~ep.device.isin(attacked)]
        extra["clean_device_alert_rate"] = float(clean[col].mean()) if len(clean) else float("nan")
    return {**extra, "epoch_tp": tp, "epoch_fp": fp, "epoch_fn": fn, "epoch_tn": tn, "epoch_precision": prec,
            "epoch_recall": rec, "epoch_f1": f1,
            "epoch_fpr": fp / (fp + tn) if fp + tn else float("nan"),
            "epoch_fnr": fn / (fn + tp) if fn + tp else float("nan"),
            "false_alert_epochs_per_device_hour": fp / (ndev * hours) if ndev * hours else float("nan")}


def window_metrics(ep: pd.DataFrame, windows: dict, E: float, col: str = "alert") -> dict:
    lat, det, n_w = [], 0, 0
    for dev, ws in windows.items():
        g = ep[ep.device == dev]
        for kind, t0, t1 in ws:
            n_w += 1
            rel_s = g.t_start - T_START
            sub = g[(rel_s < t1) & (rel_s + E > t0)]
            hit = sub[sub[col]] if col != "state_q" else sub[sub.state == "QUARANTINED"]
            if len(hit):
                det += 1
                lat.append(max(0.0, float(hit.iloc[0].t_start - T_START + E - t0)))
    return {"n_windows": n_w, "windows_detected": det,
            "window_detection_rate": det / n_w if n_w else float("nan"),
            "mean_latency_s": float(np.mean(lat)) if lat else float("nan"),
            "median_latency_s": float(np.median(lat)) if lat else float("nan")}


def response_metrics(ep: pd.DataFrame, events: list[dict], windows: dict, E: float) -> dict:
    ev = pd.DataFrame(events) if events else pd.DataFrame(columns=["ts", "device", "event_type"])
    q = ev[ev.event_type.isin(["QUARANTINE_STARTED", "RECOVERY_FAILED_REQUARANTINE"])] if len(ev) else ev
    false_q = 0
    for _, r in q.iterrows():
        rel = r.ts - T_START
        # justified if an attack window overlaps [rel-4E, rel]
        just = any((t0 < rel) and (t1 > rel - 4 * E) for _, t0, t1 in windows.get(r.device, []))
        false_q += 0 if just else 1
    contained, restored, ttr, tq = 0, 0, [], []
    n_w = sum(len(w) for w in windows.values())
    for dev, ws in windows.items():
        g = ep[ep.device == dev]
        for kind, t0, t1 in ws:
            rel_s = g.t_start - T_START
            sub = g[(rel_s < t1) & (rel_s + E > t0)]
            qs = sub[sub.state == "QUARANTINED"]
            if len(qs):
                contained += 1
                tq.append(max(0.0, float(qs.iloc[0].t_start - T_START + E - t0)))
                first_q_ts = qs.iloc[0].t_start + E
                rs = ev[(ev.device == dev) & (ev.event_type == "RESTORED") & (ev.ts >= first_q_ts)] if len(ev) else ev
                if len(rs):
                    restored += 1
                    ttr.append(float(rs.iloc[0].ts - T_START - t1))
    nq = len(q)
    return {"quarantine_events": nq, "false_quarantine_events": int(false_q),
            "false_quarantine_rate": false_q / nq if nq else float("nan"),
            "windows_contained": contained, "quarantine_rate": contained / n_w if n_w else float("nan"),
            "recovery_rate": restored / contained if contained else float("nan"),
            "mean_sim_quarantine_latency_s": float(np.mean(tq)) if tq else float("nan"),
            "mean_sim_time_to_restore_after_attack_s": float(np.mean(ttr)) if ttr else float("nan"),
            "n_devices_quarantined_ever": int(q.device.nunique()) if nq else 0}
