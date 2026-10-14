"""Simulated adaptive response state machine (Phase 9).

States: NORMAL, SUSPICIOUS, HIGH_RISK, QUARANTINED, RECOVERING, RESTORED.
NOTHING real is blocked: quarantine only changes a software state. While QUARANTINED the
device's flows are still observed (as if via a monitoring tap) so recovery can be judged.

One transition per device per epoch (decisions use epoch-end data):
 NORMAL      -> SUSPICIOUS   det_susp
 SUSPICIOUS  -> HIGH_RISK    confirmed AND trust < t_high              (evidence confirmation)
             -> NORMAL       clear_epochs consecutive epochs with no det_susp
 HIGH_RISK   -> QUARANTINED  (trust < t_quar OR 2 consecutive HIGH_RISK epochs) AND consensus gate
             -> SUSPICIOUS   no det_susp and trust >= t_high
 QUARANTINED -> RECOVERING   cooldown elapsed AND recover_clean_epochs clean AND trust >= recover_trust
 RECOVERING  -> RESTORED     probation_epochs clean epochs
             -> QUARANTINED  det_susp (cooldown x escalation_factor, capped)   [escalation]
 RESTORED    -> NORMAL       next epoch
"""
from __future__ import annotations
from dataclasses import dataclass, field
from immunomesh.config import MeshConfig

STATES = ["NORMAL", "SUSPICIOUS", "HIGH_RISK", "QUARANTINED", "RECOVERING", "RESTORED"]
EVENT_FOR = {("NORMAL", "SUSPICIOUS"): "SUSPICION_RAISED", ("SUSPICIOUS", "HIGH_RISK"): "HIGH_RISK_DECLARED",
             ("SUSPICIOUS", "NORMAL"): "SUSPICION_CLEARED", ("HIGH_RISK", "SUSPICIOUS"): "DE_ESCALATED",
             ("HIGH_RISK", "QUARANTINED"): "QUARANTINE_STARTED", ("QUARANTINED", "RECOVERING"): "RECOVERY_STARTED",
             ("RECOVERING", "RESTORED"): "RESTORED", ("RECOVERING", "QUARANTINED"): "RECOVERY_FAILED_REQUARANTINE",
             ("RESTORED", "NORMAL"): "RETURNED_TO_NORMAL"}


@dataclass
class DeviceState:
    state: str = "NORMAL"
    in_state: int = 0
    clean: int = 0
    high_epochs: int = 0
    cooldown: int = 0
    n_quarantines: int = 0


class ResponseEngine:
    def __init__(self, cfg: MeshConfig, devices: list[str]) -> None:
        self.cfg = cfg
        self.dev = {d: DeviceState(cooldown=cfg.cooldown_epochs) for d in devices}

    def step(self, device: str, det_susp: bool, confirmed: bool, trust: float, consensus: float | None) -> tuple[str, str, str | None]:
        """Advance one epoch. Returns (state_before, state_after, event_type or None)."""
        c, s = self.cfg, self.dev[device]
        before = s.state
        new = before
        s.in_state += 1
        s.clean = 0 if det_susp else s.clean + 1
        if before == "NORMAL":
            if det_susp: new = "SUSPICIOUS"
        elif before == "SUSPICIOUS":
            if confirmed and trust < c.t_high: new = "HIGH_RISK"
            elif s.clean >= c.clear_epochs: new = "NORMAL"
        elif before == "HIGH_RISK":
            s.high_epochs += 1
            gate = True if consensus is None else consensus >= c.consensus_min
            if (trust < c.t_quar or s.high_epochs >= 2) and gate:
                new = "QUARANTINED"; s.n_quarantines += 1
            elif not det_susp and trust >= c.t_high:
                new = "SUSPICIOUS"
        elif before == "QUARANTINED":
            if s.in_state > s.cooldown and s.clean >= c.recover_clean_epochs and trust >= c.recover_trust:
                new = "RECOVERING"
        elif before == "RECOVERING":
            if det_susp:
                new = "QUARANTINED"; s.cooldown = min(s.cooldown * c.escalation_factor, c.max_cooldown_epochs)
                s.n_quarantines += 1
            elif s.clean >= c.probation_epochs:
                new = "RESTORED"
        elif before == "RESTORED":
            new = "NORMAL"; s.cooldown = c.cooldown_epochs
        if new != before:
            s.state, s.in_state, s.high_epochs = new, 0, 0
            if new in ("QUARANTINED", "RECOVERING", "NORMAL"):
                s.clean = 0
        return before, new, EVENT_FOR.get((before, new))
