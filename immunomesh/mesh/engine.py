"""Epoch-level ImmunoMesh engine: ties detection, evidence, trust, consensus, response, audit (Phases 6-9).

Per epoch (cfg.mesh.epoch_s) and per device the engine computes
  det_susp  = n_anom >= k_min and n_anom/n >= a_min          (detector alone)
  confirmed = n_conf >= k_min and n_conf/n >= a_min          (detector + corroborated evidence)
  severity  = flagged fraction of the chosen signal if the epoch is suspicious else 0
              (with consensus: severity = consensus score if >= a_min else 0)
then updates trust, (optionally) consensus, and (optionally) the response state machine.
`alert` (what is scored in the ablation) is chosen by the enabled components, highest wins:
  response -> state not in {NORMAL, RESTORED};  trust -> trust < alert_trust;
  evidence -> confirmed;  otherwise -> det_susp.
`alert_strict` equals `alert` except with response enabled, where it is state in {HIGH_RISK, QUARANTINED, RECOVERING}.
"""
from __future__ import annotations
import json, time
from collections import Counter
import numpy as np
import pandas as pd
from immunomesh.config import Config
from immunomesh.schema import T_START
from immunomesh.trust.engine import TrustEngine
from immunomesh.response.engine import ResponseEngine
from immunomesh.consensus.peers import consensus_for


def n_epochs_for(duration_s: float, epoch_s: float) -> int:
    return int(np.ceil(duration_s / epoch_s))


def flow_arrays(eval_f: pd.DataFrame, pred: pd.DataFrame, evidence: pd.DataFrame | None,
                devices: list[str], epoch_s: float, n_epochs: int) -> dict:
    didx = {d: i for i, d in enumerate(devices)}
    ep = np.clip(np.floor((eval_f["timestamp"].to_numpy() - T_START) / epoch_s).astype(int), 0, n_epochs - 1)
    dev = eval_f["src_id"].map(didx).to_numpy()
    flag = pred["is_anomaly"].to_numpy().astype(bool)
    conf = np.zeros(len(flag), bool)
    stm: dict[tuple, Counter] = {}
    if evidence is not None and len(evidence):
        rows = evidence["row"].to_numpy()
        conf[rows[evidence["corroborated"].to_numpy()]] = True
        for r, s in zip(rows, evidence["statements"]):
            stm.setdefault((int(dev[r]), int(ep[r])), Counter()).update(json.loads(s))
    return {"epoch": ep, "dev": dev, "flag": flag, "conf": conf,
            "score": pred["anomaly_score"].to_numpy(), "statements": stm}


def truth_table(windows: dict, devices: list[str], epoch_s: float, n_epochs: int):
    """truth[d, t] = epoch overlaps an attack window by >= 50% of epoch length; kind[d,t] = attack type if any overlap."""
    truth = np.zeros((len(devices), n_epochs), bool)
    kind = np.full((len(devices), n_epochs), "none", dtype=object)
    for d, dev in enumerate(devices):
        for k, t0, t1 in windows.get(dev, []):
            for t in range(n_epochs):
                a, b = t * epoch_s, (t + 1) * epoch_s
                ov = max(0.0, min(t1, b) - max(t0, a))
                if ov > 0: kind[d, t] = k
                if ov >= 0.5 * epoch_s: truth[d, t] = True
    return truth, kind


