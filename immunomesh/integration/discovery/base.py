"""Discovery adapter interface (Section 4). Passive by default — Section 4: 'Do not perform
aggressive network scanning by default.'"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from immunomesh.integration.status import OpStatus


@dataclass
class DiscoveredDevice:
    ip: str
    mac: str | None
    source: str            # "arp" | "mdns" | "dhcp" | "flow_observation"
    hostname: str | None = None
    vendor: str | None = None
    confidence: float = 0.5


class DiscoveryAdapter(ABC):
    @abstractmethod
    def status(self) -> OpStatus: ...

    @abstractmethod
    def discover(self) -> list[DiscoveredDevice]:
        """One passive snapshot. Never sends probes/scans unless the adapter says so explicitly."""
