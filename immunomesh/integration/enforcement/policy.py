"""Enforcement policy (Section 16): maps a device's existing Phase 9 response state to a
proposed action. Reuses response/engine.py's states — no new detection logic here."""
from __future__ import annotations
from dataclasses import dataclass

ACTIONABLE_STATES = {"HIGH_RISK", "QUARANTINED"}


@dataclass
class ProposedAction:
    device: str
    action: str          # "isolate" | "restore" | "none"
    reason: str


def propose(device: str, response_state: str, previous_state: str) -> ProposedAction:
    if response_state == "QUARANTINED" and previous_state != "QUARANTINED":
        return ProposedAction(device, "isolate", f"response engine transitioned {previous_state} -> QUARANTINED")
    if previous_state == "QUARANTINED" and response_state in ("RECOVERING", "RESTORED", "NORMAL"):
        return ProposedAction(device, "restore", f"response engine transitioned QUARANTINED -> {response_state}")
    return ProposedAction(device, "none", f"state {response_state} requires no enforcement action")
