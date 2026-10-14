"""Transparent per-device trust model (Phase 7).

State: T_d in [0,1], initial cfg.trust_init (1 = fully trusted).
Input per epoch: severity s in [0,1] (0 = clean epoch). See METHODOLOGY.md.

    suspicious epoch (s > 0):   T <- max(0, T - lambda_pen * s * (1 + gamma * k))
                                k = number of suspicious epochs among the last H epochs
    clean epoch (s == 0):       T <- T + lambda_rec * (1 - T)

Asymmetric by design: trust falls quickly with severity and repeat behaviour, recovers
slowly and geometrically. Risk bands: T>=alert_trust LOW; >=t_high MEDIUM; >=t_quar HIGH;
else CRITICAL. This is a research heuristic, not a proven trust protocol.
"""
from __future__ import annotations
from collections import deque
from immunomesh.config import MeshConfig


class TrustEngine:
    def __init__(self, cfg: MeshConfig, devices: list[str]) -> None:
        self.cfg = cfg
        self.trust = {d: cfg.trust_init for d in devices}
        self.hist = {d: deque(maxlen=cfg.history_window) for d in devices}

    def update(self, device: str, severity: float) -> float:
        c, T = self.cfg, self.trust[device]
        if severity > 0:
            k = sum(self.hist[device])
            T = max(0.0, T - c.lambda_pen * severity * (1 + c.gamma * k))
        else:
            T = T + c.lambda_rec * (1 - T)
        self.hist[device].append(1 if severity > 0 else 0)
        self.trust[device] = T
        return T

    def risk_level(self, trust: float) -> str:
        c = self.cfg
        if trust >= c.alert_trust: return "LOW"
        if trust >= c.t_high: return "MEDIUM"
        if trust >= c.t_quar: return "HIGH"
        return "CRITICAL"
