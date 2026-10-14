"""Shared status vocabulary for the real-network integration layer (Rule 2 / Rule 3).

Every hardware/network operation reports one of these — never a bare True/False — so a
status can never be silently misread as a stronger claim than it is.
"""
from __future__ import annotations
from enum import Enum


class OpStatus(str, Enum):
    SIMULATED = "SIMULATED"      # produced by the Phase 1-10 simulator, not real traffic/hardware
    LIVE = "LIVE"                # confirmed to have come from / acted on real traffic or hardware
    DRY_RUN = "DRY_RUN"          # would have acted; nothing was sent to real hardware
    UNSUPPORTED = "UNSUPPORTED"  # this adapter/capability is not available in this environment
    FAILED = "FAILED"            # attempted against real hardware/network and did not succeed
    VERIFIED = "VERIFIED"        # an independent check confirmed the claimed effect actually happened


class RuntimeMode(str, Enum):
    OBSERVE_ONLY = "OBSERVE_ONLY"
    DRY_RUN = "DRY_RUN"
    ENFORCE = "ENFORCE"

    @classmethod
    def escalation_order(cls) -> list["RuntimeMode"]:
        return [cls.OBSERVE_ONLY, cls.DRY_RUN, cls.ENFORCE]


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"


class BaselineState(str, Enum):
    BASELINE_COLLECTION = "BASELINE_COLLECTION"
    MONITORING = "MONITORING"
    ALERT = "ALERT"


class EnforcementStage(str, Enum):
    REQUESTED = "REQUESTED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    ROLLBACK_UNSUPPORTED = "ROLLBACK_UNSUPPORTED"


class CapabilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"