def run_mesh(cfg: Config, devices: list[str], flows: dict, windows: dict, n_epochs: int,
             peer_obs: tuple | None = None) -> dict:
    M = cfg.mesh
    if (M.use_consensus or M.use_response) and not M.use_trust:
        raise ValueError("consensus and response require trust")
    if M.use_consensus and peer_obs is None:
        raise ValueError("consensus enabled but no peer observations supplied")
    D, E = len(devices), M.epoch_s
    idx = flows["dev"] * n_epochs + flows["epoch"]
    size = D * n_epochs
    n = np.bincount(idx, minlength=size).reshape(D, n_epochs)
    n_an = np.bincount(idx[flows["flag"]], minlength=size).reshape(D, n_epochs)
    n_cf = np.bincount(idx[flows["conf"]], minlength=size).reshape(D, n_epochs)
    mx = np.full(size, np.nan)
    for i, s in zip(idx, flows["score"]):
        if not (mx[i] >= s): mx[i] = s
    mx = mx.reshape(D, n_epochs)
    truth, kind = truth_table(windows, devices, E, n_epochs)

    trust = TrustEngine(M, devices)
    resp = ResponseEngine(M, devices) if M.use_response else None
    rows, events, t_dec = [], [], []
    for t in range(n_epochs):
        weights = np.array([trust.trust[d] for d in devices])  # trust at previous epoch
        for d, dev in enumerate(devices):
            t0 = time.perf_counter()
            nn, na, nc = int(n[d, t]), int(n_an[d, t]), int(n_cf[d, t])
            a_an, a_cf = (na / nn, nc / nn) if nn else (0.0, 0.0)
            det_susp = na >= M.k_min and a_an >= M.a_min
            confirmed = (nc >= M.k_min and a_cf >= M.a_min) if M.use_evidence else det_susp
            a_sig = a_cf if M.use_evidence else a_an
            base_susp = confirmed
            support = cons = agree = float("nan")
            if M.use_consensus:
                support, cons, agree = consensus_for(d, t, *peer_obs, weights, a_sig, M.omega, M.a_min)
                sev = cons if (base_susp and cons >= M.a_min) else 0.0
            else:
                sev = a_sig if base_susp else 0.0
            T = trust.update(dev, sev) if M.use_trust else float("nan")
            risk = trust.risk_level(T) if M.use_trust else "N/A"
            before, state, ev_type = ("NORMAL", "NORMAL", None)
            if resp is not None:
                before, state, ev_type = resp.step(dev, det_susp, confirmed, T, cons if M.use_consensus else None)
            alert_strict = None
            if M.use_response:
                alert = state not in ("NORMAL", "RESTORED")
                alert_strict = state in ("HIGH_RISK", "QUARANTINED", "RECOVERING")
            elif M.use_trust: alert = T < M.alert_trust
            else: alert = confirmed
            t_dec.append((time.perf_counter() - t0) * 1000.0)
            ts = T_START + (t + 1) * E  # decision time = end of epoch
            rec = {"device": dev, "epoch": t, "t_start": T_START + t * E, "n_flows": nn, "n_anom": na, "n_conf": nc,
                   "a_anom": a_an, "a_conf": a_cf, "max_score": mx[d, t], "det_susp": det_susp, "confirmed": confirmed,
                   "severity": sev, "trust": T, "peer_support": support, "consensus": cons, "agreement": agree,
                   "risk_level": risk, "state": state, "alert": bool(alert),
                   "alert_strict": bool(alert if alert_strict is None else alert_strict), "truth_attack": bool(truth[d, t]),
                   "attack_type": kind[d, t]}
            rows.append(rec)
            common = {"ts": ts, "device": dev, "trust": T, "peer_support": support, "consensus": cons, "risk_level": risk}
            if det_susp:
                top = flows["statements"].get((d, t), Counter()).most_common(3)
                events.append({**common, "event_type": "ANOMALY_DETECTED", "detection_score": mx[d, t],
                               "evidence": json.dumps({"statements": [s for s, _ in top], "n_anom": na, "n_conf": nc, "n_flows": nn}),
                               "state_from": before, "state_to": before, "response": "MONITOR",
                               "details": json.dumps({"confirmed": bool(confirmed)})})
            if ev_type:
                resp_txt = {"QUARANTINE_STARTED": "SIMULATED_QUARANTINE", "RECOVERY_FAILED_REQUARANTINE": "SIMULATED_QUARANTINE",
                            "RECOVERY_STARTED": "SIMULATED_RECOVERY_PROBATION", "RESTORED": "SIMULATED_RESTORE"}.get(ev_type, "STATE_CHANGE")
                events.append({**common, "event_type": ev_type, "detection_score": mx[d, t], "evidence": None,
                               "state_from": before, "state_to": state, "response": resp_txt,
                               "details": json.dumps({"n_quarantines": resp.dev[dev].n_quarantines})})
    ep_df = pd.DataFrame(rows)
    return {"epochs": ep_df, "events": events,
            "timing": {"epoch_decisions": len(t_dec), "mean_decision_ms": float(np.mean(t_dec)),
                       "p95_decision_ms": float(np.percentile(t_dec, 95)),
                       "note": "software simulation time on this machine; not real edge-device latency"}}
