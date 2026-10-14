"""Shared capability vocabulary for switch/AP adapters (Section 10)."""
from __future__ import annotations
from enum import Enum
from immunomesh.integration.status import CapabilityStatus


class Capability(str, Enum):
    VLAN = "VLAN"
    ACL = "ACL"
    PORT_SHUTDOWN = "PORT_SHUTDOWN"
    MAC_ISOLATION = "MAC_ISOLATION"
    PORT_MIRRORING = "PORT_MIRRORING"


CapabilityReport = dict  # {Capability: CapabilityStatus}


def unknown_report() -> CapabilityReport:
    return {c: CapabilityStatus.UNKNOWN for c in Capability}
